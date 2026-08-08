"""IR 模型：扁平有序 Block 集合（设计文档 01）。

设计要点：
- 扁平数组 + parent_id 指针，不建嵌套树；层级信息同时编码在 section_path。
- Block 是分块的最小不可分割单元（chunk 只能由完整 block 组成）。
- full.md / doc_nav.json / chunks.json 都是 IR 的序列化视图。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

BlockType = Literal[
    "heading", "paragraph", "list", "table", "image", "code_block",
    "quote", "callout", "footnote", "page_break",
]


@dataclass(frozen=True)
class Block:
    id: str
    type: BlockType
    order: int
    content: dict[str, Any]
    level: int | None = None
    parent_id: str | None = None
    section_path: str = ""
    page: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        for key in ("text", "caption", "alt_text"):
            value = self.content.get(key)
            if isinstance(value, str) and value:
                return value
        return ""


def make_block_id(document_id: str, order: int) -> str:
    return f"{document_id}-b{order:04d}"


def blocks_to_markdown(blocks: list[Block]) -> str:
    """IR → full.md 视图（供 LLM 的完整上下文）。"""
    lines: list[str] = []
    for block in blocks:
        if block.type == "heading":
            level = block.level or 1
            lines.append(f"{'#' * level} {block.text}")
        elif block.type == "paragraph":
            lines.append(block.text)
        elif block.type == "list":
            for item in block.content.get("items", []):
                lines.append(f"- {item}")
        elif block.type == "table":
            html_path = block.content.get("html_path")
            lines.append(str(html_path) if html_path else block.text)
        elif block.type == "image":
            src = block.content.get("src", "")
            caption = block.content.get("caption", "")
            lines.append(f"![{caption}]({src})")
        elif block.type == "code_block":
            lang = block.content.get("lang", "")
            lines.append(f"```{lang}\n{block.text}\n```")
        elif block.type == "quote":
            lines.append(f"> {block.text}")
        elif block.type == "callout":
            lines.append(f"[!{block.content.get('kind', 'note')}] {block.text}")
        elif block.type in ("footnote", "page_break"):
            lines.append(block.text)
    return "\n".join(lines) + ("\n" if lines else "")


def build_section_tree(blocks: list[Block]) -> list[dict[str, Any]]:
    """IR → doc_nav.json 视图：从 heading block 重建标题树。"""
    root: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for block in blocks:
        if block.type != "heading":
            continue
        level = block.level or 1
        node: dict[str, Any] = {
            "section_path": block.section_path,
            "title": block.text,
            "children": [],
        }
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            root.append(node)
        stack.append({**node, "level": level})
    return root
