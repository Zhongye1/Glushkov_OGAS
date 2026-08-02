# Agentic RAG 前端工程 — 规格总览

本目录是整个前端工程的规格单一事实源（Spec-Driven Development）。它描述的是「打算做什么、为什么这么设计」，与 `docs/`（现状说明）和 `notes/`（过程草稿）分工不同。

## 这套工程要解决什么

我们要构建一个 agentic RAG 应用的前端，它同时跑在三个宿主上：一个带 SSR 的 Web 站点、一个 Electron 桌面端、一个浏览器扩展。核心难点不在于任何单一端，而在于三端之间如何最大化复用业务代码，同时让实时对话、检索、工具调用这类运行时动态生成的内容各得其所。

整套设计的内核是 bulletproof-react 的单向分层原则，外面套一层 monorepo 来隔离多运行时。SSR 只作为一个独立的 Web target 存在，绝不强行让 Electron 也去做服务端渲染。Web 和 Electron 通过「逻辑层全复用、组件层靠 platform adapter 复用」来共享代码，而环境差异被一个专门的抽象层彻底吸收。

## 目录组织

- `adr/` 存放架构决策记录，只增不改，每条决策带背景、决策内容和后果。当一条决策被推翻时，新增一条来 supersede 旧的，而不是修改历史。
- `features/` 按功能组织规格，每个功能一个子目录，内含 requirements、design、tasks 三份文档，与代码包的物理组织解耦。
- `templates/` 存放 feature spec 和 ADR 的空白模板，供新功能直接复制填写。

## 已归档的架构决策

| 编号     | 决策                                                         | 状态     |
| -------- | ------------------------------------------------------------ | -------- |
| ADR-0001 | 采用 pnpm workspace + Turborepo 作为 monorepo 底座           | Accepted |
| ADR-0002 | SSR 只在 Web target，Electron 与扩展保持纯 CSR               | Accepted |
| ADR-0003 | 用 platform adapter 抽象层吸收三端环境差异                   | Accepted |
| ADR-0004 | 代码质量工具链选型（oxlint / oxfmt / dependency-cruiser 等） | Accepted |

## 已归档的功能规格

| 功能               | 说明                                           |
| ------------------ | ---------------------------------------------- |
| share-page         | 可被外部抓取、秒开的分享页，SSR 的典型受益场景 |
| agentic-stream     | 实时对话、Agent 中间步骤、检索轨迹的流式渲染   |
| monorepo-toolchain | 整套代码质量与工程治理工具链的落地             |
