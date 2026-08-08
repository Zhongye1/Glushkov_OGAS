"""解析 worker 任务入口（对接 worker_dispatcher.py 的派发契约）。

worker 与 FastAPI 编排解耦：任务队列 + 共享存储 key 传递产物。

注意：任务注册名固定为 ``app.core.tasks.document_ingestion_tasks.parse_task``
（Celery 按名字路由，与文件位置无关）。文件放在 document_parser 内是为了
当前可导入可测试——app/core/__init__.py 硬依赖尚未落地的 shared.* 包，
``app.core.tasks`` 路径暂时无法 import；shared 落地后可按需挪回。

MVP 骨架：Celery 可用时注册为 shared_task，否则保留纯函数直调；产物暂落
本地工作区，S3 传递接入见 TODO（设计文档 05 §4）。
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.services.document_parser.parse_service import parse_job

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


# 任务工作区：产物落到共享存储前，本地路径仅为 MVP 过渡
DEFAULT_WORKSPACE = os.getenv("PARSING_WORKSPACE", "/tmp/parsing-workspace")

_TASK_NAME = "app.core.tasks.document_ingestion_tasks.parse_task"


def _resolve_job_input(job_id: str) -> tuple[str, str]:
    """从工作区按 job_id 定位原始文件（<workspace>/<job_id>/original.<ext>）。

    TODO: 接入 JobFileResolver——从 job 记录读 s3_key，走 ArtifactStorage 拉取，
    产物按 <namespace>/<document_id>/... 写回共享存储（设计文档 05 §4）。
    """
    job_dir = os.path.join(DEFAULT_WORKSPACE, job_id)
    if not os.path.isdir(job_dir):
        raise FileNotFoundError(f"Job workspace not found: {job_dir}")
    for name in sorted(os.listdir(job_dir)):
        if name.startswith("original."):
            return os.path.join(job_dir, name), name
    raise FileNotFoundError(f"No original file in job workspace: {job_dir}")


def _parse_task_impl(
    job_id: str,
    user_id: str = "",
    job_type: str = "document_ingestion",
    **_: Any,
) -> dict[str, Any]:
    """解析任务：读原始文件 → document_parser.parse_job → 产物/状态。

    与 worker_dispatcher.py 的派发契约对齐：args=[job_id]，kwargs={user_id, job_type}。
    """
    file_full_path, filename = _resolve_job_input(job_id)
    output_dir = os.path.join(DEFAULT_WORKSPACE, job_id, "output")
    _result, state = parse_job(
        file_full_path=file_full_path,
        filename=filename,
        output_dir=output_dir,
        job_id=job_id,
    )

    document_id: str | None = None
    manifest_path = os.path.join(output_dir, filename, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as file:
            document_id = json.load(file).get("document_id")

    return {
        "job_id": job_id,
        "status": state.status.value,
        "document_id": document_id,
        "output_dir": os.path.join(output_dir, filename),
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
