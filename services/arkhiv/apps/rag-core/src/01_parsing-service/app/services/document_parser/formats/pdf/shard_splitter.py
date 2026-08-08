"""PDF 分片：bin-packing + 物理切分（参考实现移植，去掉 document_agent 依赖）。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentShard:
    """DOC_AGENT 出的语义分片（H1/H2 边界，1-based 页码）。"""

    page_start: int
    page_end: int
    title: str = ""


@dataclass
class MergedShard:
    """MinerU 单请求页数限制内的连续页区间。"""

    shard_index: int
    page_start: int  # 1-based 闭区间
    page_end: int  # 1-based 闭区间

    @property
    def page_count(self) -> int:
        return self.page_end - self.page_start + 1

    @property
    def page_offset(self) -> int:
        """MinerU 0-based page_idx → 原始 1-based 页号的偏移。"""
        return self.page_start - 1


def bin_pack_shards(
    agent_shards: list[AgentShard],
    max_pages: int,
) -> list[MergedShard]:
    """1:1 映射：每个 agent 分片就是一个 MinerU 分片。

    agent 已在 H1/H2 语义边界切好，合并会跨边界降低标题预测质量，故保留原样。
    """
    return [
        MergedShard(idx, page_start=shard.page_start, page_end=shard.page_end)
        for idx, shard in enumerate(agent_shards)
    ]


def split_pdf(
    pdf_path: str,
    shards: list[MergedShard],
    work_dir: str,
    exclude_pages: set[int] | None = None,
) -> tuple[list[str], dict[int, int] | None]:
    """用 PyMuPDF 把 PDF 物理切成子 PDF。

    返回 (shard_paths, page_remap)：
    - shard_paths：每个分片一个临时 PDF 路径；
    - page_remap：排除页时，映射 shard 本地 0-based 页号 → 原始 1-based 页号；
      无排除页时为 None。
    """
    import pymupdf  # 惰性导入

    doc = pymupdf.open(pdf_path)
    paths: list[str] = []
    page_remap: dict[int, int] | None = None
    os.makedirs(work_dir, exist_ok=True)

    try:
        if exclude_pages:
            page_remap = {}
        for shard in shards:
            shard_doc = pymupdf.open()
            global_new_index = 0
            for page_index in range(shard.page_start - 1, shard.page_end):
                page_number = page_index + 1
                if exclude_pages and page_number in exclude_pages:
                    continue
                shard_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)
                if page_remap is not None:
                    page_remap[global_new_index] = page_number
                global_new_index += 1
            if shard_doc.page_count == 0:
                shard_doc.close()
                continue
            shard_path = os.path.join(work_dir, f"shard-{shard.shard_index:03d}.pdf")
            shard_doc.save(shard_path)
            shard_doc.close()
            paths.append(shard_path)
    finally:
        doc.close()
    return paths, page_remap
