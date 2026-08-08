"""产物打包（设计文档 05）：full.md / chunks.json / doc_nav.json / toc / manifest。

原子提交约定：manifest.json 最后写入，作为产物「完成」标记；下游只认含
manifest 的产物目录。
"""

from __future__ import annotations

import json
import os
from typing import Any

from worker.services.document_parser.ir.blocks import (
    Block,
    blocks_to_markdown,
    build_section_tree,
)
from worker.services.document_parser.packaging.chunks import Chunk
from worker.services.document_parser.packaging.manifest import Manifest


def write_artifacts(
    output_dir: str,
    *,
    blocks: list[Block] | tuple[Block, ...],
    chunks: list[Chunk],
    manifest: Manifest,
) -> dict[str, str]:
    """把 IR 各视图与 manifest 写入产物目录，返回 {视图名: 路径}。"""
    os.makedirs(output_dir, exist_ok=True)
    paths: dict[str, str] = {}
    blocks = list(blocks)

    paths["full.md"] = _write_text(output_dir, "full.md", blocks_to_markdown(blocks))

    chunks_payload: dict[str, Any] = {
        "document_id": manifest.document_id,
        "ir_version": "2",
        "chunks": [chunk.to_dict() for chunk in chunks],
    }
    paths["chunks.json"] = _write_json(output_dir, "chunks.json", chunks_payload)

    nav_payload: dict[str, Any] = {
        "title": manifest.source_name,
        "sections": build_section_tree(blocks),
    }
    paths["doc_nav.json"] = _write_json(output_dir, "doc_nav.json", nav_payload)

    toc_payload = [
        {"section_path": block.section_path, "title": block.text, "level": block.level}
        for block in blocks
        if block.type == "heading"
    ]
    paths["toc_hierarchies.json"] = _write_json(
        output_dir, "toc_hierarchies.json", toc_payload
    )

    # 表格 HTML 由解析阶段写入（parse_md）；这里只为没有 html_path 的兜底
    table_dir = os.path.join(output_dir, "tables")
    for block in blocks:
        if block.type != "table" or block.content.get("html_path"):
            continue
        os.makedirs(table_dir, exist_ok=True)
        table_name = block.content.get("name", "table")
        paths[f"tables/{table_name}.html"] = _write_text(
            table_dir, f"{table_name}.html", block.content.get("html", block.text)
        )

    # 最后写 manifest：产物「完成」标记
    paths["manifest.json"] = _write_json(output_dir, "manifest.json", manifest.to_dict())
    return paths


def _write_text(output_dir: str, name: str, content: str) -> str:
    path = os.path.join(output_dir, name)
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return path


def _write_json(output_dir: str, name: str, payload: Any) -> str:
    path = os.path.join(output_dir, name)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return path
