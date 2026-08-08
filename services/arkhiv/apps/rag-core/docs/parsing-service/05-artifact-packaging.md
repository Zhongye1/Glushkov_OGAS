# 产物打包

## 1. 定位

产物包是解析服务对外交付物：一份文档的一次成功解析，产出
「原始文件 + 多视图 + 元数据」的完整集合。产物包同时是计费、
评测与增量更新的数据来源。

## 2. 产物目录结构

```text
<namespace>/<document_id>/
├── original.<ext>          # 原始文件（可配置保留）
├── full.md                 # 供 LLM 的完整上下文视图
├── chunks.json             # 检索单元（chunk 列表）
├── doc_nav.json            # 标题层级导航树
├── toc_hierarchies.json    # 目录层级原始数据
├── manifest.json           # 处理元数据（耗时/成本/统计）
├── images/
│   └── img-001.png
└── tables/
    ├── table-001.html
    └── table-001.md
```

## 3. 各文件契约

### 3.1 manifest.json

```json
{
    "version": "2.0",
    "job_id": "job_...",
    "document_id": "doc_...",
    "source_name": "annual-report.pdf",
    "processing": {
        "page_count": 83,
        "billing_status": "charged",
        "cost": { "micro_dollars": 124500, "credits": 0.1245 },
        "timing": {
            "started_at": "...",
            "completed_at": "...",
            "duration_ms": 233197
        },
        "stages": {
            "timing_ms": { "profile": 120, "extract": 8450, "structure": 3200 },
            "token_usage": { "prompt_tokens": 13512, "completion_tokens": 2901 }
        }
    },
    "statistics": {
        "total_chunks": 216,
        "text_chunks": 164,
        "image_chunks": 2,
        "table_chunks": 50
    }
}
```

### 3.2 chunks.json

```json
{
    "document_id": "doc_...",
    "ir_version": "2",
    "chunks": [
        {
            "chunk_id": "c-001",
            "type": "text",
            "section_path": "1.2",
            "parent_chunk_id": "c-000",
            "block_ids": ["b-020"],
            "page": 5,
            "text": "..."
        }
    ]
}
```

### 3.3 doc_nav.json

由 IR 重建的标题树：

```json
{
  "title": "年度报告",
  "sections": [
    {"section_path": "1", "title": "经营分析", "children": [...]}
  ]
}
```

## 4. 存储布局（对象存储）

- Key 规则：`<namespace>/<document_id>/<file>`，`document_id` 由
  `source_hash` 派生，天然版本化。
- 前缀：`private/`（原始文件与产物默认私有）、`public/`（可分享产物）。
- 保留策略：按 `document_id` 生命周期管理，删除时整前缀级联删除。

## 5. 打包流程

```text
IR（校验通过）
 → 序列化视图：full.md / chunks.json / doc_nav.json / tables
 → 写入对象存储临时 key：<ns>/<doc_id>/.tmp/<stage>
 → 全部写完后原子提交：写 final manifest.json
 → 产物校验（引用闭合、hash 核对）
 → 状态机置 done → 发布通知（索引/回调）
```

- 原子提交：manifest 是产物「完成」的标记；下游只认含 manifest 的产物。
- 失败回滚：清理 `.tmp/` 前缀，任务置 failed。

## 6. 幂等与发布

- `document_id` + `ir_version` 幂等：重复解析同一内容不覆盖已有产物，
  相同则直接复用。
- 发布载荷（webhook / 索引服务）：

```json
{
    "event": "document.parsed",
    "job_id": "job_...",
    "document_id": "doc_...",
    "namespace": "default",
    "artifact_prefix": "private/default/doc_.../",
    "statistics": { "total_chunks": 216 }
}
```

- 发布可重放；索引服务消费后幂等写入向量库与检索命名空间。

## 7. 与计费的关系

- `manifest.processing.cost` 由各阶段 token/时长核算写入；
- 失败、去重命中不写入收费账单；
- 结算读取 manifest 为准，避免二次计算。

## 8. 产物完整性校验

| 校验      | 规则                                            |
| --------- | ----------------------------------------------- |
| 引用闭合  | chunks 的 block_ids、图片/表格 asset 均存在     |
| hash 核对 | original 与 source_hash 一致                    |
| 统计一致  | manifest.statistics 与 chunks.json 实际计数一致 |
| 视图一致  | full.md 与 IR 序列化结果一致（规范化比较）      |
