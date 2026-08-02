# ADR-0001：采用 pnpm workspace + Turborepo 作为 monorepo 底座

- 日期：2026-08-01
- 状态：Accepted

## 背景

前端工程需要同时承载三个运行时宿主（Web、Electron、浏览器扩展）以及一组共享的业务包。这些包之间存在明确的依赖顺序，并且引入了 Schema 生成、类型生成这类需要在构建前执行的代码生成步骤。我们需要一个既能管理包依赖、又能按拓扑顺序编排任务并做增量缓存的底座。规模上是三个 app 加四到五个 package，属于中等规模 monorepo，不需要超大仓级别的治理能力。

## 决策

包管理器选 pnpm workspace。它的硬链接加严格 node_modules 结构能杜绝幽灵依赖，这对我们后面要强制的单向依赖架构是刚需——npm 和 yarn 的扁平化会让底层包意外引用到本不该依赖的东西，而 pnpm 默认禁止这种跨界。

任务编排选 Turborepo。我们的核心诉求是「codegen 到 core 到 ui 到 features 到 apps 按序构建，并做增量缓存」，Turborepo 的 pipeline 和 dependsOn 正好覆盖，配置心智极简。代码生成也被纳入依赖图，成为一个可缓存、可追踪、不会被漏跑的流水线节点，这比在 package.json 里手写 prebuild 脚本可靠得多。

## 后果

正面：依赖清晰、构建可缓存、幽灵依赖被杜绝、codegen 纳入流水线治理。

负面：Turborepo 不提供代码生成器和内置的模块边界插件，这两块需要额外手段补齐（边界约束交给 ADR-0003 相关的 dependency-cruiser）。

## 备选与放弃理由

Nx 提供更强的依赖图分析、内置 generators 和 enforce-module-boundaries 插件，但为此要吞下整套 Nx 的概念复杂度，对当前规模不划算。保留将来的迁移空间：当团队需要一键生成 feature 骨架或更强的边界治理时，再评估迁移到 Nx。

yarn berry 功能足够但配置心智更重，npm workspace 编排能力偏弱，均放弃。
