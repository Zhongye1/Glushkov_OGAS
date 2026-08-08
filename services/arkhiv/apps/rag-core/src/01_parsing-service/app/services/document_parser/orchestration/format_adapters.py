"""适配器接口（设计文档 02 + 参考实现移植）。

DocumentParseAdapter 是 typing.Protocol（结构化 duck typing）；适配器只做
「ParseSession → 各格式解析函数 → ParseOutput」的翻译，不含业务逻辑。
解析实现全部在 parse() 方法体内懒加载，避免路由表加载时拉入重依赖。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.document_parser.orchestration.parse_output import ParseOutput
from app.services.document_parser.orchestration.parse_session import ParseSession


class DocumentParseAdapter(Protocol):
    @property
    def document_format(self) -> object:
        """本适配器处理的文档格式。"""

    def parse(self, session: ParseSession) -> ParseOutput:
        """把一个解析会话翻译成统一解析输出。"""
        raise NotImplementedError


@dataclass(frozen=True)
class MarkdownParseAdapter:
    document_format: object

    def parse(self, session: ParseSession) -> ParseOutput:
        from app.services.document_parser.formats.markdown.parser import parse_md

        blocks = parse_md(
            session.full_output_dir,
            source_type="md",
            file_path=session.file_full_path,
            base_llm_paras=session.base_llm_paras,
            relative_root=session.relative_root,
        )
        return ParseOutput(output_dir=session.full_output_dir, blocks=tuple(blocks))


@dataclass(frozen=True)
class PdfParseAdapter:
    document_format: object

    def parse(self, session: ParseSession) -> ParseOutput:
        from app.services.document_parser.formats.pdf.parser import parse_pdfs

        blocks = parse_pdfs(
            session.file_full_path,
            filename=session.filename,
            output_dir=session.full_output_dir,
            base_llm_paras=session.base_llm_paras,
            profile=session.profile,
            relative_root=session.relative_root,
            s3_key=session.s3_key,
            job_id=session.job_id,
        )
        return ParseOutput(output_dir=session.full_output_dir, blocks=tuple(blocks))
