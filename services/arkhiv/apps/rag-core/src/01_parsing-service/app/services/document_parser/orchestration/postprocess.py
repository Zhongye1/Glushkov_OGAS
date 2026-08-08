"""产物后处理：清理孤儿图 + 压缩图片，并同步 IR 引用（参考实现移植，适配 Block IR）。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from app.services.document_parser.ir.blocks import Block
from app.services.document_parser.support.stage_profiler import stage_timer

_IMG_SRC_BASENAME_RE = re.compile(
    r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_HASH_IMAGE_RE = re.compile(
    r"^[a-f0-9]{64}\.(?:jpg|jpeg|png|gif|webp)$",
    re.IGNORECASE,
)


def apply_parse_postprocess(
    output_dir: str,
    blocks: tuple[Block, ...] | list[Block],
) -> tuple[Block, ...]:
    """解析后处理：清理孤儿图，压缩图片并回写 IR 中的图片路径。"""
    with stage_timer("document.cleanup_unreferenced_images", output_dir=output_dir):
        cleanup_unreferenced_images(output_dir)

    with stage_timer("document.compress_images", output_dir=output_dir):
        compress_stats = compress_output_images(output_dir)
        if compress_stats.rename_map:
            return apply_rename_map_to_blocks(tuple(blocks), compress_stats.rename_map)

    return tuple(blocks)


def cleanup_unreferenced_images(output_dir: str) -> int:
    """删除未被 tables/*.html 引用的 hash 命名孤儿图；image-N-* 永远保留。"""
    image_dir = os.path.join(output_dir, "images")
    if not os.path.isdir(image_dir):
        return 0
    protected = _collect_table_img_basenames(output_dir)
    removed = 0
    for filename in os.listdir(image_dir):
        if not _HASH_IMAGE_RE.match(filename) or filename in protected:
            continue
        try:
            os.remove(os.path.join(image_dir, filename))
            removed += 1
        except OSError:
            pass
    return removed


def _collect_table_img_basenames(output_dir: str) -> set[str]:
    tables_dir = os.path.join(output_dir, "tables")
    if not os.path.isdir(tables_dir):
        return set()
    basenames: set[str] = set()
    for filename in os.listdir(tables_dir):
        if not filename.endswith(".html"):
            continue
        try:
            with open(os.path.join(tables_dir, filename), encoding="utf-8") as file:
                html = file.read()
        except OSError:
            continue
        for match in _IMG_SRC_BASENAME_RE.finditer(html):
            src = match.group(1).strip()
            if src:
                basenames.add(os.path.basename(src))
    return basenames


@dataclass(frozen=True)
class CompressStats:
    processed: int = 0
    converted_png_to_jpg: int = 0
    resized: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    rename_map: dict[str, str] = field(default_factory=dict)


def compress_output_images(output_dir: str) -> CompressStats:
    """压缩 images/ 下图片（PNG→JPG / resize）。

    MVP 骨架：仅当 Pillow 可用时工作，否则为 no-op。压缩产生的文件重命名
    通过 rename_map 返回，由调用方同步 IR 引用（参考实现 compress_output_images）。
    """
    image_dir = os.path.join(output_dir, "images")
    if not os.path.isdir(image_dir):
        return CompressStats()
    try:
        from PIL import Image  # noqa: F401  # 惰性导入
    except ImportError:
        return CompressStats()
    # TODO: PNG→JPG、resize、字节统计，产出 rename_map
    return CompressStats()


def apply_rename_map_to_blocks(
    blocks: tuple[Block, ...],
    rename_map: dict[str, str],
) -> tuple[Block, ...]:
    """把压缩产生的文件改名回写到 image block 的 src，保证磁盘与 IR 一致。"""

    def _remap(block: Block) -> Block:
        if block.type != "image":
            return block
        src = block.content.get("src", "")
        renamed = rename_map.get(os.path.basename(src), rename_map.get(src, src))
        if renamed == src:
            return block
        return Block(
            id=block.id,
            type=block.type,
            order=block.order,
            content={**block.content, "src": renamed},
            level=block.level,
            parent_id=block.parent_id,
            section_path=block.section_path,
            page=block.page,
            meta=block.meta,
        )

    return tuple(_remap(block) for block in blocks)
