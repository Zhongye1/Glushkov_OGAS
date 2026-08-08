"""解析服务稳定接缝（参考实现移植 + 任务状态机接线，设计文档 03）。"""

from __future__ import annotations

import uuid

from app.services.document_parser.orchestration.parse_input import ParseInput, ParseOptions
from app.services.document_parser.orchestration.parse_pipeline import (
    ParsePipelineResult,
    run_parse_pipeline,
)
from app.services.document_parser.state_machine.machine import (
    JobState,
    JobStateMachine,
)
from app.services.document_parser.state_machine.states import JobStatus


def checkerboard_parse_output(
    file_full_path: str,
    filename: str,
    output_dir: str,
    internal_output_filename: str,
    job_id: str | None = None,
    llm_histories: int = 5,
    smart_title_parse: bool = True,
    summary_image: bool = True,
    summary_table: bool = True,
    summary_txt: bool = True,
    stopwords: list[str] | None = None,
    doc_type: str = "auto",
    add_frag_desc: str = "",
    base_url: str = "",
    fragment_content: str = "",
    s3_key: str | None = None,
) -> ParsePipelineResult:
    """稳定解析接缝（"Stable parser seam"）：展开参数 → ParseInput → 流水线。

    内部编排怎么改都不影响调用方；对应参考实现 parse_service.py。
    """
    parse_input = ParseInput(
        file_full_path=file_full_path,
        filename=filename,
        internal_output_filename=internal_output_filename,
        job_id=job_id,
        output_dir=output_dir,
        options=ParseOptions(
            add_frag_desc=add_frag_desc,
            doc_type=doc_type,
            llm_histories=llm_histories,
            smart_title_parse=smart_title_parse,
            stopwords=stopwords,
            summary_image=summary_image,
            summary_table=summary_table,
            summary_txt=summary_txt,
        ),
        base_url=base_url,
        fragment_content=fragment_content,
        s3_key=s3_key,
    )
    return run_parse_pipeline(parse_input)


def parse_job(
    file_full_path: str,
    filename: str,
    output_dir: str,
    job_id: str | None = None,
) -> tuple[ParsePipelineResult, JobState]:
    """任务状态机接线示例：PENDING → RUNNING → DONE / FAILED（设计文档 03）。"""
    job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
    machine = JobStateMachine()
    state = JobState(job_id=job_id, status=JobStatus.PENDING)
    state = machine.transition(state, JobStatus.RUNNING, stage="route")
    try:
        result = checkerboard_parse_output(
            file_full_path=file_full_path,
            filename=filename,
            output_dir=output_dir,
            internal_output_filename=filename,
            job_id=job_id,
        )
        state = machine.transition(state, JobStatus.DONE, stage="done")
        return result, state
    except Exception as exc:
        state = machine.transition(
            state,
            JobStatus.FAILED,
            stage="failed",
            error_code=getattr(exc, "error_code", "PARSE_FAILED"),
            error_message=str(exc),
        )
        raise
