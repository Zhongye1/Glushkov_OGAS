# rag-core

RAG 内核 + 协议外壳（REST / MCP）。遵循 RAG.md 的分层原则：内核只暴露
`retrieve()` / `answer()` 两个语义化入口，REST 与 MCP 只是薄协议外壳。

## 目录结构

```text
apps/rag-core/
├── src/
│   ├── api/             # FastAPI 路由、Pydantic schemas、MCP server
│   │   ├── app.py       # FastAPI 应用（uvicorn src.api.app:app）
│   │   ├── mcp_server.py # MCP server（python -m src.api.mcp_server）
│   │   └── schemas/     # 接口类型定义（HealthResponse/Chunk/Answer/...）
│   ├── ingest/          # 路由矩阵、Knowhere/PixelRAG 适配器、Celery 任务入口
│   ├── index/           # Milvus 文本/视觉存储、标签目录、文档结构
│   ├── retrievers/      # Knowhere 图检索 + PixelRAG 视觉检索
│   ├── router/          # 查询路由引擎与选择器链、语义缓存（Redis）
│   ├── generation/      # 多模态答案合成（Qwen-VL-Max）
│   ├── eval/            # RAG 评估（RAGAS 等）
│   ├── tasks/           # Celery 应用、任务状态、死信处理
│   ├── db/              # SQLModel 模型与 Alembic 元数据
│   ├── kb/              # 知识库生命周期、统计、健康
│   ├── storage/         # MinIO 客户端、去重
│   ├── attachments/     # QA 附件惰性解析
│   ├── admin/           # 运维指标、探针、MCP 调用日志
│   ├── telemetry/       # 结构化日志与 OpenTelemetry
│   ├── core/config.py   # 配置（pydantic-settings）
│   └── kernel/          # 协议无关的 RAG 内核（retrieve / answer）
├── tests/
├── pyproject.toml
├── Dockerfile
└── .env.example
```

## 关键入口

- API：`uvicorn src.api.app:app`
- MCP：`python -m src.api.mcp_server`
- Workers：`src.tasks.celery_app`（待接入 Celery）
- 配置：`src/core/config.py`（环境变量，见 `.env.example`）

## RAG 流程

1. 文档解析与分块 (Chunking) —— 最影响效果的一环。主流做法是语义分块 / 递归分块 / 按标题层级分块，配合 chunk overlap; 近两年流行 父子分块 (small-to-big): 检索用小块保证精度，喂给 LLM 用大块保证上下文完整。

2. Embedding 向量化 —— 选一个强 embedding 模型 (bge、E5、OpenAI text-embedding-3、Cohere embed 等), 中文场景常用 bge-m3。

3. 混合检索 (Hybrid Search) —— 向量检索 + 关键词检索 (BM25) 融合, 几乎是共识：向量管语义、BM25 管精确术语 / 专名，用 RRF (Reciprocal Rank Fusion) 融合两路结果。

4. 重排 (Reranking) —— 用 cross-encoder reranker (如 bge-reranker、Cohere Rerank) 对召回的候选做精排，只把最相关的少数 chunk 送进 LLM。这一步性价比极高。

5. 上下文构造与生成 —— 把精排后的 chunk 拼 prompt, 要求模型基于给定上下文作答并给出引用, 降低幻觉。

6. 评估 (Evaluation) —— 用 RAGAS 这类框架量化 faithfulness (忠实度)、answer relevancy、context precision/recall, 形成 "改一版就跑一次评测" 的闭环。这是从 demo 走向生产的分水岭。

### 离线链路（接入 → 切片 → 向量化 → 入库）

| 阶段                             | 对应包         |
| -------------------------------- | -------------- |
| 数据源接入、解析适配、解析路由   | `ingest/`      |
| 附件/图表解析（QA 附图、表格）   | `attachments/` |
| 向量化 + 索引构建（文本/视觉）   | `index/`       |
| 原始文件存储、去重               | `storage/`     |
| 异步任务编排（接入/建索引跑批）  | `tasks/`       |
| 文档/库元数据持久化              | `db/`          |
| 知识库生命周期（建库/删库/统计） | `kb/`          |

### 在线链路（query → 路由 → 召回 → 重排 → 生成）

| 阶段                                      | 对应包                               |
| ----------------------------------------- | ------------------------------------ |
| Query 路由（文本/视觉、要不要检索、选库） | `router/`                            |
| 语义缓存（Redis，命中跳过检索+生成）      | `router/cache.py`                    |
| 召回（向量 ANN / 图检索 / 视觉检索）      | `retrievers/`                        |
| 重排（Rerank）                            | `retrievers/`（召回后精排）          |
| 上下文构造 + 答案生成（含引用）           | `generation/`                        |
| 编排内核（retrieve/answer 串起整条链）    | `kernel/`                            |
| 协议外壳（REST / MCP）                    | `api/`（`app.py` / `mcp_server.py`） |

### 评估

| 阶段                                                                     | 对应包  |
| ------------------------------------------------------------------------ | ------- |
| RAG 评估（RAGAS：faithfulness / relevancy / context precision & recall） | `eval/` |

### 横切支撑

| 职责                         | 对应包           |
| ---------------------------- | ---------------- |
| 任务状态、死信处理           | `tasks/`         |
| 运维指标、探针、MCP 调用日志 | `admin/`         |
| 结构化日志 + OpenTelemetry   | `telemetry/`     |
| 配置                         | `core/config.py` |

## 本地开发

```bash
uv sync
uv run uvicorn src.api.app:app --reload --reload-dir src --port 8000
```

## 常用任务

从仓库根目录执行（`dir` 已指向本目录）：

| 命令                      | 说明                         |
| ------------------------- | ---------------------------- |
| `task dev:rag-core`       | 启动服务（自动 `uv sync`）   |
| `task test:rag-core`      | 运行 pytest                  |
| `task lint:rag-core`      | ruff 代码检查                |
| `task typecheck:rag-core` | mypy 类型检查                |
| `task format:rag-core`    | ruff 自动修复 + 格式化       |
| `task mcp:rag-core`       | 启动 MCP Server              |
| `task check:rag-core`     | test + lint + typecheck 聚合 |

## 接口

- `GET /health` 健康检查
- `POST /api/v1/retrieve` 检索片段
- `POST /api/v1/answer` 生成回答（`stream: true` 时返回 SSE 流）

接口的请求/响应类型统一定义在 `src/api/schemas/`（`HealthResponse`、`Chunk`、
`Answer`、`RetrieveRequest`、`AnswerRequest`）。

## MCP Server

```bash
uv run ogas-rag-mcp            # 或 python -m src.api.mcp_server
```

## 待实现（按 RAG.md）

- 文档解析与切片（Tree-sitter 代码切片 / 标题层级切片）
- 向量化（bge-m3 等，走现成 API 渠道）
- 混合检索：向量 + BM25，RRF 融合
- 重排（cross-encoder reranker）
- 生成与引用回填（文件路径 / 行号 / 来源链接）
- 语义缓存（Redis）
