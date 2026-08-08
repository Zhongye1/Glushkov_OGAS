"""解析任务契约（设计文档 03）：API ↔ worker 队列消息 + 任务状态。

worker 架构约定：API 层完成鉴权后，把授权结果（tenant_id / namespace /
s3_key）作为任务消息字段透传，worker 只信任本契约、不做用户鉴权。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal


class JobStatus(str, Enum):
    PENDING = "pending"
    WAITING_FILE = "waiting-file"
    RUNNING = "running"
    CONVERTING = "converting"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}
)


@dataclass(frozen=True)
class JobState:
    """任务运行态：API 落 job 表、worker 回写共用同一结构。"""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    stage: str = ""
    attempt: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class ParseJob:
    """解析任务消息：API 鉴权后发布进队列的唯一载荷（worker 的输入契约）。

    与 worker_dispatcher 的派发对齐：args=[job_id]，kwargs={user_id, job_type,
    tenant_id, namespace, s3_key, ...}；source_type 区分 file / url。
    """

    job_id: str
    source_type: Literal["file", "url"] = "file"
    file_name: str | None = None
    s3_key: str | None = None
    source_url: str | None = None
    user_id: str = ""
    tenant_id: str = "default"
    namespace: str = ""
    job_type: str = "document_ingestion"
    document_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转成可 JSON 序列化的队列消息（枚举落为字面量）。"""
        return {
            "job_id": self.job_id,
            "source_type": self.source_type,
            "file_name": self.file_name,
            "s3_key": self.s3_key,
            "source_url": self.source_url,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "namespace": self.namespace,
            "job_type": self.job_type,
            "document_id": self.document_id,
            "metadata": self.metadata,
        }
