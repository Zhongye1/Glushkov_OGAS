"""进程内 e2e：API 上传原文件 → parse_task 消费 → 产物包完整（设计文档 05 §4）。

不依赖 Redis/Celery/S3：走 parse_task 纯函数路径 + LocalArtifactStorage，
覆盖 worker 契约（s3_key 拉取、namespace 隔离、产物上传）。
"""

from __future__ import annotations

import json

from worker.services.document_parser.storage.artifact_storage import get_artifact_storage
from worker.services.document_parser.tasks import _parse_task_impl

_SAMPLE_MD = """\
# 第一章

这是第一章的正文段落。

## 第一节

| 名称 | 数量 |
|------|------|
| 苹果 | 3 |

![示意图](images/demo.png)
"""


def _configure(monkeypatch, tmp_path) -> tuple[str, str]:
    workspace = tmp_path / "ws"
    artifacts = tmp_path / "artifacts"
    workspace.mkdir()
    artifacts.mkdir()
    monkeypatch.setenv("PARSING_WORKSPACE", str(workspace))
    monkeypatch.setenv("ARTIFACT_STORAGE_LOCAL_ROOT", str(artifacts))
    return str(workspace), str(artifacts)


def test_e2e_parse_task_uploads_artifact_package(monkeypatch, tmp_path) -> None:
    _workspace, artifacts_root = _configure(monkeypatch, tmp_path)

    # API 侧：鉴权后把原文件传共享存储，任务消息携带 s3_key
    storage = get_artifact_storage()
    s3_key = "ns1/job_e2e/original.md"
    storage.put_object(s3_key, _SAMPLE_MD.encode("utf-8"))

    # worker 侧：消费任务消息（celery 未装时退化直调）
    result = _parse_task_impl(
        "job_e2e",
        user_id="u1",
        tenant_id="t1",
        namespace="ns1",
        s3_key=s3_key,
    )

    assert result["status"] == "done"
    assert result["document_id"].startswith("doc_")
    assert result["artifact_prefix"] == f"ns1/{result['document_id']}"
    assert result["job_id"] == "job_e2e"

    # 产物包完整性：manifest 最后写 = 完成标记
    prefix = result["artifact_prefix"]
    expected = {
        "full.md",
        "chunks.json",
        "doc_nav.json",
        "toc_hierarchies.json",
        "tables/table-1.html",
        "manifest.json",
    }
    actual = set()
    import os

    for root, _dirs, files in os.walk(artifacts_root):
        for name in files:
            relative = os.path.relpath(os.path.join(root, name), artifacts_root)
            actual.add(relative)
    assert {f"{prefix}/{name}" for name in expected} <= actual, (
        f"missing artifacts: {expected - actual}"
    )

    # manifest 内容对齐
    manifest = json.loads(
        storage.get_object(f"{prefix}/manifest.json").decode("utf-8")
    )
    assert manifest["job_id"] == "job_e2e"
    assert manifest["document_id"] == result["document_id"]
    assert manifest["statistics"]["total_chunks"] >= 1

    # chunks 父链：表格/图片子 chunk 挂在章节父 chunk 下
    chunks_payload = json.loads(
        storage.get_object(f"{prefix}/chunks.json").decode("utf-8")
    )
    parent_ids = {chunk["chunk_id"] for chunk in chunks_payload["chunks"]}
    for chunk in chunks_payload["chunks"]:
        if chunk["parent_chunk_id"] is not None:
            assert chunk["parent_chunk_id"] in parent_ids

    # full.md 包含标题与正文
    full_md = storage.get_object(f"{prefix}/full.md").decode("utf-8")
    assert "# 第一章" in full_md
    assert "第一节" in full_md


def test_e2e_parse_task_missing_s3_object_raises(monkeypatch, tmp_path) -> None:
    _configure(monkeypatch, tmp_path)
    try:
        _parse_task_impl("job_missing", s3_key="ns1/job_missing/original.md")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing s3 object should raise FileNotFoundError")


def test_e2e_tenant_defaults_to_namespace(monkeypatch, tmp_path) -> None:
    _workspace, artifacts_root = _configure(monkeypatch, tmp_path)
    storage = get_artifact_storage()
    storage.put_object("t9/job_tenant/original.md", "# 甲\n\n正文。\n".encode())

    result = _parse_task_impl("job_tenant", s3_key="t9/job_tenant/original.md", tenant_id="t9")

    assert result["artifact_prefix"].startswith("t9/")
    assert result["status"] == "done"
