# Monorepo 工具链 — 需求

## 背景与目标

在 pnpm workspace 加 Turborepo 的底座上，需要落地一套完整的代码质量与工程治理工具链，既要精炼不冗余，又要覆盖类型、格式、架构约束、版本治理和测试等所有关键关注点。详细的选型理由见 ADR-0001 与 ADR-0004，本规格描述落地的目标与验收。

## 验收标准

lint 用 oxlint 一遍跑过全仓，格式化用 oxfmt 统一处理 JS、TS、CSS、JSON、YAML、Markdown 并完成 import 与 Tailwind class 排序，二者不与 Prettier 系工具重复。

架构分层约束由 dependency-cruiser 强制：apps 可引用任意 packages，packages/features 可引用 ui、core、platform，但反向依赖被拦截，core 与 platform 不得引用任何上层。core、ui、features 三层出现 window、document、chrome、process 或 Electron 标识被 lint 报错。

类型正确性由 CI 里的 tsc -b 权威判定，oxlint 的 type-aware 作为本地快速反馈，二者职责在流水线里明确区分。

Git 提交前由 lefthook 触发暂存区的 oxlint --fix 与 oxfmt。多包版本由 changesets 管理并生成 changelog，依赖版本一致性由 syncpack 或 manypkg 在 CI 校验。

Vitest 覆盖单测与组件测，Playwright 覆盖 E2E。

所有检查（lint、fmt、typecheck、depcruise、test）纳入 Turborepo pipeline，按拓扑顺序执行并增量缓存，codegen 作为 build 的前置节点。

## 非目标

不引入 Prettier、husky、Nx。可选项（@t3-oss/env、Storybook、Volta、commitlint）按团队诉求后续评估，不在本次必做范围。
