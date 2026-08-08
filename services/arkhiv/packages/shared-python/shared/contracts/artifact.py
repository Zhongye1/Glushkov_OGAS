"""解析产物契约（设计文档 05 §3.1）：manifest.json 的共享结构。

worker 侧 packaging/manifest.py 负责构建与落盘；API 侧读取产物时按本契约
解析，两边不共享实现、只共享形状。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
