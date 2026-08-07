# RAG 平台

统一 RAG 内核 + 协议外壳（MCP / REST）+ Go 网关的 monorepo。

## 目录结构

```text
RAG/
├── apps/
│   ├── gateway/            # Go 网关 (Hertz)
│   ├── rag-core/           # Python FastAPI + RAG 内核
│   └── web/                # Next.js SSR
├── packages/
│   ├── contracts/          # API 契约 (OpenAPI / Protobuf)
│   ├── ts-sdk/             # 由契约生成的 TS 客户端
│   └── ui/                 # 前端共享组件 (可选)
├── docker-compose.yml
├── Taskfile.yml
└── README.md
```

## 设计要点

- 内核与协议分离：`rag-core` 只暴露 `retrieve()` / `answer()` 两个语义化入口
- 对外能力：coding agent 走 MCP 工具，Web 用户走 REST（Next.js SSR → Go 网关 → FastAPI）
- 检索链路：文档解析 → 切片 → 向量化 → 混合检索 (向量 + BM25, RRF 融合) → 重排 → 生成

## 快速开始

```bash
task dev:rag-core   # 启动 RAG 内核
task dev:gateway    # 启动 Go 网关
task dev:web        # 启动 Next.js
task test:rag-core  # 运行 rag-core 测试
task check:rag-core # rag-core 全量检查 (test + lint + typecheck)
```

详见各子目录 README。
