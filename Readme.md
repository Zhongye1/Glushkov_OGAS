# OGAS — Operational Generate Agent System

> **状态**：Draft · **RFC**：[RFC-20260802](RFC.md) · **协议**：待定（见文末）

RFC：https://zhongye1.github.io/posts/rfc_agentic_project/2026-07-25-rfc-glushkov_ogas/

<p align="center">
<img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
<img src="https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=white" alt="React" />
<img src="https://img.shields.io/badge/Jotai-000000?style=flat-square" alt="Jotai" />
<img src="https://img.shields.io/badge/TanStack_Query-FF4154?style=flat-square" alt="TanStack Query" />
<img src="https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js" />
<img src="https://img.shields.io/badge/Electron-47848F?style=flat-square&logo=electron&logoColor=white" alt="Electron" />
<img src="https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white" alt="Vite" />
<img src="https://img.shields.io/badge/SSE%2FRSC_streaming-5C6BC0?style=flat-square" alt="SSE/RSC streaming" />
<img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
<img src="https://img.shields.io/badge/Hono-E36002?style=flat-square&logo=hono&logoColor=white" alt="Hono" />
<img src="https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go" />
<img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/Zod-3E67B1?style=flat-square&logo=zod&logoColor=white" alt="Zod" />
<img src="https://img.shields.io/badge/WebSocket-673AB7?style=flat-square" alt="WebSocket" />
<img src="https://img.shields.io/badge/MCP-1E88E5?style=flat-square" alt="MCP" />
<img src="https://img.shields.io/badge/graphology-6747A1?style=flat-square" alt="graphology" />
<img src="https://img.shields.io/badge/Feishu_SDK-3370FF?style=flat-square" alt="Feishu SDK" />
<img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
<img src="https://img.shields.io/badge/Milvus-00A1EA?style=flat-square" alt="Milvus" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
<img src="https://img.shields.io/badge/pnpm-F69220?style=flat-square&logo=pnpm&logoColor=white" alt="pnpm" />
<img src="https://img.shields.io/badge/Turborepo-EF4444?style=flat-square&logo=turborepo&logoColor=white" alt="Turborepo" />
<img src="https://img.shields.io/badge/Nix-5277C3?style=flat-square&logo=nixos&logoColor=white" alt="Nix" />
<img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white" alt="GitHub Actions" />
<img src="https://img.shields.io/badge/Vitest-6E9F18?style=flat-square&logo=vitest&logoColor=white" alt="Vitest" />
<img src="https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white" alt="Playwright" />
<img src="https://img.shields.io/badge/oxlint%2Foxfmt-2D9CDB?style=flat-square" alt="oxlint/oxfmt" />
<img src="https://img.shields.io/badge/lefthook-7B61FF?style=flat-square" alt="lefthook" />
<img src="https://img.shields.io/badge/dependency-cruiser-6A5ACD?style=flat-square" alt="dependency-cruiser" />
<img src="https://img.shields.io/badge/changesets-2D3748?style=flat-square" alt="changesets" />
<img src="https://img.shields.io/badge/syncpack-5B5BD6?style=flat-square" alt="syncpack" />
<img src="https://img.shields.io/badge/OpenTelemetry-000000?style=flat-square&logo=opentelemetry&logoColor=white" alt="OpenTelemetry" />
</p>

**OGAS把编码 Agent 接入团队研发生命周期的协作平台**——需求经 DAG 编排与受控派发，由 Agent 执行到代码交付与线上部署，全程可见、可评审、可回滚。其设计目标在于解决单个 Agent 只是"某人机器上的一个 loop"，团队无法 review 执行链路；多任务有先后依赖却无人编排；评审、CI、部署等可验证环节靠人肉衔接，没有闭环等诸多痛点。

## 架构

![](https://pic4.zhimg.com/v2-c7e8e75221bb2c108789f34db132c601_r.jpg)

| 组件            | 角色                                             | 底层/来源                        |
| --------------- | ------------------------------------------------ | -------------------------------- |
| OGAS-Gate       | 入口面：飞书机器人适配，群消息 ↔ Dispatcher 翻译 | 自研（TS/Hono）                  |
| OGAS-Flow       | 编排面：跨任务 DAG 依赖调度与解锁                | 自研（TS/Hono）                  |
| OGAS-Dispatcher | 控制面：任务队列、状态机、WebSocket 枢纽         | fork Multica（Go）               |
| liskin          | 执行面：编码 Agent 内核                          | 上游（TS，各执行机安装）         |
| OGAS-Arkhiv     | 知识面：业务知识库 MCP Server                    | fork EagleRAG（Python + Milvus） |
| apps/\*         | agentic RAG 三端前端 + 审批页                    | 自研（Next.js / Vite / MV3）     |

## 仓库结构

```
Glushkov_OGAS/
├── apps/            # 前端运行时宿主：web（SSR）/ desktop（Electron）/ extension（MV3）/ approval（审批页）
├── packages/        # 共享 TS 包：platform / core / ui / features（单向依赖，禁环境全局）
├── shared/          # 全仓契约层：schema（Zod，含 OGAS task/dag/event/ask）/ generated / constants
├── services/        # OGAS 后端：gate / flow（TS）、dispatcher（Go fork）、arkhiv（Python fork）
├── infra/           # docker-compose（postgres 等）、初始化脚本
├── specs/           # 前端规格：ADR / 功能规格 / 模板
├── docs/            # 选型、结构、初始化、搭建记录、环境管理、设计文档拆解
├── flake.nix        # Nix devShell（跨平台环境）
├── RFC.md           # RFC-20260802（OGAS 架构）
└── Readme.md        # 本文档
```

完整结构与边界规则见 [docs/monorepo文件结构.md](docs/monorepo文件结构.md)。

## 快速开始

前置要求（满足其一即可）：

| 方案        | 要求                                                                                  |
| ----------- | ------------------------------------------------------------------------------------- |
| Nix（推荐） | [Determinate Nix Installer](https://install.determinate.systems/nix)；Windows 走 WSL2 |
| 手动        | Node.js ≥ 22、pnpm 11（corepack）、Go ≥ 1.25、Python ≥ 3.11                           |

```bash
git clone <repo-url> && cd Glushkov_OGAS

# 环境（二选一）
nix develop                          # Nix 路径：自动锁定 node/pnpm/go/python
corepack enable && corepack prepare pnpm@11.14.0 --activate   # 手动路径

pnpm install        # 安装全部 workspace 依赖（含 turbo/oxlint/oxfmt 工具链）
pnpm build          # 按拓扑构建 shared → packages → apps → services
pnpm test           # 单测/组件测
```

**验证**：`pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm depcruise && pnpm syncpack` 全绿即环境就绪。

**常见问题**

| 现象                                         | 处理                                                                               |
| -------------------------------------------- | ---------------------------------------------------------------------------------- |
| `ERR_PNPM_IGNORED_BUILDS`                    | 构建脚本白名单配置在 `pnpm-workspace.yaml#allowBuilds`（esbuild/lefthook 等）      |
| `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY` | CI/无 TTY 环境：`confirmModulesPurge: false` 已在 workspace 配置                   |
| sharp 源码构建失败                           | 无害噪音：预编译二进制经 optionalDependencies 提供，`allowBuilds.sharp` 已关闭     |
| Electron 无二进制                            | 运行 `apps/desktop` 前按 [docs/monorepo搭建记录.md](docs/monorepo搭建记录.md) 补装 |

## 进行开发

**1. 前端三端本地开发**

```bash
pnpm --filter @ogas/web dev          # Next.js SSR 站点（localhost:3000）
pnpm --filter @ogas/approval dev     # OGAS 审批 H5
pnpm --filter @ogas/extension build  # MV3 产物在 dist/
```

**2. 全链路质量门（CI 同款）**

```bash
pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm depcruise && pnpm syncpack
```

**3. OGAS 服务依赖与健康检查**

```bash
docker compose -f infra/compose/docker-compose.yml up -d
pnpm --filter @ogas/gate dev         # Gate（:3001）
pnpm --filter @ogas/flow dev         # Flow（:3002）
curl localhost:3001/health && curl localhost:3002/health
```

**4. DAG 定义校验（Flow）**

```bash
curl -X POST localhost:3002/dag/validate \
  -H 'Content-Type: application/json' \
  -d '{"dag":[{"id":"implement","type":"AGENT","issue":"实现登录页","agent":"liskin-frontend"},{"id":"review","type":"GATE","check":"pr_review_approved","dependsOn":["implement"]}]}'
```

**5. Go 服务（Dispatcher）**

```bash
go work sync
cd services/dispatcher && go build ./... && go vet ./... && go run .
```

**6. 进入 Nix 开发环境**

```bash
nix develop    # 或 direnv allow（进入目录自动加载）
```

## Docs

| 文档                                                     | 说明                                                              |
| -------------------------------------------------------- | ----------------------------------------------------------------- |
| [RFC.md](RFC.md)                                         | RFC-20260802：OGAS 架构（组件职责、任务派发、工程方案、推进计划） |
| [docs/ogas技术选型.md](docs/ogas技术选型.md)             | OGAS 五组件技术选型                                               |
| [docs/monorepo技术选型.md](docs/monorepo技术选型.md)     | 前端技术选型总览                                                  |
| [docs/monorepo文件结构.md](docs/monorepo文件结构.md)     | 含 OGAS 的完整仓库结构                                            |
| [docs/monorepo初始化方案.md](docs/monorepo初始化方案.md) | 前端初始化计划与步骤                                              |
| [docs/monorepo搭建记录.md](docs/monorepo搭建记录.md)     | 实际搭建过程与踩坑修复                                            |
| [docs/环境管理.md](docs/环境管理.md)                     | Nix / Dev Container 跨平台环境                                    |
| [docs/todo/设计文档补充.md](docs/todo/设计文档补充.md)   | RFC 拆解出的七份设计文档待写清单                                  |
| [specs/](specs/)                                         | 前端规格（ADR、功能规格、模板）                                   |

## Roadmap

RFC 推进计划的三阶段：

1. **阶段一**：Arkhiv + liskin 验证 Agent 懂业务（MCP client 是主线）
2. **阶段二**：Dispatcher + Gate + GitHub 协作可见（ask 通道、状态回流飞书群）
3. **阶段三**：Vercel 发布门 + Flow 闭合全链路（回滚 / promote 受控）

每阶段均有失败回退，详见 [RFC.md](RFC.md)。

## 贡献指南与协议

- **提交**：lefthook pre-commit 自动跑 `oxlint --fix` 与 `oxfmt`；多包版本变更走 `changesets`
- **质量门**：GitHub Actions 强制 lint / typecheck / test / build / syncpack / codegen 漂移 / Go build+vet，合并前全绿
- **架构约束**：dependency-cruiser 在 CI 拦截——apps 互不引用；core/ui/features 禁摸环境全局；services 只经 Dispatcher facade 通信
- **RFC 流程**：架构决策先提 Draft 到 `RFC.md`，拆解为 `docs/todo/设计文档补充.md` 的设计文档后再实现


