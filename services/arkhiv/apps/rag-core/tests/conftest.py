"""pytest 全局配置：把解析 worker 包注入 sys.path。"""

from __future__ import annotations

import sys
from pathlib import Path

PARSING_SERVICE = Path(__file__).resolve().parents[1] / "src" / "01_parsing-service"
if str(PARSING_SERVICE) not in sys.path:
    sys.path.insert(0, str(PARSING_SERVICE))
