# Monorepo 完整文件结构（前端 + OGAS）

> 在现有前端三端 monorepo 之上，把 OGAS（Gate / Flow / Dispatcher / Arkhiv）收进同一仓库。前端部分沿用 `specs/architecture-file-structure.md` 与 `docs/monorepo初始化方案.md` 的既有约定，本文档只描述增量结构与边界。

## 1. 一个仓库、两个系统、三个交汇点

- **一个仓库**：统一的 pnpm workspace + Turborepo 编排，单一 CI，一次 clone 即可同时开发前端与 OGAS。
- **两个系统**：前端（agentic RAG 三端，TS/React）与 OGAS（后端四组件，TS + Go + Python）各自保持内部结构与依赖边界。
- **三个交汇点**：
  1. `apps/approval`——OGAS Gate 的高危操作审批页，复用前端设计系统；
  2. `shared/schema`——全仓契约层，扩展 OGAS 的任务状态 / DAG / 事件 / ask schema；
  3. 根级工具链——pnpm + Turborepo 统一编排 TS 部分，`go.work` 管理 Go 部分，Python 部分独立管理。

## 2. 总览目录树

```
Glushkov_OGAS/
├── apps/                            # 前端运行时宿主 + OGAS 审批页（pnpm workspace）
│   ├── web/                         #   Next.js App Router（唯一 SSR target）
│   ├── desktop/                     #   Electron 桌面端（纯 CSR）
│   ├── extension/                   #   浏览器扩展（纯 CSR，MV3）
│   └── approval/                    # ★ OGAS Gate 审批 H5（Vite + React + Tailwind）
├── packages/                        # 共享 TS 包（pnpm workspace，原样保留）
│   ├── platform/                    #   环境差异抽象：只导出接口与 context
│   ├── core/                        #   agentic RAG 核心逻辑（禁环境全局）
│   ├── ui/                          #   设计系统组件（禁环境全局）
│   └── features/                    #   业务功能模块（禁环境全局）
├── shared/                          # 全仓契约层（pnpm workspace，扩展）
│   ├── schema/                      #   Zod：SSE 消息 / Agent 步骤 / 任务状态 / DAG / 事件 / ask
│   ├── generated/                   #   codegen 产物（schema → 类型）
│   └── constants/                   #   常量与枚举
├── services/                        # ★ OGAS 后端服务（多语言，不进 apps/packages）
│   ├── gate/                        # ★ TS：飞书入口适配（Hono + @larksuiteoapi/node-sdk）
│   ├── flow/                        # ★ TS：DAG 编排（Hono + 纯 DAG 库 + pg）
│   ├── dispatcher/                  # ★ Go：控制面（fork Multica，独立 go.mod + REBASE.md）
│   └── arkhiv/                      # ★ Python：知识面（fork EagleRAG + Milvus，REBASE.md）
├── infra/                           # ★ 部署与运维
│   ├── compose/                     #   docker-compose：gate/flow/dispatcher/arkhiv/postgres/milvus
│   ├── k8s/                         #   （可选）K8s manifests
│   └── scripts/                     #   初始化、迁移、一键拉起、liskin runtime 安装注册
├── .devcontainer/                    # ★ Dev Container（Windows/不熟悉 Nix 的备选）
├── flake.nix / .envrc               # ★ Nix devShell 环境管理（团队跨平台）
├── specs/                           # 前端规格（ADR / 功能规格 / 模板，原样保留）
├── docs/                            # 文档（RFC、选型、结构、设计文档拆解）
│   └── todo/                        #   设计文档补充（七份正文待写）
├── go.work                          # ★ Go workspace（services/dispatcher）
├── pnpm-workspace.yaml              # TS workspace：apps/* + packages/* + shared/* + services/{gate,flow}
├── turbo.json                       # 任务编排（TS pipeline；Go/Python 以独立 task 接入）
├── package.json / tsconfig.base.json / oxlint.json / oxfmt.json / dependency-cruiser
├── Readme.md                        # 项目简介（六段式 README）
└── RFC.md                           # RFC-20260802（OGAS 架构）
```

## 3. 各部分职责

### 3.1 apps（前端宿主 + 审批页）

| 目录             | 职责                                               | 依赖来源                 |
| ---------------- | -------------------------------------------------- | ------------------------ |
| apps/web         | 唯一 SSR target，agentic RAG Web 端                | packages/*、shared/*     |
| apps/desktop     | Electron 纯 CSR                                    | packages/*、shared/*     |
| apps/extension   | 浏览器扩展纯 CSR（MV3）                            | packages/*、shared/*     |
| apps/approval ★  | OGAS 高危操作审批页：跳转式强身份校验 + 确认动作   | packages/ui、shared/schema |

`apps/approval` 归入前端 apps 的理由：它是 Vite + React + Tailwind 应用，复用 `packages/ui` 设计系统与 `shared/schema` 的 ask/任务状态契约，只是业务上服务 OGAS。它与 `services/gate` 通过 HTTP API 交互，不直接 import。

### 3.2 packages（共享 TS 包，不变）

`platform` / `core` / `ui` / `features` 维持原有分层与"禁环境全局"约束。OGAS 的 TS 服务不依赖这些包（服务端无环境差异问题），唯一例外是审批页复用 `packages/ui`。

### 3.3 shared（全仓契约层，扩展 OGAS 契约）

在现有 `schema/generated/constants` 基础上，`shared/schema` 新增 OGAS 契约文件：

| 新增 schema       | 内容                                   | 消费方                     |
| ----------------- | -------------------------------------- | -------------------------- |
| `task.ts`         | Dispatcher 任务状态机与 issue 实体     | gate / flow / approval     |
| `event.ts`        | 终态事件（Completed / 重试耗尽 / Cancelled） | flow / gate          |
| `dag.ts`          | DAG 定义（AGENT/GATE/JOIN、depends_on、check） | flow / approval     |
| `ask.ts`          | ask 双向通道消息与确认回灌格式          | gate / approval / flow     |

`shared/` 是全仓唯一被所有 TS 侧依赖的层，禁止反向依赖任何 app/package/service。

### 3.4 services（OGAS 后端服务）

| 目录              | 语言/栈                  | 职责                                     | workspace 归属                  |
| ----------------- | ------------------------ | ---------------------------------------- | ------------------------------- |
| services/gate ★   | TS / Hono                | 飞书事件回调 → facade 指令；状态事件 → 群消息 | pnpm workspace                 |
| services/flow ★   | TS / Hono                | 消费终态事件，`next_ready` 推进 DAG      | pnpm workspace                 |
| services/dispatcher ★ | Go（fork Multica）   | 协调中枢：workspace/issue/队列/权限/WS hub | go.work（独立 go.mod）        |
| services/arkhiv ★ | Python（fork EagleRAG）  | 知识面 MCP Server（Milvus + 权限封装）   | 独立（uv/pip + 独立工具链）     |

- `services/gate` 与 `services/flow` 是 TS 服务，纳入 pnpm workspace，复用根级 oxlint / oxfmt / Vitest 工具链与 `shared/schema`。
- `services/dispatcher` 是 Go module，不进入 pnpm workspace；Turborepo 中为其声明独立 `build` / `test` / `lint` task（执行 `go build ./...`、`go test ./...`、`golangci-lint run`）。
- `services/arkhiv` 是 Python 项目（EagleRAG 为 Python），用 `uv`（或 pip）独立管理依赖，工具链沿用 EagleRAG 既有约定（ruff / pytest 一类），不并入 pnpm workspace。
- **fork 组织方式（已确认）**：dispatcher 与 arkhiv 均直接复制上游代码进 `services/`，各自带 `REBASE.md` 记录上游仓库地址、基线版本与同步流程（如何对比、如何合入、改动点清单），支持周期性 rebase 上游。
- 服务间纪律：一律经 Dispatcher 版本化 facade（REST + WebSocket）交互，不互相 import、不读对方内部表。

### 3.5 liskin（执行面上游，各执行机环境安装）

- **liskin 不进入仓库**。作为外部 CLI 安装在每台执行机上，Dispatcher Daemon 启动时扫描 PATH 上的 AI CLI 并注册成 runtime（与 pi 的注册方式同构），通过 `liskin agent exec` 的 stdin/stdout 驱动。
- 版本管理：由各执行机安装的 liskin 版本决定；`infra/scripts/install-liskin.sh` 固化安装与版本检查，避免机器间漂移。
- 后续支持其他 SOTA Agent（Claude Code、Codex）时，同样走"执行机安装 + Daemon 注册 runtime"的路径，不改变仓库结构。

### 3.6 infra（部署与运维）

- `infra/compose/docker-compose.yml`：一键拉起 gate / flow / dispatcher / arkhiv / postgres / milvus。
- `infra/k8s/`：阶段二起按需补充。
- `infra/scripts/`：初始化（建库、迁移、一键拉起）、liskin runtime 安装注册。

## 4. 多语言编排

| 关注点           | 方案                                                         |
| ---------------- | ------------------------------------------------------------ |
| TS 依赖图        | pnpm workspace：apps/* + packages/* + shared/* + services/{gate,flow} |
| Go 依赖图        | `go.work` 收录 services/dispatcher（未来新增 Go 服务时追加） |
| Python 依赖图    | services/arkhiv 独立：`uv`（或 pip）管理，不参与根级 workspace |
| 任务编排         | Turborepo 统一入口：TS 走既有 pipeline；Go/Python 服务声明独立 task（`go test` / `golangci-lint` / `pytest` / `ruff`），按依赖关系编排 |
| 兜底脚本         | 根 `Makefile` 提供 `make dev` / `make test` / `make infra-up` 等聚合命令 |
| CI               | GitHub Actions：`pnpm` 部分（turbo run lint+typecheck+test+build）+ `go` 部分（go test + golangci-lint）+ `python` 部分（pytest + ruff，仅 arkhiv 变更时触发） |

## 5. 对既有约定与初始化步骤的影响

- 保留：apps 互不引用、core/ui/features 禁环境全局、dependency-cruiser 单向依赖、codegen 漂移校验。
- 目录骨架扩展：新增 `apps/approval`、`services/*`、`infra/*`（对应 `docs/monorepo初始化方案.md` 第 5 节第 2 步）。
- 新增初始化步骤：初始化 `go.work`、复制 fork 并编写 `services/{dispatcher,arkhiv}/REBASE.md`、编写 docker-compose、各执行机安装 liskin 并注册 runtime、CI 增加 Go/Python 检查。
- 文档入口：`docs/monorepo初始化方案.md` 负责前端部分，本文档负责含 OGAS 的完整结构。

## 6. 待确认项

- **执行机形态**：人手一台常驻开发机 vs 内网集中执行机，直接影响 Dispatcher 部署拓扑与 Daemon 注册策略（阶段二前拍板）。
- **事件总线时机**：MVP 走 WS + Postgres；并行汇聚、跨系统事件重放或补偿需求出现后，再评估 Kafka/NATS 或直接升级 Temporal。
- **审批页托管位置**：飞书内嵌 H5 vs 独立 Web 审批系统，以及身份校验强度定义。
- **Multica 许可证合规**：NOASSERTION 许可证的法务确认，直接决定 dispatcher fork 路线是否成立（已确认的组织方式是前置假设）。
