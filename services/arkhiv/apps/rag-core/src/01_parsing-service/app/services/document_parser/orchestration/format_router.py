"""格式枚举与路由注册表（参考实现移植；MVP 仅注册 PDF/Markdown）。"""

from __future__ import annotations

import os
from enum import StrEnum

from app.services.document_parser.orchestration.errors import UnsupportedFormatError
from app.services.document_parser.orchestration.format_adapters import (
    DocumentParseAdapter,
    MarkdownParseAdapter,
    PdfParseAdapter,
)


class DocumentFormat(StrEnum):
    TEXT = "text"
    FRAGMENT = "fragment"
    IMAGE = "image"
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    PPTX = "pptx"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


SUPPORTED_FILE_TYPES: tuple[str, ...] = (
    ".txt",
    ".fragment",
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".pptx",
    ".md",
    ".html",
    ".htm",
    ".json",
)

_EXTENSION_TO_FORMAT: dict[str, DocumentFormat] = {
    ".fragment": DocumentFormat.FRAGMENT,
    ".txt": DocumentFormat.TEXT,
    ".png": DocumentFormat.IMAGE,
    ".jpg": DocumentFormat.IMAGE,
    ".jpeg": DocumentFormat.IMAGE,
    ".pdf": DocumentFormat.PDF,
    ".doc": DocumentFormat.DOC,
    ".docx": DocumentFormat.DOCX,
    ".xls": DocumentFormat.XLS,
    ".xlsx": DocumentFormat.XLSX,
    ".pptx": DocumentFormat.PPTX,
    ".md": DocumentFormat.MARKDOWN,
    ".json": DocumentFormat.JSON,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
}


def resolve_document_format(file_path: str) -> DocumentFormat:
    extension = os.path.splitext(file_path)[1].lower()
    document_format = _EXTENSION_TO_FORMAT.get(extension)
    if document_format is None:
        raise UnsupportedFormatError(
            f"Unsupported file type: {extension} "
            f"(must be one of: {', '.join(SUPPORTED_FILE_TYPES)})"
        )
    return document_format


# MVP 注册表：新增格式 = 新增适配器 + 注册一行（设计文档 02 §4）
_ADAPTER_BY_FORMAT: dict[DocumentFormat, DocumentParseAdapter] = {
    DocumentFormat.PDF: PdfParseAdapter(document_format=DocumentFormat.PDF),
    DocumentFormat.MARKDOWN: MarkdownParseAdapter(
        document_format=DocumentFormat.MARKDOWN
    ),
}


def get_document_parse_adapter(
    document_format: DocumentFormat,
) -> DocumentParseAdapter:
    adapter = _ADAPTER_BY_FORMAT.get(document_format)
    if adapter is None:
        raise UnsupportedFormatError(
            f"No adapter registered for {document_format.value} "
            "(MVP ships PDF/Markdown only)"
        )
    return adapter
