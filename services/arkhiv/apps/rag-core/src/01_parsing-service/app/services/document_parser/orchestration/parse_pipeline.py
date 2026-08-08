"""解析流水线：建会话 → 路由 → 后处理 → 打包（设计文档 02/03/05）。

对应参考实现的 run_parse_pipeline，新增打包阶段（设计文档 05）。
"""

from __future__ import annotations

from app.services.document_parser.orchestration.parse_input import ParseInput
from app.services.document_parser.orchestration.parse_output import ParseOutput
from app.services.document_parser.orchestration.parse_session import build_parse_session
from app.services.document_parser.orchestration.postprocess import apply_parse_postprocess
from app.services.document_parser.orchestration.route_parse import route_document_parse
from app.services.document_parser.packaging.chunks import build_chunks
from app.services.document_parser.packaging.manifest import build_manifest, make_document_id
from app.services.document_parser.packaging.writer import write_artifacts
from app.services.document_parser.support.stage_profiler import (
    cleanup_stage_tracker,
    get_stage_timings,
    init_stage_tracker,
    stage_timer,
)

ParsePipelineResult = ParseOutput


def run_parse_pipeline(parse_input: ParseInput) -> ParsePipelineResult:
    """运行解析流水线并返回稳定解析输出（ParsePipelineResult = ParseOutput）。"""
    init_stage_tracker()
    try:
        session = build_parse_session(parse_input)
        parsed_output = route_document_parse(session)

        processed_blocks = apply_parse_postprocess(
            parsed_output.output_dir,
            parsed_output.blocks,
        )

        with stage_timer("document.package", filename=session.filename):
            document_id = make_document_id(session.filename, session.profile.page_count)
            chunks = build_chunks(processed_blocks, document_id)
            manifest = build_manifest(
                job_id=session.job_id,
                document_id=document_id,
                source_name=session.filename,
                page_count=session.profile.page_count,
                chunks=chunks,
                timings=get_stage_timings(),
            )
            write_artifacts(
                session.full_output_dir,
                blocks=processed_blocks,
                chunks=chunks,
                manifest=manifest,
            )

        return parsed_output.with_blocks(tuple(processed_blocks))
    finally:
        cleanup_stage_tracker()
