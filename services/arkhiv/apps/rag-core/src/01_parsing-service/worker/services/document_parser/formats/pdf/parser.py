"""PDF 适配器：三分支（Atlas / 分片 / 标准）+ 分片归 md（参考实现移植）。

参考实现 formats/pdf/parser.py 的重构骨架：MinerU 由可插拔 PdfTextProvider
取代（MVP 用 PyMuPDF 文本层）；逐片标题预测 / TOC 排除在分片管线中标记 TODO。
"""

from __future__ import annotations

import os
import shutil

from worker.services.document_parser.formats.markdown.parser import parse_md
from worker.services.document_parser.formats.pdf.provider import get_pdf_provider
from worker.services.document_parser.formats.pdf.shard_splitter import (
    AgentShard,
    bin_pack_shards,
    split_pdf,
)
from worker.services.document_parser.ir.blocks import Block
from worker.services.document_parser.support.stage_profiler import stage_timer

MAX_PDF_SHARD_PAGES = 200


def parse_pdfs(
    pdf_path: str,
    filename: str,
    output_dir: str,
    base_llm_paras: dict | None = None,
    profile=None,
    relative_root: str | None = None,
    s3_key: str | None = None,
    job_id: str | None = None,
) -> list[Block]:
    """解析 PDF 为 IR Block 列表（文本层抽取 → 归 md → 行扫描状态机）。"""
    base_llm_paras = base_llm_paras or {}

    routing_category = (
        getattr(profile, "routing_category", None) if profile else None
    )
    if routing_category == "atlas":
        # 参考实现：Atlas 图册直接 bypass MinerU 走 parse_atlas（MVP 未实现）
        raise NotImplementedError("Atlas track is not implemented in the MVP")

    anatomy = getattr(profile, "anatomy", None) if profile else None
    if anatomy is not None:
        return _parse_pdf_via_shards(
            pdf_path,
            filename,
            output_dir,
            base_llm_paras,
            profile=profile,
            relative_root=relative_root,
            s3_key=s3_key,
            job_id=job_id,
        )

    # ── 标准单趟：文本层抽取 → parse_md Phase A 旁路 ──
    with stage_timer("pdf.extract.standard", filename=filename):
        md_lines = get_pdf_provider().extract_text_lines(pdf_path)

    with stage_timer("pdf.parse_md", filename=filename):
        return parse_md(
            output_dir,
            source_type="md",
            md_lines=md_lines,
            base_llm_paras=base_llm_paras,
            relative_root=relative_root,
            skip_toc_detection=True,
        )


def _parse_pdf_via_shards(
    pdf_path: str,
    filename: str,
    output_dir: str,
    base_llm_paras: dict | None,
    profile=None,
    relative_root: str | None = None,
    s3_key: str | None = None,
    job_id: str | None = None,
) -> list[Block]:
    """分片管线：DOC_AGENT 计划 → bin_pack → split → 并行抽取 → 合并 → parse_md。

    对应参考实现 _parse_pdf_via_shards（docstring 7 步）；MVP 把 MinerU 换成
    PdfTextProvider，逐片标题预测（eval_md_headings + split_toc_for_shard）与
    并行化标记 TODO。
    """
    base_llm_paras = base_llm_paras or {}
    anatomy = getattr(profile, "anatomy", None)
    shard_plan = getattr(anatomy, "shard_plan", None)
    agent_shards = list(getattr(shard_plan, "shards", []) or [])
    toc_result = getattr(anatomy, "toc_result", None)
    toc_pages = (
        set(getattr(toc_result, "toc_pages", []) or []) if toc_result else set()
    )

    page_count = getattr(profile, "page_count", None)
    if not agent_shards:
        agent_shards = [
            AgentShard(page_start=1, page_end=page_count or MAX_PDF_SHARD_PAGES)
        ]

    with stage_timer("pdf.bin_pack", filename=filename):
        merged_shards = bin_pack_shards(agent_shards, max_pages=MAX_PDF_SHARD_PAGES)

    fast_path_original_pdf = len(merged_shards) == 1 and not toc_pages
    provider = get_pdf_provider()

    if fast_path_original_pdf:
        with stage_timer("pdf.extract.standard", filename=filename):
            all_lines = provider.extract_text_lines(pdf_path)
    else:
        work_dir = _local_shard_workspace(output_dir)
        shard_s3_keys: list[str] = []
        try:
            with stage_timer("pdf.split_shards", filename=filename):
                shard_pdf_paths, _page_remap = split_pdf(
                    pdf_path,
                    merged_shards,
                    work_dir,
                    exclude_pages=toc_pages if toc_pages else None,
                )

            with stage_timer("pdf.extract.shards", filename=filename):
                all_lines = []
                for shard_path in shard_pdf_paths:
                    all_lines.extend(provider.extract_text_lines(shard_path))
            # TODO: 逐片标题预测（eval_md_headings，首片带完整 TOC）+ merge_images
        finally:
            _cleanup_temp_shard_s3_assets(shard_s3_keys)
            _cleanup_local_shard_workspace(work_dir)

    with stage_timer("pdf.parse_md", filename=filename):
        return parse_md(
            output_dir,
            source_type="md",
            md_lines=all_lines,
            base_llm_paras=base_llm_paras,
            relative_root=relative_root,
            skip_toc_detection=True,
        )


def _local_shard_workspace(output_dir: str) -> str:
    work_dir = os.path.join(output_dir, "_shards")
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def _cleanup_temp_shard_s3_assets(s3_keys: list[str]) -> None:
    # MVP：无 S3 分片产物；保留钩子与参考实现对齐
    pass


def _cleanup_local_shard_workspace(work_dir: str) -> None:
    shutil.rmtree(work_dir, ignore_errors=True)
