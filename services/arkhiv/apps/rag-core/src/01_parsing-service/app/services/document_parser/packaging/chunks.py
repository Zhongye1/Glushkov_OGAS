"""层级锚定分块（设计文档 01 §6 + 05 §3.2）。

chunk 由完整 block 组成，绝不在表格/图片/代码块中间切断；每节一个父 chunk
（正文聚合），表格/图片独立成子 chunk（small-to-big 的 parent 链）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.document_parser.ir.blocks import Block

MAX_CHUNK_CHARS = 1500
_SECTION_BLOCK_TYPES = frozenset(
    {"paragraph", "list", "code_block", "quote", "callout", "footnote"}
)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    type: str
    section_path: str
    block_ids: tuple[str, ...]
    text: str
    parent_chunk_id: str | None = None
    page: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "type": self.type,
            "section_path": self.section_path,
            "parent_chunk_id": self.parent_chunk_id,
            "block_ids": list(self.block_ids),
            "page": self.page,
            "text": self.text,
        }


def build_chunks(
    blocks: list[Block] | tuple[Block, ...],
    document_id: str,
) -> list[Chunk]:
    """按标题锚定分块：每节一个父 chunk + 表格/图片独立子 chunk。"""
    chunks: list[Chunk] = []
    counter = 0
    section_blocks: list[Block] = []
    section_path = ""
    section_page: int | None = None

    def next_chunk_id() -> str:
        nonlocal counter
        chunk_id = f"{document_id}-c{counter:04d}"
        counter += 1
        return chunk_id

    def flush_section() -> None:
        nonlocal section_blocks
        if not section_blocks:
            return
        text = _blocks_text(section_blocks)
        if not text:
            return
        chunks.append(
            Chunk(
                chunk_id=next_chunk_id(),
                type="text",
                section_path=section_path,
                block_ids=tuple(block.id for block in section_blocks),
                text=text,
                parent_chunk_id=None,
                page=section_page,
            )
        )
        section_blocks = []

    for block in blocks:
        if block.type == "heading":
            flush_section()
            section_path = block.section_path
            section_page = block.page
            continue

        if block.type in ("table", "image"):
            flush_section()
            parent = chunks[-1] if chunks else None
            parent_id = (
                parent.chunk_id
                if parent is not None and parent.parent_chunk_id is None
                else None
            )
            chunks.append(
                Chunk(
                    chunk_id=next_chunk_id(),
                    type=block.type,
                    section_path=block.section_path,
                    block_ids=(block.id,),
                    text=block.text,
                    parent_chunk_id=parent_id,
                    page=block.page,
                )
            )
            continue

        if block.type in _SECTION_BLOCK_TYPES:
            if not section_path:
                section_path = block.section_path
            if section_page is None:
                section_page = block.page
            section_blocks.append(block)
            if sum(len(b.text) for b in section_blocks) >= MAX_CHUNK_CHARS:
                flush_section()

    flush_section()
    return chunks


def _blocks_text(blocks: list[Block]) -> str:
    return "\n".join(block.text for block in blocks if block.text).strip()
