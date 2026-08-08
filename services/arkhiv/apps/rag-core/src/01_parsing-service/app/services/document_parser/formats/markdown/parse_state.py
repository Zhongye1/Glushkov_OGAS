"""Markdown 行扫描状态机（参考实现移植）。

这是 Markdown/PDF（归 md）共用的解析引擎：栈 + 基准级归一 + 同名去重 +
延迟 LLM 任务。MVP 去掉 LLM 依赖，保留状态转移骨架；to_blocks() 把
positional rows 转成设计文档 01 的 IR Block 列表。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.services.document_parser.ir.blocks import Block, make_block_id
from app.services.document_parser.ir.parsed_row import (
    ParsedRow,
    ParsedRowsBuilder,
    process_dup_paths_df,
)

ParserRowValues = list[str | int]

RowUpdater = Callable[
    [list[ParserRowValues], list[str], str, dict[str, Any], str, str, int, bool],
    list[ParserRowValues],
]


@dataclass(frozen=True)
class DeferredSummaryTask:
    row_index: int
    content: str


def escape_path_segment(segment: str) -> str:
    """转义路径分隔符（先转义反斜杠，保证往返可逆），与参考实现一致。"""
    text = segment.strip()
    return text.replace("\\", "\\\\").replace("/", "\\/")


@dataclass
class MarkdownParseState:
    relative_root: str
    split_char: str
    llm_parameters: dict[str, Any]
    timestamp: str
    row_updater: RowUpdater
    rows: list[ParserRowValues] = field(default_factory=list)
    content_items: list[str] = field(default_factory=list)
    path_stack: list[tuple[str, int]] = field(default_factory=list)
    inner_paths: list[str] = field(default_factory=list)
    error_line_numbers: list[int] = field(default_factory=list)
    table_lines: list[str] = field(default_factory=list)
    base_level: int | None = None
    path: str = ""
    path_counter: dict[str, int] = field(default_factory=dict)
    deferred_llm_tasks: list[DeferredSummaryTask] = field(default_factory=list)
    seen_images: dict[str, dict[str, str]] = field(default_factory=dict)
    image_count: int = 1
    table_count: int = 1

    def __post_init__(self) -> None:
        if not self.path:
            self.path = self.relative_root

    def record_page_marker(self, line: str) -> bool:
        """识别并跳过 HTML 注释页标记（<!--page--> 等）。

        页码追踪已移除；未来由 page_memory 提供精确页码。
        """
        if "<!--" not in line or "-->" not in line:
            return False
        return "page" in line or "Slide number" in line

    def flush_current_content(self) -> None:
        self.rows = self.row_updater(
            self.rows,
            self.content_items,
            self.path,
            self.llm_parameters,
            self.timestamp,
            "",
            1500,
            True,
        )
        self.content_items = []

    def flush_placeholder_chunk(self) -> None:
        self.rows = self.row_updater(
            self.rows,
            [],
            self.path,
            self.llm_parameters,
            self.timestamp,
            "",
            1500,
            True,
        )

    def enter_heading(self, heading: str, level: int) -> None:
        if self.base_level is None:
            self.base_level = level
        elif level < self.base_level:
            self.base_level = level

        adjusted_level = level - self.base_level + 1
        self.path_stack = [
            (item_heading, item_level)
            for item_heading, item_level in self.path_stack
            if item_level < adjusted_level
        ]

        current_heading = escape_path_segment(heading)
        tentative_names = [item_heading for item_heading, _ in self.path_stack]
        tentative_names.append(current_heading)
        tentative_path_parts = [self.relative_root] if self.relative_root else []
        tentative_path_parts.extend(tentative_names)
        tentative_path = self.split_char.join(tentative_path_parts)

        if tentative_path in self.path_counter:
            self.path_counter[tentative_path] += 1
            current_heading = f"{current_heading}_{self.path_counter[tentative_path]}"
        else:
            self.path_counter[tentative_path] = 1

        self.path_stack.append((current_heading, adjusted_level))
        heading_names = [item_heading for item_heading, _ in self.path_stack]
        path_parts = [self.relative_root] if self.relative_root else []
        path_parts.extend(heading_names)
        self.inner_paths.append(self.split_char.join(heading_names))
        self.path = self.split_char.join(path_parts)

    def append_content_item(self, item: str) -> None:
        self.content_items.append(item)

    def append_plain_text(self, text: str) -> None:
        self.content_items.append(text.strip())

    def append_row(self, row: ParserRowValues) -> None:
        self.rows.append(row)

    def schedule_deferred_task(self, task: DeferredSummaryTask) -> None:
        self.deferred_llm_tasks.append(task)

    def to_dataframe(self):
        """positional rows → ParsedRow DataFrame（惰性 pandas）。"""
        rows_builder = ParsedRowsBuilder()
        for row_values in self.rows:
            rows_builder.append(self._row_values_to_parsed_row(row_values))
        return process_dup_paths_df(rows_builder.to_dataframe())

    def to_blocks(self, document_id: str = "doc") -> list[Block]:
        """positional rows → IR Block 列表（设计文档 01）。

        每个行路径按 split_char 拆出标题层级：先补发 heading block，再发
        内容 block（type: text→paragraph / image→image / table→table）。
        """
        blocks: list[Block] = []
        order = 0
        current_heading_id: str | None = None
        emitted_paths: set[str] = set()
        root_segments = [
            segment
            for segment in (self.relative_root or "").split(self.split_char)
            if segment
        ]

        for row_values in self.rows:
            content = str(row_values[0]) if row_values else ""
            path = str(row_values[1]) if len(row_values) > 1 else self.path
            row_type = str(row_values[2]) if len(row_values) > 2 else "text"
            page_raw = row_values[10] if len(row_values) > 10 else ""
            page = int(page_raw) if str(page_raw).isdigit() else None

            segments = [segment for segment in path.split(self.split_char) if segment]
            heading_segments = segments[len(root_segments):]
            heading_prefixes: list[str] = []
            prefix = list(segments[: len(root_segments)])
            for segment in heading_segments:
                prefix = prefix + [segment]
                heading_prefixes.append(self.split_char.join(prefix))

            for level, heading_path in enumerate(heading_prefixes, start=1):
                if heading_path in emitted_paths:
                    continue
                emitted_paths.add(heading_path)
                blocks.append(
                    Block(
                        id=make_block_id(document_id, order),
                        type="heading",
                        order=order,
                        level=level,
                        section_path=heading_path,
                        content={"text": heading_path.split(self.split_char)[-1]},
                        parent_id=current_heading_id,
                    )
                )
                current_heading_id = blocks[-1].id
                order += 1

            if not content:
                continue

            block_type = {
                "text": "paragraph",
                "image": "image",
                "table": "table",
            }.get(row_type, "paragraph")
            content_payload: dict[str, Any] = {"text": content}
            if block_type == "image":
                image_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", content)
                if image_match:
                    content_payload = {
                        "caption": image_match.group(1),
                        "src": image_match.group(2),
                    }
                else:
                    content_payload["src"] = content
            if block_type == "table":
                table_match = re.match(
                    r"^\[TABLE\s+([^\]]+)\]\(([^)]+)\)$", content
                )
                if table_match:
                    content_payload["name"] = table_match.group(1)
                    content_payload["html_path"] = table_match.group(2)

            blocks.append(
                Block(
                    id=make_block_id(document_id, order),
                    type=block_type,
                    order=order,
                    section_path=path,
                    page=page,
                    parent_id=current_heading_id,
                    content=content_payload,
                )
            )
            order += 1

        return blocks

    def _row_values_to_parsed_row(self, row_values: ParserRowValues) -> ParsedRow:
        return ParsedRow(
            content=str(row_values[0]) if row_values else "",
            path=str(row_values[1]) if len(row_values) > 1 else self.path,
            type=str(row_values[2]) if len(row_values) > 2 else "text",
            length=(
                int(row_values[3])
                if len(row_values) > 3 and str(row_values[3]).isdigit()
                else None
            ),
            keywords=str(row_values[4]) if len(row_values) > 4 else "",
            summary=str(row_values[5]) if len(row_values) > 5 else "",
            know_id=str(row_values[6]) if len(row_values) > 6 else "",
            tokens=str(row_values[7]) if len(row_values) > 7 else "",
            connectto=str(row_values[8]) if len(row_values) > 8 else "",
            addtime=str(row_values[9]) if len(row_values) > 9 else self.timestamp,
            page_nums=str(row_values[10]) if len(row_values) > 10 else "",
            entities=str(row_values[11]) if len(row_values) > 11 else "",
            asset_title=str(row_values[12]) if len(row_values) > 12 else "",
        )
