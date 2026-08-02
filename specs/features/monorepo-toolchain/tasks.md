# Monorepo 工具链 — 任务

以下任务完成后不删除，作为已交付记录保留。

- [ ] 初始化 pnpm-workspace.yaml 与根 package.json，锁定 packageManager
- [ ] 配置 turbo.json pipeline：codegen 作为 build 前置，串起 lint、fmt、typecheck、depcruise、test、build
- [ ] 建立 tsconfig.base.json，各包 tsconfig 继承并配置 paths
- [ ] 配置 oxlint（含 typescript 插件与 type-aware），配置 oxfmt（含 import 与 Tailwind 排序）
- [ ] 配置 dependency-cruiser 的单向依赖规则并接入 CI
- [ ] 配置 no-restricted-globals 拦截 core/ui/features 三层的环境全局访问
- [ ] CI 增加 tsc -b 权威类型检查步骤
- [ ] 配置 lefthook.yml，暂存区跑 oxlint --fix 与 oxfmt
- [ ] 接入 changesets 管理多包版本与 changelog
- [ ] 接入 syncpack 或 manypkg 校验依赖版本一致性并挂 CI
- [ ] 搭建 Vitest 与 Playwright 基础配置
- [ ] CI 增加「codegen 后 git diff 为空」的漂移校验
