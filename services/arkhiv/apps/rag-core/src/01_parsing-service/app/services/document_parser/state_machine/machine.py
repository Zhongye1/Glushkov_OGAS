"""任务级状态机（设计文档 03 §3-§8）。

参考实现没有任务级 FSM（只有管线线性流），本骨架按设计补齐。落地 DB 时把
JobState 映射为 job 表、迁移落库即可；幂等/租约/重试见设计文档。
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.document_parser.state_machine.states import (
    TERMINAL_STATUSES,
)
from shared.contracts.parsing import JobState, JobStatus


class IllegalTransitionError(ValueError):
    def __init__(self, current: JobStatus, target: JobStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Illegal job transition: {current.value} -> {target.value}")


# 迁移表（设计文档 03 §3）：done / failed / cancelled 为终态
TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.PENDING: frozenset(
        {JobStatus.WAITING_FILE, JobStatus.RUNNING, JobStatus.CANCELLED}
    ),
    JobStatus.WAITING_FILE: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED}),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.CONVERTING,
            JobStatus.DONE,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }
    ),
    JobStatus.CONVERTING: frozenset(
        {JobStatus.RUNNING, JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
    JobStatus.DONE: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


class JobStateMachine:
    """校验并执行状态迁移；非法迁移抛 IllegalTransitionError。"""

    def can_transition(self, current: JobStatus, target: JobStatus) -> bool:
        return target in TRANSITIONS.get(current, frozenset())

    def transition(
        self,
        state: JobState,
        target: JobStatus,
        *,
        stage: str | None = None,
        attempt: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> JobState:
        if not self.can_transition(state.status, target):
            raise IllegalTransitionError(state.status, target)
        now = datetime.now(UTC)
        started_at = state.started_at
        if target is JobStatus.RUNNING and started_at is None:
            started_at = now
        completed_at = state.completed_at
        if target in TERMINAL_STATUSES:
            completed_at = now
        return JobState(
            job_id=state.job_id,
            status=target,
            stage=stage if stage is not None else state.stage,
            attempt=attempt if attempt is not None else state.attempt,
            error_code=error_code if error_code is not None else state.error_code,
            error_message=error_message if error_message is not None else state.error_message,
            created_at=state.created_at,
            started_at=started_at,
            completed_at=completed_at,
        )
