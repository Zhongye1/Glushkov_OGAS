# ADR-0004：代码质量与工程治理工具链选型

- 日期：2026-08-01
- 状态：Accepted

## 背景

在 pnpm workspace 加 Turborepo 的底座上，需要一套完整的代码质量和工程治理工具链。团队已经确定 lint 用 oxlint、格式化用 oxfmt、架构分层约束用 dependency-cruiser，需要评估这套组合覆盖了哪些关注点、还缺哪些腿。

## 决策

### 已由核心组合覆盖，不再重复配工具

格式化交给 oxfmt 一把梭，它已到 beta、100% 兼容 Prettier，并内置 CSS、JSON、YAML、Markdown 等多格式支持以及 import 排序和 Tailwind class 排序，Turborepo 自身也在用它，因此不再引入 Prettier 或 prettier-plugin-tailwindcss。

循环依赖检测由 oxlint 的多文件分析覆盖（import/no-cycle），import 排序由 oxfmt 覆盖，dependency-cruiser 专注架构分层约束，三者不冲突。

### 补充的四类缺口

类型检查保留一条权威兜底。oxlint 的 type-aware 目前是 alpha，虽然能用 --type-aware --type-check 在 lint 时顺带类型检查、适合本地快速反馈，但权威的类型正确性判定仍由 CI 里的 tsc -b（或已 GA 的 tsgo）承担，尤其我们有 Spec-Driven 和 Schema 生成，类型是契约正确性的最后防线。

Git hooks 引擎选 lefthook 而非 husky 加 lint-staged。monorepo 多包场景下 lefthook 用一个 YAML 就能声明并行任务、按 glob 过滤暂存文件，和 pnpm workspace 契合更好，用来跑暂存区的 oxlint --fix 和 oxfmt。

版本与发布用 changesets。多包 monorepo 需要独立版本化和联动发版，changesets 是事实标准，管理版本 bump、生成 changelog，Turborepo 官方也推荐搭配。

依赖版本一致性用 syncpack 或 manypkg。多包最容易出的坑是同一依赖在不同包里版本不一致导致重复打包甚至运行时冲突，需要挂进 CI 校验。

测试用 Vitest 加 Playwright。Vitest 做单测和组件测，与 Vite 同源、monorepo 友好，oxlint 也内置了 vitest 规则；Playwright 做 E2E，用于验证 SSR 的 Web 端和流式对话的端到端行为。

### 可选项

环境变量校验用 @t3-oss/env 加 Zod，避免 SSR 与客户端环境变量混用出错；组件开发用 Storybook 让 packages/ui 脱离宿主独立开发；Node 版本用 Volta 或 .nvmrc 加 engines 锁定；提交信息规范用 commitlint，若已用 changesets 可弱化。

## 后果

正面：工具链精炼，oxfmt 顺带解决格式化和 import 排序，避免 Prettier 系冗余；质量保障的四条腿（类型、hooks、版本治理、测试）补齐后矩阵完整。

负面：oxlint type-aware 尚在 alpha，本地与 CI 的类型检查存在双轨（oxlint 快检 + tsc 权威判定），需要在流水线里明确各自职责，避免团队误以为只跑 lint 就够。

## 完整工具矩阵

| 关注点 | 选型 | 来源 |
|---|---|---|
| 包管理 | pnpm workspace | 已定 |
| 任务编排与缓存 | Turborepo | 已定 |
| Lint | oxlint（含 type-aware） | 已定 |
| 格式化与 import/tailwind 排序 | oxfmt | 已定 |
| 架构分层约束 | dependency-cruiser | 已定 |
| 类型检查（权威） | tsc -b / tsgo | 补充 |
| Git hooks | lefthook | 补充 |
| 版本与发布 | changesets | 补充 |
| 依赖版本一致性 | syncpack / manypkg | 补充 |
| 单测与组件测 | Vitest | 补充 |
| E2E | Playwright | 补充 |
| 环境变量校验 | @t3-oss/env + Zod | 可选 |
| 组件开发 | Storybook | 可选 |
| Node 版本锁定 | Volta / .nvmrc | 可选 |
