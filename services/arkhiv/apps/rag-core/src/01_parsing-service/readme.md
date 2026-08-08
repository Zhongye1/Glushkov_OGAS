# 文档解析服务（01_parsing-service）

## 定位与边界

- 单一职责：输入原始文件 + 元数据，输出一份结构化的文档产物包（文本 + 层级 + 表格 + 图片
  - 分块），不做检索、不做 embedding，也不直接答用户问题。
- **形态：解析 worker（队列消费者）**。不对外开 HTTP 接口、不做用户鉴权——auth 与入口职责
  （建 job / 查进度 / 拿结果）都在 API 层；worker 只消费队列任务、读写共享存储。
- 解析是 RAG 链路里最影响质量的一环，值得作为独立进程/镜像部署、可单独扩缩容。

## worker 架构约定

- 鉴权发生在 API 入口：用户带 token 进来，API 验明身份后把授权结果
  （`tenant_id` / `namespace` / `s3_key`）作为任务消息透传，worker 只用它们做数据隔离。
- worker 唯一需要的是基础设施凭证（broker / 对象存储 / LLM 的 key），不感知"用户"。
- 输入与产物一律经对象存储 key 传递（`ArtifactStorage`），不依赖本地磁盘路径；
  产物落 `<namespace>/<document_id>/...`，`manifest.json` 最后写入作为"完成"标记。
- 任务消息契约：`shared.contracts.parsing.ParseJob`（job_id / s3_key / tenant_id / namespace ...）；
  产物契约：`shared.contracts.artifact.Manifest`。

## 目录结构

```text
01_parsing-service/
├── worker/
│   └── services/document_parser/
│       ├── ir/            # Block（对外 IR）+ ParsedRow/列契约
│       ├── state_machine/ # 任务级状态机（pending → … → done/failed）
│       ├── orchestration/ # ParseInput/Session/Output、适配器、路由、流水线、后处理
│       ├── profiling/     # 文档画像（页数/加密探测）
│       ├── formats/
│       │   ├── markdown/  # 行扫描状态机（Markdown/PDF 共用引擎）
│       │   └── pdf/       # 文本提供器 + 分片归 md
│       ├── packaging/     # manifest / chunks / 各视图写入（manifest 最后写）
│       ├── storage/       # ArtifactStorage（local / S3）
│       ├── tasks.py       # parse_task（Celery 注册名 app.core.tasks.document_ingestion_tasks.parse_task）
│       └── worker_app.py  # Celery 应用入口（python -m 启动）
└── readme.md
```

## 核心设计决策

目标设计详见 `docs/parsing-service/`；当前代码是 MVP 骨架，差异对照见
`docs/parsing-service/06-reference-implementation.md`。

- **统一中间表示（IR）**：所有格式先归一成扁平 Block 集合（层级编码在 `section_path`），
  `full.md` / `chunks.json` / `tables/*.html` / `doc_nav.json` 都是 IR 的序列化视图。
- **流水线**：profile → route（适配器）→ extract → structure（标题/目录）→ serialize →
  chunk → package（manifest 最后写）。
- **适配器**：`DocumentParseAdapter` Protocol + frozen dataclass + lazy import；新增格式 =
  新适配器 + 路由表一行。
- **PDF 收敛回 Markdown**：分片后"万物归 md"，再进同一台行扫描状态机。
- **分块**：层级锚定 + 父子分块（父 chunk 聚合正文，表格/图片独立子 chunk 挂父链）。
- **状态机两层**：管线级线性流转（`parse_pipeline`）+ 任务级状态机（`JobStateMachine`，
  纯内存，落库时映射 job 表）。
- **产物**：`manifest.json`（阶段耗时 / token / 成本 / 统计）最后写 = 完成标记；下游只认
  含 manifest 的目录。

## 启动与镜像

```bash
# 开发（celery 未装时 parse_task 退化为纯函数直调）
PYTHONPATH=src/01_parsing-service python -m worker.services.document_parser.worker_app

# 独立镜像（队列消费者，构建上下文 = services/arkhiv 仓库根）
docker build -f apps/rag-core/Dockerfile.worker -t ogas-parsing-worker .
```

## 演进路线

- MVP（当前）：PDF 文本层 + Markdown + 规则结构 + 层级分块，已打通"上传 → 消费 → 产物包"。
- V2：API 侧闭环（建 job → 入队 → 回写）、Office 适配器、LLM 辅助标题/摘要、队列级 e2e。
- V3：MinerU/OCR、飞书/网页、视觉解析、评测闭环。

两个原则贯穿始终：规则优先、LLM 兜底；产物可追溯（chunk 能反查原文）。
