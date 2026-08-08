"""PDF 文本提供器（替代参考实现的 MinerU provider，设计文档 04）。

MVP 用 PyMuPDF 文本层抽取；接入 MinerU 时实现同一 Protocol 即可（参考实现
parse_via_full）。extract 返回「md 风格行」，供 Markdown 状态机消费。
"""

from __future__ import annotations

from typing import Protocol


class PdfTextProvider(Protocol):
    def extract_text_lines(
        self,
        pdf_path: str,
        *,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> list[str]: ...


class PyMuPDFProvider:
    """PyMuPDF 文本层抽取：页内 block 按坐标（top→bottom, left→right）排序。"""

    def extract_text_lines(
        self,
        pdf_path: str,
        *,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> list[str]:
        import pymupdf  # 惰性导入

        doc = pymupdf.open(pdf_path)
        lines: list[str] = []
        start = page_start or 0
        end = page_end if page_end is not None else doc.page_count
        try:
            for page_number in range(start, min(end, doc.page_count)):
                page = doc.load_page(page_number)
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda block: (round(block[1], 1), block[0]))
                for block in blocks:
                    text = str(block[4]).strip()
                    if text:
                        lines.append(text)
        finally:
            doc.close()
        return lines


def get_pdf_provider() -> PdfTextProvider:
    """工厂：返回当前启用的文本提供器。

    TODO: 接入 MinerU provider（参考实现 parse_via_full），支持 S3 对象与
    分片并行。
    """
    return PyMuPDFProvider()
