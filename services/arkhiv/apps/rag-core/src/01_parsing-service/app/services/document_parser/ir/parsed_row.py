"""ParsedRow 与解析层列契约（参考实现移植，去掉 shared.core.config 依赖）。

参考实现：Knowhere apps/worker/app/services/document_parser/support/parser_rows.py。
列定义由 ``ALL_DF_COLS`` 环境变量驱动（缺省用内置默认），并强制补尾部
``entities`` / ``asset_title`` 两个必需列，兼容只声明 legacy 11 列的老部署。
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DEFAULT_ALL_DF_COLS: str = (
    "content,path,type,length,keywords,summary,know_id,tokens,connectto,"
    "addtime,page_nums,entities,asset_title"
)

# 解析层硬依赖的尾部列；缺失时按列名写入会 ValueError。
_REQUIRED_TRAILING_COLUMNS: tuple[str, ...] = ("entities", "asset_title")


def resolve_parser_columns(env_all_df_cols: str | None = None) -> tuple[str, ...]:
    raw = env_all_df_cols if env_all_df_cols is not None else os.getenv("ALL_DF_COLS")
    columns = (
        [col.strip() for col in raw.split(",") if col.strip()]
        if raw
        else [col.strip() for col in DEFAULT_ALL_DF_COLS.split(",") if col.strip()]
    )
    for required in _REQUIRED_TRAILING_COLUMNS:
        if required not in columns:
            columns.append(required)
    return tuple(columns)


PARSER_ROW_COLUMNS: tuple[str, ...] = resolve_parser_columns()


def serialize_entities(entities: Any) -> str:
    """把实体列表序列化为 JSON 字符串；空值保持空字符串。"""
    if not entities:
        return ""
    normalized: list[dict[str, str]] = []
    for item in entities:
        if hasattr(item, "to_dict"):
            item = item.to_dict()
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            normalized.append({"text": text, "type": str(item.get("type", "")).strip()})
    if not normalized:
        return ""
    return json.dumps(normalized, ensure_ascii=False)


@dataclass(frozen=True)
class ParsedRow:
    content: str
    path: str
    type: str
    know_id: str
    addtime: str
    keywords: str = ""
    summary: str = ""
    tokens: str = ""
    connectto: str = ""
    page_nums: str = ""
    length: int | None = None
    entities: str = ""
    asset_title: str = ""

    def to_list(self) -> list[object]:
        content_length = self.length if self.length is not None else len(self.content)
        return [
            self.content,
            self.path,
            self.type,
            content_length,
            self.keywords,
            self.summary,
            self.know_id,
            self.tokens,
            self.connectto,
            self.addtime,
            self.page_nums,
            self.entities,
            self.asset_title,
        ]

    def to_dict(self) -> dict[str, object]:
        return dict(zip(PARSER_ROW_COLUMNS, self.to_list()))


class ParsedRowsBuilder:
    def __init__(self) -> None:
        self._rows: list[ParsedRow] = []

    def append(self, row: ParsedRow) -> None:
        self._rows.append(row)

    def extend(self, rows: list[ParsedRow]) -> None:
        self._rows.extend(rows)

    def to_dataframe(self):
        import pandas as pd  # 惰性导入

        return pd.DataFrame(
            [row.to_list() for row in self._rows],
            columns=pd.Index(PARSER_ROW_COLUMNS),
        )


# 位置行下标常量：替代 row[4]/row[5] 魔法下标（audit P5）。
COL_KEYWORDS = PARSER_ROW_COLUMNS.index("keywords")
COL_SUMMARY = PARSER_ROW_COLUMNS.index("summary")
COL_ENTITIES = PARSER_ROW_COLUMNS.index("entities")
COL_ASSET_TITLE = PARSER_ROW_COLUMNS.index("asset_title")


def apply_body_summary(row: list[Any], result: dict[str, Any]) -> None:
    """把 BodySummary（dict）按列名写回位置行。"""
    _ensure_row_width(row)
    row[COL_SUMMARY] = result.get("summary", "")
    row[COL_ENTITIES] = serialize_entities(result.get("entities"))
    row[COL_KEYWORDS] = result.get("keywords", "")


def apply_asset_summary(row: list[Any], result: dict[str, Any]) -> None:
    """把 AssetSummary（dict）按列名写回位置行，含 asset_title。"""
    _ensure_row_width(row)
    row[COL_ASSET_TITLE] = result.get("title", "")
    row[COL_SUMMARY] = result.get("summary", "")
    row[COL_ENTITIES] = serialize_entities(result.get("entities"))
    row[COL_KEYWORDS] = result.get("keywords", "")


def _ensure_row_width(row: list[Any]) -> None:
    while len(row) < len(PARSER_ROW_COLUMNS):
        row.append("")


def process_dup_paths_df(df):
    """对 DataFrame 重复 path 追加 _N 后缀（简化版：不传播父路径改名）。"""
    if "path" not in df.columns:
        return df
    original_paths = [str(p) for p in df["path"]]
    seen: dict[str, int] = {}
    new_paths: list[str] = []
    changed = False
    for path in original_paths:
        occurrence = seen.get(path, 0)
        seen[path] = occurrence + 1
        new_path = path if occurrence == 0 else f"{path}_{occurrence + 1}"
        if new_path != path:
            changed = True
        new_paths.append(new_path)
    if changed:
        df["path"] = new_paths
    return df


def gen_know_id(source: str) -> str:
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]


def blocks_to_dataframe(blocks, *, addtime: str | None = None):
    """把 IR Block 列表转成 ParsedRow DataFrame 存储视图（惰性导入 pandas）。

    标题 block 不生成行（层级编码在 section_path），与参考实现一致。
    """
    builder = ParsedRowsBuilder()
    stamp = addtime or datetime.now(timezone.utc).isoformat()
    for block in blocks:
        if block.type == "heading":
            continue
        content = block.text
        builder.append(
            ParsedRow(
                content=content,
                path=block.section_path,
                type=block.type,
                know_id=gen_know_id(content or block.section_path),
                addtime=stamp,
                tokens=str(len(content.split())),
                page_nums=str(block.page) if block.page is not None else "",
                entities=serialize_entities(block.content.get("entities")),
                asset_title=block.content.get("asset_title", ""),
            )
        )
    return process_dup_paths_df(builder.to_dataframe())
