"""解析任务状态定义（设计文档 03 §2）。"""

from __future__ import annotations

from enum import Enum


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
