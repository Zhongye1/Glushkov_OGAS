"""解析输出契约（参考实现移植 + 设计 IR）。

blocks 是对外 IR（Block 列表）；parsed_df 是 ParsedRow/DataFrame 存储视图，
需要 pandas 时才惰性生成。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.document_parser.ir.blocks import Block


@dataclass(frozen=True)
class ParseOutput:
    output_dir: str
    blocks: tuple[Block, ...] = ()
    parsed_df: Any = None  # pd.DataFrame | None

    @property
    def rows_count(self) -> int:
        return len(self.blocks)

    def with_blocks(self, blocks: tuple[Block, ...]) -> ParseOutput:
        return ParseOutput(output_dir=self.output_dir, blocks=blocks, parsed_df=self.parsed_df)

    def with_dataframe(self, parsed_df: Any) -> ParseOutput:
        return ParseOutput(output_dir=self.output_dir, blocks=self.blocks, parsed_df=parsed_df)
