"""Markdown 行扫描状态机：标题栈、基准级归一、同名去重、IR 输出。"""

from __future__ import annotations

from worker.services.document_parser.formats.markdown.heading import md_heading_match
from worker.services.document_parser.formats.markdown.parse_state import (
    MarkdownParseState,
    escape_path_segment,
)
from worker.services.document_parser.formats.markdown.row_updater import update_df_list


def _new_state(relative_root: str = "doc") -> MarkdownParseState:
    return MarkdownParseState(
        relative_root=relative_root,
        split_char="/",
        llm_parameters={},
        timestamp="2026-01-01T00:00:00",
        row_updater=update_df_list,
    )


def test_heading_path_builds_with_root() -> None:
    state = _new_state(relative_root="doc")
    state.enter_heading("第一章", 1)
    assert state.path == "doc/第一章"
    state.enter_heading("第一节", 2)
    assert state.path == "doc/第一章/第一节"


def test_base_level_normalization_from_h2() -> None:
    state = _new_state(relative_root="doc")
    state.enter_heading("第一节", 2)  # H2 起步
    assert state.base_level == 2
    assert state.path == "doc/第一节"  # adjusted level 1，无多余层级


def test_heading_dedup_appends_suffix() -> None:
    state = _new_state(relative_root="doc")
    state.enter_heading("第一章", 1)
    state.enter_heading("第一章", 1)
    state.enter_heading("第一节", 2)
    assert state.path == "doc/第一章_2/第一节"
    assert state.path_stack[0][0] == "第一章_2"
    assert state.path_stack[1][0] == "第一节"


def test_escape_path_segment() -> None:
    assert escape_path_segment("a/b") == "a\\/b"
    assert escape_path_segment("a\\b") == "a\\\\b"
    assert escape_path_segment("  标题  ") == "标题"


def test_record_page_marker() -> None:
    state = _new_state()
    assert state.record_page_marker("<!--page-->")
    assert state.record_page_marker("<!-- Slide number 3 -->")
    assert not state.record_page_marker("普通段落 <!-- 注释 -->")
    assert not state.record_page_marker("## 标题")


def test_to_blocks_emits_headings_and_content() -> None:
    state = _new_state(relative_root="doc")
    state.enter_heading("第一章", 1)
    state.append_plain_text("正文段落")
    state.flush_current_content()
    state.append_row(
        [
            "![图注](x.png)",
            state.path,
            "image",
            8,
            "", "", "", "", "",
            state.timestamp,
            "", "", "",
        ]
    )
    state.append_row(
        [
            "[TABLE table-1](tables/table-1.html)",
            state.path,
            "table",
            10,
            "", "", "", "", "",
            state.timestamp,
            "", "", "",
        ]
    )

    blocks = state.to_blocks(document_id="doc")
    types = [block.type for block in blocks]
    assert types == ["heading", "paragraph", "image", "table"]
    heading = blocks[0]
    assert heading.level == 1
    assert heading.section_path == "doc/第一章"
    assert heading.content["text"] == "第一章"
    assert blocks[1].section_path == "doc/第一章"
    assert blocks[2].content["src"] == "x.png"
    assert blocks[3].content["html_path"] == "tables/table-1.html"


def test_md_heading_match_pairs_with_enter() -> None:
    text, level = md_heading_match("## 小节")
    state = _new_state(relative_root="doc")
    state.enter_heading(text, level)
    assert state.path == "doc/小节"
