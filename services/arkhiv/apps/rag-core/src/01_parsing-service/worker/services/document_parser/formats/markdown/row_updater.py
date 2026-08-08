"""行写回（参考实现 update_df_list 的简化移植，去掉 LLM 摘要与 shared 依赖）。

职责：把累积的 content_items 落成一行 ParsedRow（纯文本行）；图片/表格行由
调用方直接 append_row。
"""

from __future__ import annotations

from worker.services.document_parser.ir.parsed_row import ParsedRow
from worker.services.document_parser.support.identifiers import gen_str_codes

_REF_MARKERS = ("![", "<table", "<img", "TABLE_REF", "IMAGE_REF")


def detect_row_type(content: str) -> str:
    lowered = content.lower()
    if "<table" in lowered or lowered.startswith("|") or "TABLE_REF" in content:
        return "table"
    if "![" in content or "<img" in lowered or "IMAGE_REF" in content:
        return "image"
    return "text"


def update_df_list(
    df_list,
    content_items,
    path,
    llm_paras,
    time_stamp,
    page_nums="",
    summary_len=1500,
    skip_llm=False,
):
    """把累积的 content_items 落成一行（纯文本；图片/表格行由调用方直接 append_row）。"""
    bottom_content = "\n".join(content_items).strip()
    if not bottom_content:
        return df_list

    pure_text = "\n".join(
        item
        for item in content_items
        if not any(marker in str(item) for marker in _REF_MARKERS)
    ).strip()
    know_id_source = pure_text if pure_text else f"{path}::{page_nums}"
    df_list.append(
        ParsedRow(
            content=bottom_content,
            path=path,
            type=detect_row_type(bottom_content),
            keywords="",
            summary="",
            know_id=gen_str_codes(know_id_source),
            tokens=str(len(bottom_content.split())),
            connectto="",
            addtime=time_stamp,
            page_nums=page_nums,
            entities="",
        ).to_list()
    )
    return df_list
