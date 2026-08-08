# IR 模型（统一中间表示）

## 1. 定位

IR 是文档解析服务的「产品定义」。所有格式解析完成后归一为同一套
文档结构模型；下游的 markdown 序列化、分块、表格/图片视图、检索发布
全部只消费 IR，不接触源格式。

## 2. 设计原则

1. 无歧义、可版本化：IR 带 `ir_version`，JSON 可序列化，字段只增不删。
2. 保留阅读顺序与版面：多栏、图文混排、跨页表格靠 `order` / `page` 还原。
3. 可追溯：每个 block 可映射回源文件位置（页码/坐标），是「带引用回答」的根基。
4. 一源多视图：`full.md`、`chunks.json`、`tables/*.html`、`doc_nav.json`
   都由 IR 派生，不各写各的。
5. Block 自治：每个 block 自包含语义，不依赖兄弟节点才能被理解。

## 3. 顶层结构

```json
{
    "ir_version": "2",
    "document_id": "doc_01HZX...",
    "meta": {
        "source_name": "annual-report.pdf",
        "mime": "application/pdf",
        "lang": "zh",
        "page_count": 83,
        "source_hash": "blake2b-..."
    },
    "blocks": [],
    "assets": {
        "images": ["assets/img-001.png"],
        "tables": ["assets/table-001.html"]
    }
}
```

- `document_id`：由 `source_hash` + 版本派生，同一文件内容不变则 id 不变，
  支持去重与增量更新。
- `assets` 只存引用，文件本体在对象存储，IR 保持轻量。

## 4. Block 模型

### 4.1 公共字段

| 字段           | 类型    | 说明                                 |
| -------------- | ------- | ------------------------------------ |
| `id`           | string  | 稳定 id，由内容 hash + 位置派生      |
| `type`         | enum    | block 类型，见 4.2                   |
| `level`        | int?    | 仅 heading/list 使用                 |
| `parent_id`    | string? | 父 block（标题层级锚点）             |
| `section_path` | string  | 标题路径，如 `1.2.3`，分块与引用共用 |
| `page`         | int?    | 源页码；无版面格式为 null            |
| `order`        | int     | 全局阅读顺序，单调递增               |
| `meta`         | object  | 来源与置信度：`{source, confidence}` |
| `content`      | object  | 按 type 不同的载荷                   |

### 4.2 类型表

| type         | content 载荷         | 说明                     |
| ------------ | -------------------- | ------------------------ |
| `heading`    | `{text}` + level     | 标题，层级树的锚点       |
| `paragraph`  | `{text}`             | 正文段落                 |
| `list`       | `{ordered, items[]}` | 列表，支持嵌套           |
| `table`      | 见 4.3               | 结构化表格               |
| `image`      | 见 4.4               | 图片 + 题注 + 上下文引用 |
| `code_block` | `{lang, text}`       | 代码块                   |
| `equation`   | `{latex, alt}`       | 公式                     |
| `quote`      | `{text, source?}`    | 引用块                   |
| `callout`    | `{kind, text}`       | 提示/结论块              |
| `footnote`   | `{text}`             | 脚注                     |
| `page_break` | `{}`                 | 版面标记，分块边界参考   |

### 4.3 表格建模

```json
{
    "id": "b-101",
    "type": "table",
    "content": {
        "rows": 5,
        "cols": 4,
        "header_rows": 1,
        "cells": [
            { "row": 0, "col": 0, "rowspan": 1, "colspan": 2, "text": "指标" }
        ],
        "asset_id": "assets/table-001.html"
    }
}
```

复杂表格序列化为 HTML/Markdown 均为纯函数，表格本体落
`assets/tables/`，不硬塞进 markdown 流。

### 4.4 图片建模

```json
{
    "id": "b-200",
    "type": "image",
    "content": {
        "asset_id": "assets/img-001.png",
        "caption": "图 1：收入结构",
        "alt_text": "收入结构饼图",
        "context_block_id": "b-201"
    }
}
```

「图 + 题注 + 上下文段落」绑定为一个引用单元，后续视觉解析与图检索
不改变 IR 结构。

## 5. 扁平数组还是树

采用**扁平数组 + parent 指针**，不建嵌套树：

- JSON 流式构建简单，分块/检索天然需要扁平访问；
- `section_path` 已隐含树关系，`doc_nav.json` 按需重建；
- 避免节点同时存在于数组与树的双份维护。

## 6. IR 与分块的关系

- Block 是**最小不可分割单元**：chunk 只能由完整 block 组成，禁止在
  表格、列表、代码块中间切断。
- chunk 是 IR 之上的聚合视图，携带 `parent_chunk_id` 支持父子分块
  （small-to-big：检索小块，喂上下文时取父级）。

```json
{
    "chunk_id": "c-001",
    "type": "text",
    "block_ids": ["b-020", "b-021"],
    "section_path": "1.2",
    "parent_chunk_id": "c-000",
    "text": "..."
}
```

追溯链：chunk → block → 原文位置。

## 7. 版本化与校验

- `ir_version` 进入模型与产物包；升级时旧产物可迁移或标记 deprecated。
- pydantic v2 实现：

```python
Block = Annotated[
    Union[Heading, Paragraph, Table, Image, ...],
    Field(discriminator="type"),
]
```

- 校验规则（加载时强制）：

| 规则     | 说明                                                  |
| -------- | ----------------------------------------------------- |
| 引用闭合 | `parent_id`、`context_block_id`、`asset_id` 必须存在  |
| 顺序唯一 | `order` 单调且无重复                                  |
| 层级合法 | heading level 1–6，list 嵌套深度受限                  |
| 类型枚举 | `type` 必须在注册表内，未知类型报错或降级为 paragraph |

## 8. 演进策略

- 新 block 类型：向后兼容地新增枚举值 + content 变体，旧产物不受影响。
- 新元数据：只加 `meta` 字段，不做破坏性变更。
- 大版本（如 v3）：允许结构变化，产物包同时保留 `ir_version` 标记。
