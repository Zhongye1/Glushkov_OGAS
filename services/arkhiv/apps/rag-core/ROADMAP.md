# RAG 内核 roadmap（文档解析服务）

## 已完成（MVP 骨架）

- 设计文档 6 篇：`docs/parsing-service/`（IR 模型 / 适配器接口 / 状态机 / PDF+Markdown
  适配器 / 产物打包 / 参考实现对照）
- 解析内核 `src/01_parsing-service/worker/services/document_parser/`：IR（Block/ParsedRow）、
  Protocol 适配器 + 路由、任务状态机、Markdown 行扫描引擎、PDF 分片归 md、产物打包
- 契约包 `packages/shared-python`：JobStatus / JobState / ParseJob / Manifest（API↔worker 共享）
- 共享存储抽象 `storage/artifact_storage.py`：local / S3，产物按对象存储 key 传递
- worker 入口 `worker_app.py` + `Dockerfile.worker`：队列消费者，无 HTTP、无鉴权
- 测试：41 个解析单测 + 进程内 e2e（46 passed，1 skipped）

## 下一步

### P0：API 侧闭环（最关键）

1. 最小 `shared` 层落地：`shared.core.config` + job 表 + job repository——只落能跑通闭环的部分，
   不照搬 Knowhere 全量
2. API 建 job（pending）→ 发布 `ParseJob` 到队列 → worker 消费 → 回写
   running/done + `artifact_prefix` → `get_result` 读产物（manifest/chunks）
3. `worker_dispatcher` 接线（任务注册名 `app.core.tasks.document_ingestion_tasks.parse_task`
   已对齐，API 侧按此名发消息）

### P1：worker 工程化

4. docker-compose 加 redis + celery worker；celery 进 pyproject 依赖
5. 队列级 e2e（真 broker）：提交 → 消费 → 回写，作为集成测试

### P2：解析能力补齐

6. PDF：MinerU provider 接入（当前 PyMuPDF 文本层占位）、分片标题预测、图片/表格 LLM 摘要
7. Office 适配器（docx/xlsx/pptx）、HTML/JSON 适配器注册

### P3：下游与质量

8. `chunks.json` 契约对接 index/检索层（父链、去重 hash、引用追溯）
9. 评测闭环：标题层级准确率、表格还原率、文本抽取召回（ground-truth 回归集）

建议顺序：P0 → P1 → P2 → P3。
