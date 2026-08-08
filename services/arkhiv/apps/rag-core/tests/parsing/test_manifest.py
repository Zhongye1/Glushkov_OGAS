"""产物 manifest：document_id 稳定派生 + 分块统计（设计文档 05）。"""

from __future__ import annotations

from worker.services.document_parser.ir.blocks import Block, make_block_id
from worker.services.document_parser.packaging.chunks import build_chunks
from worker.services.document_parser.packaging.manifest import (
    Manifest,
    build_manifest,
    make_document_id,
)


def test_document_id_is_stable_and_distinct() -> None:
    assert make_document_id("a.pdf", 10) == make_document_id("a.pdf", 10)
    assert make_document_id("a.pdf", 10) != make_document_id("a.pdf", 11)
    assert make_document_id("a.pdf", 10) != make_document_id("b.pdf", 10)
    assert make_document_id("a.pdf", 10).startswith("doc_")


def test_build_manifest_statistics() -> None:
    blocks = [
        Block(id=make_block_id("doc", 0), type="heading", order=0, section_path="doc/甲", content={"text": "甲"}),
        Block(id=make_block_id("doc", 1), type="paragraph", order=1, section_path="doc/甲", content={"text": "正文"}),
        Block(id=make_block_id("doc", 2), type="table", order=2, section_path="doc/甲", content={"text": "表"}),
        Block(id=make_block_id("doc", 3), type="image", order=3, section_path="doc/甲", content={"text": "图"}),
    ]
    chunks = build_chunks(blocks, "doc")
    manifest = build_manifest(
        job_id="job_1",
        document_id="doc_1",
        source_name="a.md",
        page_count=None,
        chunks=chunks,
        timings={"document.package": 10},
    )
    assert manifest.statistics["total_chunks"] == 3
    assert manifest.statistics["text_chunks"] == 1
    assert manifest.statistics["table_chunks"] == 1
    assert manifest.statistics["image_chunks"] == 1
    assert manifest.document_id == "doc_1"
    assert manifest.job_id == "job_1"


def test_manifest_to_dict_shape() -> None:
    manifest = Manifest(job_id="job_1", document_id="doc_1", source_name="a.md")
    payload = manifest.to_dict()
    assert payload["version"] == "2.0"
    assert payload["job_id"] == "job_1"
    assert payload["processing"]["cost"]["micro_dollars"] == 0
    assert payload["processing"]["timing"]["duration_ms"] == 0
    assert "statistics" in payload
