"""解析任务状态定义（设计文档 03 §2）。

契约在 ``shared.contracts.parsing``（API 与 worker 共享），本模块只做再导出，
保持 ``worker.services.document_parser`` 内部引用路径不变。
"""

from __future__ import annotations

from shared.contracts.parsing import TERMINAL_STATUSES, JobStatus

__all__ = ["TERMINAL_STATUSES", "JobStatus"]
