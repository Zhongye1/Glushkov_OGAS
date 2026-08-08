"""Markdown 标题检测与表格渲染（Phase A 规则版）。"""

from __future__ import annotations

from worker.services.document_parser.formats.markdown.heading import (
    eval_md_headings,
    md_heading_match,
)
from worker.services.document_parser.formats.markdown.parser import md_table_to_html


def test_atx_heading_match() -> None:
    assert md_heading_match("# 标题") == ("标题", 1)
    assert md_heading_match("### 三级") == ("三级", 3)
    assert md_heading_match("不是标题") == ("", -1)


def test_numbered_heading_fallback() -> None:
    assert md_heading_match("1. 第一章")[1] == 1
    assert md_heading_match("1.2 小节")[1] == 2
    assert md_heading_match("1.2.3 三级")[1] == 3
    # 纯数字行不当作标题
    assert md_heading_match("2026.08.08") == ("", -1)


def test_eval_md_headings_normalizes_numbered() -> None:
    lines = [
        "# 已有标题",
        "",
        "1. 编号标题",
        "1.1 子标题",
        "普通正文",
    ]
    normalized = eval_md_headings(lines, source_type="md")
    assert normalized == [
        "# 已有标题",
        "# 编号标题",
        "## 子标题",
        "普通正文",
    ]


def test_md_table_to_html() -> None:
    lines = [
        "| a | b |",
        "|---|---|",
        "| 1 | <x> |",
    ]
    html = md_table_to_html(lines)
    assert "<table>" in html
    assert "<th>a</th>" in html
    assert "<td>&lt;x&gt;</td>" in html
    assert "|---|---|" not in html


def test_md_table_to_html_empty() -> None:
    assert md_table_to_html([]) == ""
