"""层级锚定分块：父 chunk + 表格/图片子 chunk 父链（设计文档 05）。"""

from __future__ import annotations

from worker.services.document_parser.ir.blocks import Block, make_block_id
from worker.services.document_parser.packaging.chunks import MAX_CHUNK_CHARS, build_chunks


def _block(order: int, block_type: str, section_path: str, text: str = "") -> Block:
    return Block(
        id=make_block_id("doc", order),
        type=block_type,
        order=order,
        section_path=section_path,
        content={"text": text},
        level=1,
        page=1,
    )


def test_section_text_chunk_then_children() -> None:
    blocks = [
        _block(0, "heading", "doc/第一章", "第一章"),
        _block(1, "paragraph", "doc/第一章", "正文一"),
        _block(2, "table", "doc/第一章", "[TABLE table-1](tables/table-1.html)"),
        _block(3, "image", "doc/第一章", "![图](x.png)"),
    ]
    chunks = build_chunks(blocks, "doc")
    types = [chunk.type for chunk in chunks]
    assert types == ["text", "table", "image"]

    parent = chunks[0]
    assert parent.parent_chunk_id is None
    assert parent.block_ids == ("doc-b0001",)
    assert parent.section_path == "doc/第一章"

    table_chunk, image_chunk = chunks[1], chunks[2]
    assert table_chunk.parent_chunk_id == parent.chunk_id
    assert image_chunk.parent_chunk_id == parent.chunk_id
    assert table_chunk.block_ids == ("doc-b0002",)


def test_new_heading_flushes_section() -> None:
    blocks = [
        _block(0, "heading", "doc/甲", "甲"),
        _block(1, "paragraph", "doc/甲", "甲正文"),
        _block(2, "heading", "doc/乙", "乙"),
        _block(3, "paragraph", "doc/乙", "乙正文"),
    ]
    chunks = build_chunks(blocks, "doc")
    assert len(chunks) == 2
    assert [chunk.section_path for chunk in chunks] == ["doc/甲", "doc/乙"]
    assert chunks[0].text == "甲正文"
    assert chunks[1].text == "乙正文"


def test_long_section_splits_by_max_chars() -> None:
    long_text = "字" * (MAX_CHUNK_CHARS + 10)
    blocks = [
        _block(0, "heading", "doc/长", "长"),
        _block(1, "paragraph", "doc/长", long_text),
        _block(2, "paragraph", "doc/长", long_text),
    ]
    chunks = build_chunks(blocks, "doc")
    # block 是原子单元，单个超长 block 不切断；多 block 累积触发切分
    assert len(chunks) == 2
    assert all(chunk.type == "text" for chunk in chunks)


def test_empty_section_produces_no_chunk() -> None:
    blocks = [_block(0, "heading", "doc/空", "空")]
    assert build_chunks(blocks, "doc") == []
