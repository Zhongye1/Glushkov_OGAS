# Monorepo 初始化方案

> 单一入口文档：整合 `specs/` 中初始化本 monorepo 所需的全部信息——文件组织、技术选型、架构方案。按此文档即可从零搭建仓库，各选型的决策理由见对应 ADR。
>
> 本文档覆盖**前端部分**（agentic RAG 三端）。含 OGAS 各组成部分的完整仓库结构见 [monorepo文件结构.md](monorepo文件结构.md)。
>
> 实际搭建过程与踩坑修复见 [monorepo搭建记录.md](monorepo搭建记录.md)。

## 1. 目标概览

本工程是 agentic RAG 应用的前端，同时跑在三个运行时宿主上：

- **apps/web**：唯一带 SSR 的 Web target（Next.js App Router）
- **apps/desktop**：Electron 桌面端（纯 CSR）
- **apps/extension**：浏览器扩展（纯 CSR，MV3）

共享层由 `packages/`（platform / core / ui / features）与 `shared/`（跨端契约）构成，目标是最大化三端业务代码复用，同时保证构建可编排、可增量缓存、质量门槛可强制。

初始化完成的验收标准：`pnpm install` 后，Turborepo pipeline 能按拓扑顺序串起 codegen → lint → fmt → typecheck → depcruise → test → build，并支持增量缓存。

## 2. 技术选型

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

明确不引入：**Prettier / prettier-plugin-tailwindcss**（格式由 oxfmt 覆盖）、**husky**（hooks 由 lefthook 覆盖）、**Nx**（编排由 Turborepo 覆盖）。

## 3. 文件组织

### 3.1 目标目录结构

```
frontend/                         # monorepo 根（pnpm workspace + turbo）
├── package.json                  # 锁定 packageManager
├── pnpm-workspace.yaml
├── turbo.json                    # pipeline：codegen 前置，串起各检查与 build
├── tsconfig.base.json            # 各包 tsconfig 继承并配置 paths
├── oxlint.json / oxfmt 配置
├── dependency-cruiser 配置
├── lefthook.yml                  # 暂存区并行任务
├── syncpack 配置
├── .changeset/
│
├── specs/                        # 规格单一事实源
│   ├── overview.md
│   ├── adr/                      # 架构决策记录，只增不改
│   ├── features/                 # 功能规格：requirements/design/tasks
│   └── templates/
│
├── apps/                         # 运行时入口层 —— 互不依赖
│   ├── web/                      # 唯一带 SSR 的 target（Next.js App Router）
│   │   ├── app/
│   │   │   ├── layout.tsx             # 根布局 = app-shell，SSR 直出外壳
│   │   │   ├── (chat)/c/[id]/page.tsx # 对话页：历史 SSR，实时区 "use client"
│   │   │   ├── share/[token]/page.tsx # 分享页：SSR + 可抓取
│   │   │   └── kb/[docId]/page.tsx    # 知识库公开页：SSR / ISR
│   │   └── src/
│   │       ├── platform-web.ts        # 注入 web 版 platform 实现
│   │       └── providers.tsx
│   ├── desktop/                  # Electron（纯 CSR）
│   │   ├── electron/             # 主进程 + ipc
│   │   ├── preload/bridge.ts
│   │   └── renderer/             # Vite 打包的 CSR
│   │       └── platform-electron.ts  # 注入 electron 版 platform（走 IPC）
│   └── extension/                # 浏览器扩展（纯 CSR，MV3）
│       ├── background/ content/ sidepanel/ popup/
│       └── platform-extension.ts # 注入扩展版 platform（chrome.*）
│
├── packages/                     # 跨运行时共享 —— 越靠下越稳定
│   ├── platform/                 # 枢纽：只有接口，无实现
│   │   └── src/{types.ts, context.tsx, index.ts}
│   ├── core/                     # 逻辑层 —— 100% 复用，零 UI
│   │   └── src/{api/, store/{atoms,entities}, stream/, message-adapter/, query.ts, types/}
│   ├── ui/                       # 通用组件 —— 环境无关
│   │   └── src/{prompt-input/, editor/, chat-layout/, app-sidebar/, primitives/}
│   └── features/                 # 业务模块 —— 环境无关，靠 platform 注入
│       └── src/{stream/, chat/, project/, task-center/, skill/, tools/, generative-ui/, otp-auth/}
│
├── shared/                       # 跨端纯契约
│   └── src/{schema/, generated/, constants/}
│
├── docs/                         # 面向读者的现状文档
└── notes/                        # 研发过程记录
```

### 3.2 各包职责

| 目录              | 职责                            | 关键内容                                                                  |
| ----------------- | ------------------------------- | ------------------------------------------------------------------------- |
| apps/web          | 唯一 SSR target，服务端组件优先 | App Router 路由、metadata/OG 卡片、platform-web 注入                      |
| apps/desktop      | Electron 纯 CSR                 | 主进程 + ipc、preload bridge、Vite renderer、platform-electron 注入       |
| apps/extension    | 扩展纯 CSR（MV3）               | background / content / sidepanel / popup、platform-extension 注入         |
| packages/platform | 环境差异抽象，只有接口无实现    | PlatformAPI 类型、context（usePlatform）                                  |
| packages/core     | 纯逻辑，零 UI，100% 复用        | API 封装、Jotai store、实体缓存、SSE 解析、message-adapter、query.ts      |
| packages/ui       | 环境无关通用组件                | prompt-input、editor、chat-layout、app-sidebar、primitives                |
| packages/features | 环境无关业务模块                | stream、chat、project、task-center、skill、tools、generative-ui、otp-auth |
| shared            | 跨端纯契约                      | schema（Zod）、generated（codegen 产物）、constants                       |
| specs             | 规格单一事实源                  | 已归档 ADR 与功能规格，初始化时同步建立                                   |

## 4. 架构方案

### 4.1 分层与依赖规则

依赖方向固定为：**apps → features → ui → core → platform**，越往下越稳定、越与环境无关；apps 之间横向绝不互相引用。

用 **dependency-cruiser** 在 CI 强制：

- apps 可引用任意 packages
- features 可引用 ui、core、platform，反向不行
- core 与 platform 不引用任何上层
- 谁写了反向依赖，CI 直接红

### 4.2 环境全局禁令

core、ui、features 三层中出现 `window`、`document`、`chrome`、`process` 或 Electron 相关标识一律 lint 报错（`no-restricted-globals` 加自定义规则）。需要环境能力时只能走 `usePlatform()`。这是保证「同一份组件三端都能跑且 SSR 端不炸」的底线；SSR 不友好的写法（首屏读 localStorage、直接摸 window）也由此拦截。

### 4.3 platform adapter

- `packages/platform` 只导出 `PlatformAPI` 接口与 context，不含任何实现
- 组件调用 `usePlatform()`：Web 注入 `window.open` 等实现，Electron 注入 IPC 调用，扩展注入 chrome API
- 各 app 入口壳负责组装、注入 platform 实现、挂载
- 新增宿主只需实现一份 adapter，不动业务代码

### 4.4 渲染策略

- **SSR 只在 Web target**：应用外壳与导航骨架、已完成对话的静态回放与分享页、知识库与文档浏览页、静态配置与元信息四类内容服务端直出
- **客户端流式**：LLM 逐 token 回答、Agent 中间步骤与工具调用轨迹、动态引用锚定、强交互组件，走 SSE 或 RSC streaming；对话页实时区标 "use client"
- Electron 与扩展保持纯 CSR，复用 Web 端除 SSR 入口以外的一切
- 分享页在 `share/[token]` 用服务端组件直出完整对话，metadata 生成 OG 卡片；token 校验在服务端完成

### 4.5 数据流

单向数据流：UI 事件 → hook → core API → 服务端 SSE/RSC streaming → features/stream 消费流并写入 core 实体缓存与 Jotai 运行时状态 → 消息列表渲染。SSE 消息、Agent 中间步骤、OpenUI 卡片的 schema 在 shared 用 Zod 手写，并在 message-adapter 做运行时校验。

### 4.6 工程治理与 pipeline

- **Turborepo pipeline**：codegen 作为 build 前置节点（`outputs` 指向 `shared/generated`），串起 lint、fmt、typecheck、depcruise、test、build，按拓扑顺序执行并增量缓存
- **类型检查双轨**：oxlint type-aware 本地快检，CI 用 tsc -b（或已 GA 的 tsgo）做权威判定
- **Git hooks**：lefthook 在暂存区并行跑 `oxlint --fix` 与 `oxfmt`
- **版本治理**：changesets 管多包版本与 changelog；syncpack / manypkg 在 CI 校验依赖版本一致
- **测试**：Vitest 单测与组件测，Playwright E2E（SSR Web 端与流式对话）
- **漂移校验**：CI 增加「codegen 后 git diff 为空」，防止 schema 改动未提交生成物导致前后端漂移

## 5. 初始化步骤清单

按以下顺序落地（对应 `specs/features/monorepo-toolchain/tasks.md`，完成后勾选保留作为交付记录）：

1. 初始化 `pnpm-workspace.yaml` 与根 `package.json`，锁定 `packageManager`
2. 建立目录骨架：`apps/web`、`apps/desktop`、`apps/extension`、`packages/{platform,core,ui,features}`、`shared`、`specs`（按第 3 节结构）
3. 配置 `turbo.json` pipeline：codegen 作为 build 前置，串起 lint、fmt、typecheck、depcruise、test、build
4. 建立 `tsconfig.base.json`，各包 tsconfig 继承并配置 paths
5. 配置 oxlint（含 typescript 插件与 type-aware），配置 oxfmt（含 import 与 Tailwind 排序）
6. 配置 dependency-cruiser 的单向依赖规则并接入 CI
7. 配置 `no-restricted-globals` 拦截 core/ui/features 三层的环境全局访问
8. CI 增加 `tsc -b` 权威类型检查步骤
9. 配置 `lefthook.yml`，暂存区跑 `oxlint --fix` 与 `oxfmt`
10. 接入 changesets 管理多包版本与 changelog
11. 接入 syncpack 或 manypkg 校验依赖版本一致性并挂 CI
12. 搭建 Vitest 与 Playwright 基础配置
13. CI 增加「codegen 后 git diff 为空」的漂移校验
14. 验收：`pnpm install` 后 `turbo run build` 全绿，三端 app 可启动

## 6. 来源

- ADR-0001：采用 pnpm workspace + Turborepo 作为 monorepo 底座
- ADR-0002：SSR 只在 Web target，Electron 与扩展保持纯 CSR
- ADR-0003：用 platform adapter 抽象层吸收三端环境差异
- ADR-0004：代码质量工具链选型（oxlint / oxfmt / dependency-cruiser 等）
- 目标文件结构参考：specs/architecture-file-structure.md
- 功能规格：monorepo-toolchain、agentic-stream、share-page
