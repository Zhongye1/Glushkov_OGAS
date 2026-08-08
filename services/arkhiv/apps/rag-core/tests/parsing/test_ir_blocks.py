"""IR 模型：Block 视图（markdown/nav/tree）与 ParsedRow 列契约（设计文档 01）。"""

from __future__ import annotations

import pytest
from worker.services.document_parser.ir.blocks import (
    Block,
    blocks_to_markdown,
    build_section_tree,
    make_block_id,
)
from worker.services.document_parser.ir.parsed_row import (
    PARSER_ROW_COLUMNS,
    ParsedRow,
    ParsedRowsBuilder,
)


def _block(order: int, block_type: str, *, level: int = 1, **content) -> Block:
    return Block(
        id=make_block_id("doc", order),
        type=block_type,
        order=order,
        content=content,
        level=level,
        section_path=f"doc/第{order}章",
    )


def test_make_block_id_format() -> None:
    assert make_block_id("doc_abc", 3) == "doc_abc-b0003"


def test_block_text_falls_back_across_content_keys() -> None:
    assert _block(0, "paragraph", text="正文").text == "正文"
    assert _block(1, "image", caption="图注", src="a.png").text == "图注"
    assert _block(2, "image", alt_text="alt").text == "alt"


def test_blocks_to_markdown_roundtrip() -> None:
    blocks = [
        _block(0, "heading", text="第一章", level=1),
        _block(1, "paragraph", text="正文段落"),
        _block(2, "list", items=["a", "b"]),
        _block(3, "table", text="[TABLE table-1](tables/table-1.html)"),
        _block(4, "image", caption="图", src="images/x.png"),
        _block(5, "code_block", text="print(1)", lang="python"),
    ]
    md = blocks_to_markdown(blocks)
    assert "# 第一章" in md
    assert "正文段落" in md
    assert "- a" in md and "- b" in md
    assert "tables/table-1.html" in md
    assert "![图](images/x.png)" in md
    assert "```python" in md


def test_build_section_tree_nesting() -> None:
    blocks = [
        _block(0, "heading", text="A"),
        _block(1, "heading", text="A1", level=2),
        _block(2, "paragraph", text="正文"),
        _block(3, "heading", text="B"),
    ]
    tree = build_section_tree(blocks)
    assert [node["title"] for node in tree] == ["A", "B"]
    assert tree[0]["children"][0]["title"] == "A1"


def test_parsed_row_to_list_matches_columns() -> None:
    row = ParsedRow(
        content="内容",
        path="doc/第一章",
        type="text",
        know_id="k1",
        addtime="2026-01-01",
        length=2,
    )
    values = row.to_list()
    assert len(values) == len(PARSER_ROW_COLUMNS)
    assert dict(zip(PARSER_ROW_COLUMNS, values, strict=True))["content"] == "内容"


def test_parsed_rows_builder_roundtrip() -> None:
    pytest.importorskip("pandas")
    builder = ParsedRowsBuilder()
    builder.append(
        ParsedRow(content="第一行", path="doc/甲", type="text", know_id="k1", addtime="t")
    )
    builder.append(
        ParsedRow(content="第二行", path="doc/乙", type="text", know_id="k2", addtime="t")
    )
    frame = builder.to_dataframe()
    assert list(frame.columns) == PARSER_ROW_COLUMNS
    assert len(frame) == 2
    assert frame.iloc[0]["content"] == "第一行"
