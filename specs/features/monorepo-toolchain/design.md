# Monorepo 工具链 — 设计

## 影响的包

工具链是仓库级配置，影响根目录与全部 apps 和 packages，而非单一业务包。

| 位置 | 涉及内容 |
|---|---|
| 仓库根 | pnpm-workspace.yaml、turbo.json、tsconfig.base.json、oxlint 与 oxfmt 配置、dependency-cruiser 配置、lefthook.yml、changesets、syncpack |
| 各 package | 各自的 tsconfig、build 与 test 脚本，供 Turborepo pipeline 编排 |
| shared | codegen 产物（OpenAPI 生成的类型与客户端、Zod schema），作为 build 前置 |

## 关键设计

底座是 pnpm workspace 加 Turborepo，见 ADR-0001。pnpm 的严格 node_modules 杜绝幽灵依赖，为单向依赖约束打底；Turborepo 的 pipeline 把 codegen、lint、fmt、typecheck、depcruise、test、build 编排成有拓扑顺序、可增量缓存的图。

代码质量按 ADR-0004 分工。oxfmt 独占格式化与 import/Tailwind 排序，不配 Prettier。oxlint 做 lint，并借多文件分析覆盖循环依赖检测。dependency-cruiser 专注架构分层约束，声明单向依赖规则：apps 引用任意 packages，features 引用 ui、core、platform 但不反向，core 与 platform 不引用上层。三层禁摸环境全局用 lint 的 no-restricted-globals 加自定义规则实现。

类型检查双轨：oxlint --type-aware --type-check 供本地快速反馈，CI 用 tsc -b 做权威判定，避免团队误以为只跑 lint 就够。

codegen 挂进 pipeline 作为 build 前置。turbo.json 里让 codegen 的 outputs 指向 shared/generated，build 的 dependsOn 包含 codegen 与上游包的 build。CI 加一步「codegen 后检查 git diff 为空」，防止有人改了 schema 却忘记提交生成物导致前后端漂移。

工程治理三件：lefthook 用一个 YAML 声明暂存区并行任务，跑 oxlint --fix 与 oxfmt；changesets 管多包版本与 changelog；syncpack 或 manypkg 校验跨包依赖版本一致。

测试两层：Vitest 做单测与组件测（与 Vite 同源），Playwright 做 E2E（覆盖 SSR 的 Web 端与流式对话）。

## 风险

oxlint type-aware 处于 alpha，本地与 CI 的类型检查双轨需要在文档与 CI 里写清各自职责。codegen 若未纳入缓存正确的 outputs 声明，会破坏增量缓存或导致漂移，需要在 turbo.json 里准确声明输入输出。
