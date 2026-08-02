# Monorepo 技术选型

> 本文档整合 `specs/` 下已归档 ADR 与功能规格中的技术选型，是 monorepo 技术选型的单一入口；各选型的背景、决策理由与放弃原因见对应 ADR。

## 背景与目标

本工程是一个 agentic RAG 应用的前端，同时跑在三个运行时宿主上：带 SSR 的 Web 站点、Electron 桌面端、浏览器扩展。选型目标是最大化三端业务代码复用，同时保证构建可编排、可增量缓存、质量门槛可强制。

## 选型总览

| 关注点           | 选型                     | 说明                                                  | 来源           |
| ---------------- | ------------------------ | ----------------------------------------------------- | -------------- |
| 包管理           | pnpm workspace           | 严格 node_modules 杜绝幽灵依赖                        | ADR-0001       |
| 任务编排与缓存   | Turborepo                | pipeline 按拓扑顺序编排并增量缓存，codegen 纳入依赖图 | ADR-0001       |
| 前端框架         | React                    | 三端共用同一套组件与逻辑                              | ADR-0002       |
| Web 渲染         | Next.js App Router       | 唯一 SSR target，RSC + streaming                      | ADR-0002       |
| Electron 渲染    | Vite 打包纯 CSR          | 与 SSR 解耦                                           | ADR-0002       |
| 扩展             | MV3 纯 CSR               | 与 SSR 解耦                                           | 架构文件结构   |
| 流式传输         | SSE / RSC streaming      | 对话与 Agent 中间步骤实时渲染                         | agentic-stream |
| 环境差异抽象     | platform adapter         | 只导出接口与 context，各 app 注入实现                 | ADR-0003       |
| 状态管理         | Jotai                    | 运行时状态与实体缓存                                  | agentic-stream |
| 服务端数据       | TanStack Query           | API 请求与缓存                                        | agentic-stream |
| 契约与校验       | Zod                      | shared 中 SSE 消息、Agent 步骤、OpenUI 卡片 schema    | agentic-stream |
| Lint             | oxlint（含 type-aware）  | 多文件分析覆盖循环依赖                                | ADR-0004       |
| 格式化           | oxfmt                    | 含 import 与 Tailwind class 排序，不配 Prettier       | ADR-0004       |
| 架构分层约束     | dependency-cruiser       | 强制单向依赖                                          | ADR-0004       |
| 类型检查（权威） | tsc -b / tsgo            | CI 权威判定，oxlint type-aware 仅本地快检             | ADR-0004       |
| Git hooks        | lefthook                 | 暂存区并行跑 oxlint --fix 与 oxfmt                    | ADR-0004       |
| 版本与发布       | changesets               | 多包版本管理并生成 changelog                          | ADR-0004       |
| 依赖版本一致性   | syncpack / manypkg       | CI 校验跨包依赖版本一致                               | ADR-0004       |
| 单测与组件测     | Vitest                   | 与 Vite 同源，monorepo 友好                           | ADR-0004       |
| E2E              | Playwright               | 覆盖 SSR 的 Web 端与流式对话                          | ADR-0004       |
| 环境变量校验     | @t3-oss/env + Zod        | 可选，后续评估                                        | ADR-0004       |
| 组件开发         | Storybook                | 可选，让 packages/ui 脱离宿主开发                     | ADR-0004       |
| Node 版本锁定    | Volta / .nvmrc + engines | 可选                                                  | ADR-0004       |
| 提交信息规范     | commitlint               | 可选，用 changesets 后可弱化                          | ADR-0004       |

## Monorepo 底座（ADR-0001）

- 包管理器用 **pnpm workspace**。硬链接加严格 node_modules 结构杜绝幽灵依赖，为后续强制的单向依赖架构打底；npm 与 yarn 的扁平化会让底层包意外引用到本不该依赖的东西。
- 任务编排用 **Turborepo**。核心诉求是「codegen → core → ui → features → apps 按序构建并做增量缓存」，由 pipeline 与 dependsOn 覆盖，配置心智极简；codegen 作为可缓存、可追踪的流水线节点，比手写 prebuild 脚本可靠。
- 放弃方案：**Nx**（概念复杂度高，generators 与 enforce-module-boundaries 对当前规模不划算，保留未来迁移空间）、**yarn berry**（配置心智重）、**npm workspace**（编排能力弱）。

## 运行时与渲染（ADR-0002）

- **SSR 只在 Web target**。Next.js App Router 的 RSC 加 streaming 模型与 agentic RAG 的数据形态最贴合：外壳与历史回放用服务端组件直出，实时对话区标 "use client" 接管流式。
- SSR 覆盖四类内容：应用外壳与导航骨架、已完成对话的静态回放与分享页、知识库与文档浏览页、静态配置与元信息；LLM 逐 token 回答、Agent 中间步骤与工具调用轨迹等运行时内容走 SSE 或 RSC streaming，不做传统 SSR。
- **Electron renderer 用 Vite 打包的纯 CSR**，浏览器扩展同为纯 CSR（MV3），复用 Web 端除 SSR 入口以外的一切。
- 放弃方案：**Pages Router**（仅作为老代码迁移场景的退路）、**全站 SSR**（主体是多运行时 CSR 应用，收益低而约束大）。

## 架构分层（ADR-0003）

- 复用按三层切分：纯逻辑（业务逻辑、API 封装、Jotai store、实体缓存、message-adapter、SSE 解析）在 `packages/core`；React 组件（`packages/ui` 与 `packages/features`）不直接摸环境全局；各 app 入口壳只负责组装、注入 platform 实现、挂载。
- **platform adapter** 是枢纽：`packages/platform` 只导出 `PlatformAPI` 接口与 context，不含实现；组件调用 `usePlatform()`，Web 注入 `window.open`、Electron 注入 IPC、扩展注入 chrome API。
- 依赖方向：apps → features → ui → core → platform，apps 之间互不引用；反向依赖由 dependency-cruiser 在 CI 拦截。

## 状态与数据（功能规格）

- **Jotai** 承载运行时状态与实体缓存（`packages/core/store`）；**TanStack Query** 承载 API 请求与缓存（`packages/core/query.ts`）。
- **Zod** 在 `shared` 手写 SSE 消息、Agent 中间步骤、OpenUI 卡片的 schema，并在 `message-adapter` 里做运行时校验——流式与后端契约口径最容易漂移，运行时校验价值最大。
- 流式链路：UI 事件 → hook → core API → 服务端 SSE/RSC streaming → features/stream 消费并写入实体缓存与 Jotai 状态 → 消息列表渲染。

## 代码质量与工程治理（ADR-0004）

- **oxlint** 负责 lint，`--type-aware --type-check` 提供本地快速反馈；多文件分析（import/no-cycle）覆盖循环依赖检测，内置 vitest 规则。
- **oxfmt** 独占格式化，100% 兼容 Prettier，内置 CSS、JSON、YAML、Markdown 支持以及 import 排序和 Tailwind class 排序，因此不引入 Prettier 或 prettier-plugin-tailwindcss。
- **dependency-cruiser** 专注架构分层约束，声明单向依赖规则并挂进 CI。
- **tsc -b（或已 GA 的 tsgo）** 在 CI 做权威类型判定；本地 lint 快检与 CI 权威检查的职责在流水线里明确区分。
- **lefthook** 用一个 YAML 声明暂存区并行任务，跑 `oxlint --fix` 与 `oxfmt`，替代 husky + lint-staged。
- **changesets** 管理多包版本 bump 与 changelog；**syncpack 或 manypkg** 校验跨包依赖版本一致性并挂 CI。
- **Vitest** 覆盖单测与组件测，**Playwright** 覆盖 E2E（SSR 的 Web 端与流式对话）。
- **codegen** 作为 Turborepo pipeline 的 build 前置节点，`outputs` 指向 `shared/generated`；CI 增加「codegen 后 git diff 为空」的漂移校验，防止 schema 改动未提交生成物。
- 所有检查（lint、fmt、typecheck、depcruise、test）纳入 Turborepo pipeline，按拓扑顺序执行并增量缓存。

## 明确不引入

- **Prettier / prettier-plugin-tailwindcss**：格式与排序由 oxfmt 覆盖。
- **husky**：Git hooks 由 lefthook 覆盖。
- **Nx**：编排与缓存由 Turborepo 覆盖，当前规模不划算。

## 来源

- ADR-0001：采用 pnpm workspace + Turborepo 作为 monorepo 底座
- ADR-0002：SSR 只在 Web target，Electron 与扩展保持纯 CSR
- ADR-0003：用 platform adapter 抽象层吸收三端环境差异
- ADR-0004：代码质量工具链选型（oxlint / oxfmt / dependency-cruiser 等）
- 功能规格：monorepo-toolchain、agentic-stream、share-page
