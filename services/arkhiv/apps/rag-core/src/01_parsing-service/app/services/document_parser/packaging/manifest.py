"""产物 manifest 构建（设计文档 05 §3.1）。

Manifest 形状契约在 ``shared.contracts.artifact``（API 读取产物时按同一结构
解析），本模块只负责从流水线阶段计时与分块统计构建实例。
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from shared.contracts.artifact import Manifest


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def make_document_id(source_name: str, page_count: int | None) -> str:
    """document_id 由 source_name + page_count 派生，内容不变则 id 稳定。"""
    digest = hashlib.sha1(f"{source_name}:{page_count}".encode()).hexdigest()[:12]
    return f"doc_{digest}"


def build_manifest(
    *,
    job_id: str | None,
    document_id: str,
    source_name: str,
    page_count: int | None,
    chunks: list,
    timings: dict[str, int],
    started_at: str | None = None,
    completed_at: str | None = None,
) -> Manifest:
    """从流水线阶段计时与分块统计构建 manifest（结算以 manifest 为准）。"""
    started_at = started_at or _now_iso()
    completed_at = completed_at or _now_iso()
    duration_ms = 0
    try:
        delta = datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
        duration_ms = max(0, int(delta.total_seconds() * 1000))
    except ValueError:
        pass

    chunk_stats = {"total_chunks": 0, "text_chunks": 0, "image_chunks": 0, "table_chunks": 0}
    for chunk in chunks:
        chunk_stats["total_chunks"] += 1
        key = f"{chunk.type}_chunks"
        if key in chunk_stats:
            chunk_stats[key] += 1

    return Manifest(
        job_id=job_id,
        document_id=document_id,
        source_name=source_name,
        page_count=page_count,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        stages_timing_ms=dict(timings),
        statistics=chunk_stats,
    )
