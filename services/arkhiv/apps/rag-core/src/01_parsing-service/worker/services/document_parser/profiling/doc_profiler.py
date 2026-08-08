"""文档画像（参考实现移植简化）。

MVP 只做轻量探测：PDF 用 PyMuPDF 拿页数与加密状态；DOC_AGENT 解剖（anatomy、
routing_category）为后续接入点，MVP 一律为 None。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentProfile:
    filename: str
    page_count: int | None = None
    encrypted: bool = False
    routing_category: str | None = None
    anatomy: Any = None
    extra: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"{self.filename} pages={self.page_count} encrypted={self.encrypted} "
            f"routing={self.routing_category}"
        )


def profile_document(
    file_full_path: str,
    internal_output_filename: str | None = None,
    job_id: str | None = None,
    output_dir: str | None = None,
) -> DocumentProfile:
    profile = DocumentProfile(filename=os.path.basename(file_full_path))
    extension = os.path.splitext(file_full_path)[1].lower()
    if extension != ".pdf":
        return profile
    try:
        import pymupdf  # 惰性导入
    except ImportError:
        return profile
    try:
        doc = pymupdf.open(file_full_path)
        profile.page_count = doc.page_count
        profile.encrypted = bool(doc.needs_pass)
        doc.close()
    except Exception:
        # 损坏 PDF：让提取阶段给出 CORRUPTED 错误码
        return profile
    return profile
