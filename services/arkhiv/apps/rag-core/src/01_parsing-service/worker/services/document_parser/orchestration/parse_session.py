"""ParseSession 与输出路径解析（参考实现移植）。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from worker.services.document_parser.orchestration.parse_input import ParseInput
from worker.services.document_parser.profiling.doc_profiler import (
    DocumentProfile,
    profile_document,
)
from worker.services.document_parser.support.stage_profiler import stage_timer

_UNSAFE_PATH_RE = re.compile(r"[\\/:*?\"<>|\s]+")


def build_parser_path_segment(value: str | None, default: str = "document") -> str:
    raw_value = str(value or "").strip()
    raw_segment = os.path.basename(raw_value) if raw_value else default
    segment = _UNSAFE_PATH_RE.sub("_", raw_segment).strip("._")
    return segment if segment not in {"", ".", ".."} else default


@dataclass(frozen=True)
class ParseSession:
    base_llm_paras: dict[str, object]
    base_url: str
    file_full_path: str
    filename: str
    fragment_content: str
    full_output_dir: str
    internal_output_filename: str
    job_id: str | None
    output_dir: str
    profile: DocumentProfile
    relative_root: str
    s3_key: str | None


def build_parse_session(parse_input: ParseInput) -> ParseSession:
    """构建解析会话：解析输出路径 + 文档画像（document.profile 阶段）。"""
    parse_options = parse_input.options
    base_llm_paras: dict[str, object] = {
        "llm_histories": parse_options.llm_histories,
        "smart_title_parse": parse_options.smart_title_parse,
        "summary_image": parse_options.summary_image,
        "summary_table": parse_options.summary_table,
        "summary_txt": parse_options.summary_txt,
        "stopwords": parse_options.stopwords or [],
        "doc_type": parse_options.doc_type,
        "frag_desc": parse_options.add_frag_desc,
        "parse_track": parse_options.parse_track,
        "model_name": "mvp-rule-based",
    }

    relative_root, full_output_dir = _resolve_output_paths(
        filename=parse_input.filename,
        internal_output_filename=parse_input.internal_output_filename,
        output_dir=parse_input.output_dir,
    )

    with stage_timer("document.profile", filename=parse_input.filename):
        profile = profile_document(
            parse_input.file_full_path,
            internal_output_filename=parse_input.internal_output_filename,
            job_id=parse_input.job_id,
            output_dir=full_output_dir,
        )

    return ParseSession(
        base_llm_paras=base_llm_paras,
        base_url=parse_input.base_url,
        file_full_path=parse_input.file_full_path,
        filename=parse_input.filename,
        fragment_content=parse_input.fragment_content,
        full_output_dir=full_output_dir,
        internal_output_filename=parse_input.internal_output_filename,
        job_id=parse_input.job_id,
        output_dir=parse_input.output_dir,
        profile=profile,
        relative_root=relative_root,
        s3_key=parse_input.s3_key,
    )


def _resolve_output_paths(
    *,
    filename: str,
    internal_output_filename: str,
    output_dir: str,
) -> tuple[str, str]:
    filename_segment = build_parser_path_segment(filename)
    internal_filename_segment = build_parser_path_segment(
        internal_output_filename,
        default=filename_segment,
    )
    relative_root = filename_segment

    full_output_dir = os.path.join(output_dir, internal_filename_segment)
    resolved_output_dir = os.path.realpath(output_dir)
    resolved_full_output_dir = os.path.realpath(full_output_dir)
    if (
        os.path.commonpath([resolved_output_dir, resolved_full_output_dir])
        != resolved_output_dir
    ):
        raise ValueError(
            f"Parser output directory escaped task workspace: {full_output_dir}"
        )
    os.makedirs(resolved_full_output_dir, exist_ok=True)
    return relative_root, resolved_full_output_dir
