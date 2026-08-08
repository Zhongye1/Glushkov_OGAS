"""解析服务接缝：parse_job 状态流转与产物落盘。"""

from __future__ import annotations

import json

import pytest
from shared.contracts.parsing import JobStatus
from worker.services.document_parser.parse_service import parse_job


def test_parse_job_success_writes_artifacts(tmp_path) -> None:
    source = tmp_path / "sample.md"
    source.write_text("# 第一章\n\n正文。\n", encoding="utf-8")
    output_dir = tmp_path / "output"

    result, state = parse_job(
        file_full_path=str(source),
        filename="sample.md",
        output_dir=str(output_dir),
        job_id="job_test",
    )

    assert state.status is JobStatus.DONE
    assert state.stage == "done"
    assert state.completed_at is not None
    assert result.output_dir == str(output_dir / "sample.md")

    manifest_path = output_dir / "sample.md" / "manifest.json"
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["job_id"] == "job_test"
    assert payload["statistics"]["total_chunks"] >= 1

    assert (output_dir / "sample.md" / "full.md").exists()
    assert (output_dir / "sample.md" / "chunks.json").exists()


def test_parse_job_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_job(
            file_full_path=str(tmp_path / "missing.md"),
            filename="missing.md",
            output_dir=str(tmp_path / "output"),
            job_id="job_fail",
        )
