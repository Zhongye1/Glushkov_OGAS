"""产物 manifest（设计文档 05 §3.1，字段对齐参考产物 manifest.json）。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_document_id(source_name: str, page_count: int | None) -> str:
    """document_id 由 source_name + page_count 派生，内容不变则 id 稳定。"""
    digest = hashlib.sha1(f"{source_name}:{page_count}".encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"


@dataclass(frozen=True)
class Manifest:
    version: str = "2.0"
    job_id: str | None = None
    document_id: str = ""
    source_name: str = ""
    page_count: int | None = None
    billing_status: str = "pending"
    cost_micro_dollars: int = 0
    credits: float = 0.0
    started_at: str = ""
    completed_at: str = ""
    duration_ms: int = 0
    stages_timing_ms: dict[str, int] = field(default_factory=dict)
    token_usage: dict[str, int] = field(default_factory=dict)
    statistics: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "job_id": self.job_id,
            "document_id": self.document_id,
            "source_name": self.source_name,
            "processing": {
                "page_count": self.page_count,
                "billing_status": self.billing_status,
                "cost": {
                    "micro_dollars": self.cost_micro_dollars,
                    "credits": self.credits,
                },
                "timing": {
                    "started_at": self.started_at,
                    "completed_at": self.completed_at,
                    "duration_ms": self.duration_ms,
                },
                "stages": {
                    "timing_ms": self.stages_timing_ms,
                    "token_usage": self.token_usage,
                },
            },
            "statistics": self.statistics,
        }


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
