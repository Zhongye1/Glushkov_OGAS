"""Markdown 标题检测（Phase A 规则版，替代参考实现的 LLM 标题预测）。

参考实现此处为 eval_md_headings + heading_hierarchy（LLM）；MVP 用规则替代，
LLM 接入点保留在 TODO。规则：ATX 标题（#）优先，编号标题（1. / 1.1 等）兜底。
"""

from __future__ import annotations

import re

MD_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)[、.．]\s*(.*)$")


def md_heading_match(line: str, as_is: bool = False) -> tuple[str, int]:
    """返回 (标题文本, 级别)；非标题返回 ("", -1)。"""
    match = re.match(r"^(\#{1,6})\s*(.*)$", line)
    if match:
        return match.group(2).strip(), len(match.group(1))
    if not as_is:
        numbered = _NUMBERED_HEADING_RE.match(line.strip())
        if numbered:
            depth = min(len(numbered.group(1).split(".")), 6)
            return numbered.group(2).strip(), depth
    return "", -1


def eval_md_headings(
    md_lines: list[str],
    source_type: str = "md",
    toc_hierarchies=None,
    **kwargs,
) -> list[str]:
    """规则版标题归一：编号标题转 # 前缀，保留已有 # 标题。

    TODO: 接入参考实现的 LLM 标题预测（含 TOC 上下文与分片区间）。
    """
    normalized: list[str] = []
    for line in md_lines:
        stripped = line.strip()
        if not stripped:
            continue
        text, level = md_heading_match(stripped, as_is=False)
        if level > 0 and not stripped.startswith("#"):
            normalized.append(f"{'#' * level} {text}")
        else:
            normalized.append(stripped)
    return normalized
