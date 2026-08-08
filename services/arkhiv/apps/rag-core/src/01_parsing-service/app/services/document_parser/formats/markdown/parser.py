"""Markdown 适配器：Phase A（标题归一）+ Phase B（行扫描状态机）。

参考实现 formats/markdown/parser.py 的重构骨架：去掉 LLM TOC 检测、LLM 标题
预测、图片/表格 LLM 摘要，保留 Phase A/B 结构与 MarkdownParseState 引擎。
"""

from __future__ import annotations

import os
import re

from app.services.document_parser.formats.markdown.heading import (
    MD_IMAGE_PATTERN,
    eval_md_headings,
    md_heading_match,
)
from app.services.document_parser.formats.markdown.parse_state import MarkdownParseState
from app.services.document_parser.formats.markdown.row_updater import update_df_list
from app.services.document_parser.ir.blocks import Block
from app.services.document_parser.support.identifiers import get_str_time
from app.services.document_parser.support.stage_profiler import stage_timer


def parse_md(
    output_dir: str,
    source_type: str,
    file_path: str | None = None,
    md_lines: list[str] | None = None,
    base_llm_paras: dict | None = None,
    relative_root: str | None = None,
    toc_hierarchies: list | None = None,
    lines_with_heading: list[str] | None = None,
    is_first_shard: bool = True,
    skip_toc_detection: bool = False,
) -> list[Block]:
    """解析 Markdown（或归 md 的行）为 IR Block 列表。"""
    base_llm_paras = base_llm_paras or {}
    relative_root = relative_root or ""

    if lines_with_heading is None:
        # ── Phase A：TOC 检测（LLM，MVP 跳过）+ 标题归一 ──
        if md_lines is None and file_path is not None:
            with open(file_path, encoding="utf-8") as file:
                md_lines = file.read().splitlines()
        md_lines = [line.strip() for line in (md_lines or []) if line.strip()]

        if toc_hierarchies is not None:
            _write_toc_hierarchies(output_dir, toc_hierarchies)
        elif not skip_toc_detection:
            # TODO: 参考实现 detect_tocs_in_texts（LLM 目录检测）；MVP 跳过
            pass

        with stage_timer(
            "md.predict_headings",
            line_count=len(md_lines),
            smart_parse=base_llm_paras.get("smart_title_parse", True),
        ):
            lines_with_heading = eval_md_headings(md_lines, source_type)

    # ── Phase B：MarkdownParseState 遍历 ──
    tables_dir = os.path.join(output_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    parser_state = MarkdownParseState(
        relative_root=relative_root,
        split_char="/",
        llm_parameters=base_llm_paras,
        timestamp=get_str_time(),
        row_updater=update_df_list,
    )

    index = 0
    while index < len(lines_with_heading):
        line = lines_with_heading[index]

        if parser_state.record_page_marker(line):
            index += 1
            continue

        current_heading, current_heading_level = md_heading_match(line, as_is=False)
        if current_heading_level != -1:
            if parser_state.content_items:
                parser_state.flush_current_content()
            elif parser_state.path and parser_state.path != relative_root:
                parser_state.flush_placeholder_chunk()
            parser_state.enter_heading(current_heading, current_heading_level)
            index += 1
            continue

        # 图片行 → 独立 image 行（MVP 不下载/不摘要，只记录引用）
        image_matches = MD_IMAGE_PATTERN.findall(line)
        if image_matches:
            for caption, src in image_matches:
                parser_state.append_row(
                    [
                        f"![{caption}]({src})",
                        parser_state.path,
                        "image",
                        len(src),
                        "",
                        "",
                        "",
                        "",
                        "",
                        parser_state.timestamp,
                        "",
                        "",
                        "",
                    ]
                )
            index += 1
            continue

        # 表格行 → 累积到表格结束，写 tables/table-N.html 并落一行
        if line.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines_with_heading) and (
                lines_with_heading[index].startswith("|")
                or _is_table_separator(lines_with_heading[index])
            ):
                table_lines.append(lines_with_heading[index])
                index += 1
            table_html = md_table_to_html(table_lines)
            table_name = f"table-{parser_state.table_count}"
            with open(
                os.path.join(tables_dir, f"{table_name}.html"),
                "w",
                encoding="utf-8",
            ) as file:
                file.write(table_html)
            content_ref = f"[TABLE {table_name}](tables/{table_name}.html)"
            parser_state.append_row(
                [
                    content_ref,
                    parser_state.path,
                    "table",
                    len(table_html),
                    "",
                    "",
                    "",
                    "",
                    "",
                    parser_state.timestamp,
                    "",
                    "",
                    "",
                ]
            )
            parser_state.table_count += 1
            continue

        parser_state.append_plain_text(line)
        index += 1

    if parser_state.content_items:
        parser_state.flush_current_content()

    # TODO: apply_markdown_deferred_summaries（LLM 摘要，MVP 跳过）
    with stage_timer("md.build_dataframe", row_count=len(parser_state.rows)):
        return parser_state.to_blocks()


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if "-" not in stripped:
        return False
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", stripped))


def md_table_to_html(lines: list[str]) -> str:
    """GFM 管道表格 → 简单 HTML 表格。"""
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip().strip("|")
        cells = [cell.strip() for cell in stripped.split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue  # 分隔行
        rows.append(cells)
    if not rows:
        return ""
    head, body = rows[0], rows[1:]
    html = ["<table>"]
    html.append("<thead><tr>" + "".join(f"<th>{_escape_html(c)}</th>" for c in head) + "</tr></thead>")
    if body:
        html.append("<tbody>")
        for row in body:
            html.append("<tr>" + "".join(f"<td>{_escape_html(c)}</td>" for c in row) + "</tr>")
        html.append("</tbody>")
    html.append("</table>")
    return "\n".join(html)


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _write_toc_hierarchies(output_dir: str, toc_hierarchies) -> None:
    import json

    path = os.path.join(output_dir, "toc_hierarchies.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(toc_hierarchies, file, ensure_ascii=False, indent=2)
