"""任务级状态机：迁移表、终态、非法迁移（设计文档 03）。"""

from __future__ import annotations

import pytest
from shared.contracts.parsing import TERMINAL_STATUSES, JobState, JobStatus
from worker.services.document_parser.state_machine.machine import (
    IllegalTransitionError,
    JobStateMachine,
)


def test_terminal_statuses_are_frozen() -> None:
    assert JobStatus.DONE in TERMINAL_STATUSES
    assert JobStatus.FAILED in TERMINAL_STATUSES
    assert JobStatus.CANCELLED in TERMINAL_STATUSES
    assert JobStatus.RUNNING not in TERMINAL_STATUSES


def test_legal_transitions() -> None:
    machine = JobStateMachine()
    assert machine.can_transition(JobStatus.PENDING, JobStatus.RUNNING)
    assert machine.can_transition(JobStatus.RUNNING, JobStatus.DONE)
    assert machine.can_transition(JobStatus.RUNNING, JobStatus.FAILED)
    assert machine.can_transition(JobStatus.CONVERTING, JobStatus.RUNNING)


def test_illegal_transition_raises() -> None:
    machine = JobStateMachine()
    state = JobState(job_id="j1", status=JobStatus.DONE)
    with pytest.raises(IllegalTransitionError) as exc_info:
        machine.transition(state, JobStatus.RUNNING)
    assert exc_info.value.current is JobStatus.DONE
    assert exc_info.value.target is JobStatus.RUNNING


def test_terminal_states_have_no_outgoing() -> None:
    machine = JobStateMachine()
    for status in TERMINAL_STATUSES:
        state = JobState(job_id="j1", status=status)
        for target in JobStatus:
            assert not machine.can_transition(state.status, target), (
                f"{status} should be terminal"
            )


def test_transition_records_stage_and_timestamps() -> None:
    machine = JobStateMachine()
    state = JobState(job_id="j1", status=JobStatus.PENDING)
    running = machine.transition(state, JobStatus.RUNNING, stage="route")
    assert running.status is JobStatus.RUNNING
    assert running.stage == "route"
    assert running.started_at is not None

    done = machine.transition(running, JobStatus.DONE, stage="done")
    assert done.status is JobStatus.DONE
    assert done.completed_at is not None


def test_transition_records_error() -> None:
    machine = JobStateMachine()
    state = JobState(job_id="j1", status=JobStatus.RUNNING)
    failed = machine.transition(
        state,
        JobStatus.FAILED,
        stage="failed",
        error_code="PARSE_FAILED",
        error_message="boom",
    )
    assert failed.error_code == "PARSE_FAILED"
    assert failed.error_message == "boom"
    assert failed.completed_at is not None


def test_job_state_is_frozen() -> None:
    state = JobState(job_id="j1")
    with pytest.raises(AttributeError):
        state.stage = "mutate"  # type: ignore[misc]
