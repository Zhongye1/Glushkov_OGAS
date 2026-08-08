"""结构化阶段计时（参考实现移植简化：去掉 gevent/greenlet 依赖）。

阶段计时累积到线程本地 tracker，流水线结束时读入 manifest.stages.timing_ms。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

logger = logging.getLogger("document_parser.stage")

_tracker = threading.local()


def init_stage_tracker() -> dict[str, int]:
    tracker: dict[str, int] = {}
    _tracker.timings = tracker
    return tracker


def get_current_stage_tracker() -> dict[str, int] | None:
    return getattr(_tracker, "timings", None)


def get_stage_timings() -> dict[str, int]:
    return dict(getattr(_tracker, "timings", {}) or {})


def cleanup_stage_tracker() -> None:
    if hasattr(_tracker, "timings"):
        del _tracker.timings


@contextmanager
def stage_timer(stage: str, **fields: Any) -> Iterator[None]:
    """记录阶段耗时，不改变控制流；异常时照常抛出。"""
    start_time: float = perf_counter()
    try:
        yield
    except Exception:
        elapsed_ms: int = int((perf_counter() - start_time) * 1000)
        logger.warning("Stage failed: %s (%dms, %s)", stage, elapsed_ms, fields)
        raise
    elapsed_ms: int = int((perf_counter() - start_time) * 1000)
    tracker = get_current_stage_tracker()
    if tracker is not None:
        tracker[stage] = tracker.get(stage, 0) + elapsed_ms
    logger.debug("Stage completed: %s (%dms, %s)", stage, elapsed_ms, fields)
