"""标识符与时间工具（参考实现移植简化）。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime


def gen_str_codes(source: str) -> str:
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]


def get_str_time() -> str:
    return datetime.now(UTC).isoformat()
