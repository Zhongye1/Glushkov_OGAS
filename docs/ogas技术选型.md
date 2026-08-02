# OGAS 技术选型

> 本文档整合 [RFC-20260802](../RFC.md) 中五组件的职责边界与交互关系，落到可实现的代码层面选型，是 OGAS 后端的技术选型单一入口。前端工程（agentic RAG 三端 monorepo）的选型见 `docs/monorepo技术选型.md`。

## 1. 选型原则

- **控制面/执行面分离**：Dispatcher 不碰代码、密钥、prompt，只做协调；编排（Flow）做确定性、零推理的图推进。
- **语言边界 = 架构边界**：组件间一律通过 Dispatcher 的版本化 API facade（REST + WebSocket）交互，不共享内存与内部表，因此异构语言不会产生跨进程耦合。
- **改动集中在上游的适配层与扩展层**：Dispatcher fork Multica、Arkhiv 改造 EagleRAG、liskin 直接用上游，均不侵入核心。
- **MVP 刻意做窄**：第一版只做线性串联与简单依赖解锁，不引入 Kafka/Temporal 等重型基础设施，等失败语义与并行需求稳定后再扩。

## 2. 选型总览

| 组件       | 语言/运行时        | 框架与库                                      | 存储                                               | 通信方式                          | 部署                          | 来源         |
| ---------- | ------------------ | --------------------------------------------- | -------------------------------------------------- | --------------------------------- | ----------------------------- | ------------ |
| Gate       | TypeScript / Node  | Hono + `@larksuiteoapi/node-sdk` + ws         | 无（无状态）                                       | 飞书事件回调 / Dispatcher WS      | Docker / 二进制               | RFC 4.3      |
| Flow       | TypeScript / Node  | Hono + 纯 DAG 库 + Zod + pg                   | 复用 Dispatcher Postgres（只读事件 + flow_events） | Dispatcher WS 订阅 + facade REST  | Docker / 二进制               | RFC 4.4      |
| Dispatcher | Go                 | fork Multica，gorilla/coder WebSocket         | Postgres                                           | REST + WebSocket                  | Docker Compose / 二进制 / K8s | RFC 3.3、4.2 |
| Arkhiv     | 沿用 EagleRAG 栈   | MCP Server（streamable HTTP + stdio）+ Milvus | Milvus 向量库                                      | MCP（被 liskin 以 ToolPort 注入） | Docker                        | RFC 3.2、4.5 |
| liskin     | TypeScript         | 上游既定：pnpm monorepo，Hono + SQLite        | SQLite + Harness                                   | stdin/stdout（`agent exec`）      | 本地开发机 Daemon 驱动        | RFC 3.1      |
| 审批 H5 页 | TypeScript / React | Vite + Tailwind                               | -                                                  | 跳转式强身份校验                  | Vercel / 静态托管             | RFC 4.3      |

## 3. Gate（入口面，TS）

**角色**：飞书群 ↔ Dispatcher 的翻译器。群内指令 → facade API 调用，状态事件 → 群消息。

| 关注点          | 选型                               | 说明                                                        |
| --------------- | ---------------------------------- | ----------------------------------------------------------- |
| 语言            | TypeScript / Node（Hono）          | 与 liskin、审批页同栈；飞书官方维护 Node SDK                |
| 飞书接入        | `@larksuiteoapi/node-sdk`          | 事件订阅回调、发送群消息、卡片；官方 SDK 免去自研签名与重试 |
| Dispatcher 通信 | facade REST + WebSocket 订阅（ws） | 指令走 REST；状态事件走 WS 订阅，镜像成飞书群消息           |
| 状态回流粒度    | 全量 / 终态 / 混合（项目级配置）   | 混合模式：AGENT 全量、GATE 终态；RFC 4.3 定义               |
| 高危操作        | 只提示、不执行，跳转 H5 审批页     | 生产回滚 / promote / 改部署检查配置；强身份校验界面         |
| 审批页          | Vite + React + Tailwind            | 飞书内嵌 H5；与前端工程同栈，审批 UI 可复用前端组件规范     |

## 4. Flow（编排面，TS）

**角色**：消费 Dispatcher 终态事件，用 `next_ready` 纯函数推进 DAG，向 facade 下发派单指令。不执行代码、不调用 LLM。

| 关注点          | 选型                                                    | 说明                                                                                                                     |
| --------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 语言            | TypeScript / Node（Hono）                               | 用户已确认；与 Gate、liskin 同栈                                                                                         |
| DAG 数据结构    | 纯 DAG 库（graphology，备选 dependency-graph）          | 只做环检测、拓扑排序、祖先后代查询；graphology 维护活跃、API 全，dependency-graph 更轻，视规模二选一，必要时自写 ~100 行 |
| DAG 定义        | YAML 进 Git                                             | 可 review、可 diff；Zod 校验 schema + 图算法校验（环/可达性/GATE 表达式可解析）                                          |
| GATE 判定表达式 | 第一版用 JSONPath 起步，预留 CEL 升级                   | 线性串联阶段判定简单，JSONPath 心智最轻；条件分支出现后再评估 CEL/自定义 DSL                                             |
| 事件溯源        | 复用 Dispatcher 的 Postgres                             | Flow 不另存权威副本：订阅 WS 事件流，进程重启从头 fold 重建已完成集合；写 `flow_events` 表兜底审计                       |
| 推进逻辑        | 自写纯函数 `next_ready(拓扑, 已完成集合) -> 待派发列表` | 逻辑简单，不值得上重型框架；天然幂等、可单测                                                                             |
| 失败语义        | 重试归 Dispatcher，编排归 Flow                          | Flow 只读终态（Completed / 重试耗尽 / Cancelled），绝不自己重试                                                          |
| 校验            | 提交时静态校验 + dry-run 模拟（OrchBench 思路）         | mock liskin 喂合成终态，跑 `next_ready` 验依赖正确性/无冗余派单/无死锁                                                   |
| 升级路径        | 条件分支/并行汇聚/自动补偿出现后 → Temporal/Cadence     | 第一版刻意不上，等真实失败语义稳定                                                                                       |
| 测试            | Vitest                                                  | 纯函数推进器与事件 fold 的单元测试成本极低                                                                               |

## 5. Dispatcher（控制面，Go）

**角色**：中心化任务调度器，fork Multica。Server/Daemon 双进程，任务状态机 Queued → Dispatched → Running → Completed/Failed/Cancelled。

| 关注点         | 选型                                                          | 说明                                                                                          |
| -------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 语言           | Go（跟随上游 Multica）                                        | fork 保证可周期性 rebase 上游；控制面稳定优先                                                 |
| fork 改动      | 四处：liskin runtime 注册、状态事件引出、ask 通道、API facade | 不侵入核心调度路径（RFC 4.2）                                                                 |
| liskin runtime | 仿 pi adapter 注册 liskin provider                            | Daemon 拉起 `liskin agent exec`，stdin/stdout 驱动；MVP 可先薄 shim                           |
| 任务队列       | Postgres 表 + 状态机，MVP 不引入 Kafka/Redis                  | 单机协调规模够用；事件导出走 Postgres 与 WS                                                   |
| WebSocket 枢纽 | gorilla/websocket 或 coder/websocket                          | 任务下发、状态事件订阅、ask 双向通道                                                          |
| 事件语义       | 每次状态流转发一个可订阅事件                                  | Flow/Gate 均消费；"重试耗尽"与 Failed 区分用事件类型或 `retry_exhausted` 字段，设计文档二选一 |
| 部署           | Docker Compose / 二进制 / K8s（上游既定三形态）               | 执行机形态（人手一台 vs 集中执行机）在阶段二前拍板                                            |

## 6. Arkhiv（知识面，沿用 EagleRAG 栈）

**角色**：业务知识库 MCP Server。底层复用 EagleRAG 检索引擎，改造集中在权限与命名空间封装。

| 关注点         | 选型                                        | 说明                                                                   |
| -------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| 底座           | Python（fork EagleRAG，MCP Server + Milvus）| 提供 `/mcp`（streamable HTTP）与 stdio；ingest/query/retrieve 直接复用 |
| 权限封装       | 在 plugin_namespace 上叠加 workspace 级权限 | 不同业务线知识库隔离，成员按 workspace 检索（RFC 4.5）                 |
| 命名空间结构   | PRD / 接口契约 / UI 规范 / 历史决策         | 结构化知识分区，供 Agent 检索时缩小范围                                |
| 与 liskin 对接 | 作为 MCP 工具经 ToolPort 注入               | liskin 的 MCP client 是阶段一主线，Arkhiv 就是它的首个工具来源         |
| 待确认         | 封装层改动量（语言已确认 Python）            | 权限/命名空间封装若改动量大，需评估自研检索入口的替代方案     |

## 7. liskin（执行面，上游既定）

- 上游已确认：TypeScript、pnpm monorepo，`packages/{core,tools,llm,server}`（Hono + SQLite），CLI 提供 `agent exec / chat / serve`。
- OGAS 不改内核，只在集成层适配：Daemon 进程驱动 + Sandbox 三档确认（auto/ask/deny）插人工卡点 + ToolPort 注入 MCP 工具。
- 后续通过 SDK 支持其他 SOTA Agent（Claude Code、Codex）时，Dispatcher 侧只需新增对应 runtime adapter，语言栈不受影响。

## 8. 横切选型

| 关注点       | 选型                           | 说明                                                                                         |
| ------------ | ------------------------------ | -------------------------------------------------------------------------------------------- |
| ask 双向通道 | WebSocket 子协议               | Dispatcher 第三层改动；Gate 桥接飞书群提示，确认动作跳转 H5 审批页并回调回灌 liskin stdin    |
| 可观测性     | OpenTelemetry（trace ID 贯穿） | 飞书消息 → Gate → Flow → Dispatcher → Daemon → liskin → Vercel 全链路                        |
| CI           | GitHub Actions                 | TS 组件复用前端 monorepo 工具链（pnpm + oxlint + Vitest）；Go 组件 `go test` + golangci-lint |
| 密钥         | 仅 Daemon 环境变量透传         | Dispatcher 与 Gate 都看不到 GitHub/Vercel token                                              |

## 9. 待确认项

- **执行机形态**：人手一台常驻开发机 vs 内网集中执行机，直接影响 Dispatcher 部署拓扑与 Daemon 注册策略（阶段二前拍板）。
- **事件总线时机**：MVP 按本文档走 WS + Postgres；当出现并行汇聚、跨系统事件重放或补偿需求时，再评估 Kafka/NATS 或直接升级 Temporal。
- **Arkhiv 封装改动量**：语言已确认 Python；评估权限/命名空间封装的改动量，决定纯增量改造还是重写检索入口。
- **审批页托管位置**：飞书内嵌 H5 还是独立 Web 审批系统，以及身份校验强度定义。

## 10. 来源

- RFC-20260802：3.1–3.5 现状与依赖、4.2–4.6 五组件工程方案、其他关注点（DAG 状态 / 部署安全 / 可观测性 / 语言选型 / Gate 交互协议）
- `docs/todo/设计文档补充.md`：七份设计文档拆解（Dispatcher fork、Flow、Gate 等），本文档的选型结论是撰写正文的前提
