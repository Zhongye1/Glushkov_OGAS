"""解析 worker 任务入口（对接 worker_dispatcher.py 的派发契约）。

worker 契约：
- worker 是队列消费者，不对外开接口、不做用户鉴权；
- API 层完成鉴权后，把授权结果（tenant_id / namespace / s3_key）作为任务
  payload 透传，worker 仅用它们做数据隔离；
- 输入与产物一律走 ArtifactStorage 的对象存储 key，不依赖本地路径。

注册名固定为 ``app.core.tasks.document_ingestion_tasks.parse_task``（Celery
按名字路由，与文件位置无关）。文件放 document_parser 内是当前可导入可测试
的过渡：app/core/__init__.py 硬依赖尚未落地的 shared.* 包。MVP 未装 Celery
时退化为纯函数直调。
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.services.document_parser.parse_service import parse_job
from app.services.document_parser.storage.artifact_storage import get_artifact_storage

try:  # Celery 为可选依赖（pyproject 未声明时退化为直调）
    from celery import shared_task as _celery_shared_task

    _CELERY_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CELERY_AVAILABLE = False

    def _celery_shared_task(*args, **kwargs):  # type: ignore[no-redef]
        def decorator(func):
            return func

        if args and callable(args[0]):
            return args[0]
        return decorator


# 任务工作区：原始文件/产物的本地过渡目录（仅缓存，不传递路径）
DEFAULT_WORKSPACE = os.getenv("PARSING_WORKSPACE", "/tmp/parsing-workspace")

_TASK_NAME = "app.core.tasks.document_ingestion_tasks.parse_task"


def _resolve_job_input(job_id: str, s3_key: str | None) -> tuple[str, str]:
    """定位原始文件：优先按 s3_key 从 ArtifactStorage 拉取，否则查本地工作区。"""
    if s3_key:
        data = get_artifact_storage().get_object(s3_key)
        filename = os.path.basename(s3_key) or "original.bin"
        local_path = os.path.join(DEFAULT_WORKSPACE, job_id, filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as file:
            file.write(data)
        return local_path, filename

    job_dir = os.path.join(DEFAULT_WORKSPACE, job_id)
    if not os.path.isdir(job_dir):
        raise FileNotFoundError(f"Job workspace not found: {job_dir}")
    for name in sorted(os.listdir(job_dir)):
        if name.startswith("original."):
            return os.path.join(job_dir, name), name
    raise FileNotFoundError(f"No original file in job workspace: {job_dir}")


def upload_artifacts(output_dir: str, *, namespace: str, document_id: str) -> str:
    """把本地产物目录上传到共享存储，返回 artifact_prefix（<namespace>/<document_id>）。"""
    storage = get_artifact_storage()
    prefix = f"{namespace}/{document_id}"
    for root, _dirs, files in os.walk(output_dir):
        for name in files:
            full_path = os.path.join(root, name)
            relative = os.path.relpath(full_path, output_dir)
            with open(full_path, "rb") as file:
                storage.put_object(f"{prefix}/{relative}", file.read())
    return prefix


def _parse_task_impl(
    job_id: str,
    user_id: str = "",
    job_type: str = "document_ingestion",
    tenant_id: str = "default",
    namespace: str = "",
    s3_key: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """解析任务：拉原始文件 → document_parser.parse_job → 产物上传共享存储。

    与 worker_dispatcher.py 的派发契约对齐：args=[job_id]，kwargs={user_id, job_type}；
    tenant_id / namespace / s3_key 由 API 层鉴权后透传，用于数据隔离。
    """
    namespace = namespace or tenant_id
    file_full_path, filename = _resolve_job_input(job_id, s3_key)
    output_dir = os.path.join(DEFAULT_WORKSPACE, job_id, "output")
    _result, state = parse_job(
        file_full_path=file_full_path,
        filename=filename,
        output_dir=output_dir,
        job_id=job_id,
    )

    document_id: str | None = None
    local_artifacts = os.path.join(output_dir, filename)
    manifest_path = os.path.join(local_artifacts, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as file:
            document_id = json.load(file).get("document_id")

    artifact_prefix = upload_artifacts(
        local_artifacts,
        namespace=namespace,
        document_id=document_id or "unknown",
    )

    return {
        "job_id": job_id,
        "status": state.status.value,
        "document_id": document_id,
        "artifact_prefix": artifact_prefix,
        "output_dir": local_artifacts,
    }


parse_task = (
    _celery_shared_task(name=_TASK_NAME)(_parse_task_impl)
    if _CELERY_AVAILABLE
    else _parse_task_impl
)


def upload_url_file_task(
    job_id: str,
    url: str,
    user_id: str = "",
    **_: Any,
) -> dict[str, Any]:
    """URL 上传任务（creation_service 引用）。

    TODO: 校验 URL → 下载到工作区 → 复用 parse_task；URL 安全校验见
    shared.services.http.url_security。
    """
    raise NotImplementedError("upload_url_file_task is not implemented in the MVP")
