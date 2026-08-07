# rag-core

RAG 内核 + 协议外壳（REST / MCP）。遵循 RAG.md 的分层原则：内核只暴露
`retrieve()` / `answer()` 两个语义化入口，REST 与 MCP 只是薄协议外壳。

## 目录结构

```text
apps/rag-core/
├── src/
│   ├── main.py          # FastAPI 应用
│   ├── core/config.py   # 配置（pydantic-settings）
│   ├── kernel/          # 协议无关的 RAG 内核（retrieve / answer）
│   ├── api/             # REST 协议外壳
│   └── mcp/             # MCP 协议外壳（面向 coding agent）
├── tests/
├── pyproject.toml
├── Dockerfile
└── .env.example
```

## 本地开发

```bash
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

## 接口

- `GET /health` 健康检查
- `POST /api/v1/retrieve` 检索片段
- `POST /api/v1/answer` 生成回答（`stream: true` 时返回 SSE 流）

## MCP Server

```bash
uv run ogas-rag-mcp
```

## 待实现（按 RAG.md）

- 文档解析与切片（Tree-sitter 代码切片 / 标题层级切片）
- 向量化（bge-m3 等，走现成 API 渠道）
- 混合检索：向量 + BM25，RRF 融合
- 重排（cross-encoder reranker）
- 生成与引用回填（文件路径 / 行号 / 来源链接）
- 语义缓存（Redis）
