# Monorepo 搭建记录

> 本文档是 `docs/monorepo初始化方案.md`（计划）与 `docs/monorepo文件结构.md`（含 OGAS 结构）的落地实录：从空仓库到全链路验证通过的实际步骤、命令与踩坑修复。按此记录可复现整套搭建。

## 1. 前置条件

| 工具    | 版本        | 说明                     |
| ------- | ----------- | ------------------------ |
| Node.js | v22.22.2    | 根 package.json 锁定 >=22 |
| pnpm    | 11.14.0     | packageManager 锁定      |
| Go      | 1.25.4      | `go.work` 对齐           |
| Python  | 3.14.5      | Arkhiv 预留（uv/pip）    |

仓库初始状态：已有 3 个 commit（spec / readme / 初始化方案），`bulletproof-react/` 被 `.gitignore` 忽略。

## 2. 搭建步骤

### 2.1 目录骨架

按 `docs/monorepo文件结构.md` 建立 `apps/`、`packages/`、`shared/`、`services/`、`infra/`、`.github/`、`.changeset/`：

```
apps/{web,desktop,extension,approval}  packages/{platform,core,ui,features}
shared/src/{schema,generated,constants}  services/{gate,flow,dispatcher,arkhiv}
infra/{compose,k8s,scripts}  .github/workflows  .changeset
```

### 2.2 根级配置

- `package.json`：`packageManager: pnpm@11.14.0`、根脚本代理到 turbo（build/dev/lint/typecheck/test/depcruise/syncpack/fmt）
- `pnpm-workspace.yaml`：`apps/*`、`packages/*`、`shared`、`shared/*`、`services/{gate,flow}`
- `turbo.json`：pipeline 为 `build(dependsOn ^build+codegen) → lint/typecheck/test/depcruise`
- `tsconfig.base.json`：strict、ES2022、moduleResolution Bundler、jsx react-jsx、noEmit
- 质量工具：`oxlint.json`、`.dependency-cruiser.cjs`（单向依赖规则）、`lefthook.yml`、`.changeset/config.json`、`.syncpackrc.json`

### 2.3 共享层与 packages

- `shared`：`@ogas/shared`，`src/schema` 含前端（SSE/Agent 步骤）与 OGAS（task/event/dag/ask）四类 Zod 契约，全仓唯一契约层
- `packages/platform`：`Platform` 接口 + `PlatformProvider/usePlatform`
- `packages/core` / `packages/ui` / `packages/features`：分层骨架，`core/ui/features` 配 `.oxlintrc.json` 的 `no-restricted-globals` 环境禁令
- 每个 TS 包：`tsconfig.json`（typecheck）+ `tsconfig.build.json`（emit dist），exports 指向 dist

### 2.4 apps 四端

- `apps/web`：Next.js App Router（唯一 SSR），`transpilePackages` 指向五个内部包
- `apps/approval`：Vite + React + Tailwind v4（`@tailwindcss/vite`），OGAS 审批页
- `apps/desktop`：Electron 主进程（CJS）+ Vite renderer，preload 桥占位
- `apps/extension`：MV3（manifest + background/content/sidepanel/popup），build = tsc + copy-static

### 2.5 services 与 infra、CI

- `services/gate`、`services/flow`：TS + Hono，纳入 pnpm workspace，flow 带 `/dag/validate`（Zod 校验）
- `services/dispatcher`：Go 占位（`go.mod` + `/health`），fork 同步流程记在 `REBASE.md`
- `services/arkhiv`：Python 占位（`pyproject.toml` + `REBASE.md`）
- `go.work` 收录 dispatcher；`infra/compose/docker-compose.yml`（postgres 等）、`infra/scripts/`
- `.github/workflows/ci.yml`：TS（lint/typecheck/test/build/syncpack/漂移检查）+ Go（build/test/vet）双 job

## 3. 依赖安装与 pnpm 11 适配

安装过程中踩到的 pnpm 11 行为变化，按序记录：

| # | 现象 | 原因 | 处理 |
| - | ---- | ---- | ---- |
| 1 | `ERR_SQLITE_ERROR unable to open database file` | 沙箱只允许写仓库与 /tmp，默认 store 目录不可写 | `--store-dir /tmp/pnpm-store` |
| 2 | `ERR_PNPM_WORKSPACE_PKG_NOT_FOUND`：找不到 `@ogas/shared` | `shared/*` glob 匹配不到 `shared` 根包 | workspace 增加 `- shared` |
| 3 | `ERR_PNPM_IGNORED_BUILDS`（esbuild/lefthook/protobufjs/sharp/electron） | pnpm 11 默认阻止依赖构建脚本 | `pnpm-workspace.yaml` 配 `allowBuilds`（electron 保持 false 跳过二进制） |
| 4 | `The "pnpm" field in package.json is no longer read` | pnpm 11 配置迁移到 `pnpm-workspace.yaml` | 删除 package.json 的 pnpm 字段 |
| 5 | `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY` | 配置变化触发 modules 重建确认，无 TTY 无法确认 | `confirmModulesPurge: false` |
| 6 | `Cannot install with frozen-lockfile` | CI=true 默认 frozen-lockfile | 首次用 `pnpm install --no-frozen-lockfile` 更新 lockfile |

工具链激活：`pnpm rebuild esbuild lefthook protobufjs sharp` 后 lefthook 2.1.10、turbo 2.10.8 可用；`pnpm exec lefthook install` 安装 pre-commit hook。

## 4. 构建验证与问题修复

首轮 `turbo run build` 后逐项修复，记录如下：

| # | 报错 | 原因 | 修复 |
| - | ---- | ---- | ---- |
| 1 | `error TS5083: Cannot read file .../TESTRANGE02/tsconfig.base.json` | `shared` 的 tsconfig `extends` 多写一级 `../` | `shared` 用 `../tsconfig.base.json`；`apps/*`、`packages/*` 保持 `../../tsconfig.base.json`（两层深） |
| 2 | `Could not find a declaration file for module 'react'` | platform 缺 `@types/react` | 补 `@types/react`，react 统一 `^19.0.0`（原 packages 用 18 与 apps 不一致） |
| 3 | zod `Cannot find name 'Map'/'Set'` | 同上：tsconfig 失效导致 lib/skipLibCheck 未生效 | 修复 extends 后消失 |
| 4 | `Cannot find type definition file for 'node'` | gate/flow tsconfig 声明 `types: ["node"]` 但未装 @types/node | `pnpm add -D @types/node` |
| 5 | `Expected '>' but found 'type'`（oxlint） | `packages/ui/src/index.ts` 扩展名 `.ts` 内含 JSX | 组件拆为 `Button.tsx`，index 重新导出 |
| 6 | `Type 'Promise<Window | null>' is not assignable to 'Promise<void>'` | desktop `openUrl` 实现返回类型不匹配 | 改为 `window.open(...)` 后不 return |
| 7 | syncpack：`typescript ^5.6.0 → ^5.9.3` 不一致、`dependencyTypes/lintVersions` 弃用 | 版本漂移 + syncpack 15 配置迁移 | 统一 `typescript ^5.9.3`；`.syncpackrc.json` 只留 `sortFirst` |
| 8 | depcruise：`Can't open a config file at the default location` | 包级运行时找不到根配置 | 各包 depcruise script 显式 `--config ../../.dependency-cruiser.cjs` |
| 9 | sharp `Attempting to build from source ... Failed` | 平台预编译二进制缺失 | 不阻断构建，Next 图片优化后续处理 |

另有一处工程修正：`apps/desktop/renderer/src/platform-electron.ts` 原从 `@ogas/shared` 引 `Platform` 类型，改从 `@ogas/platform` 引入（shared 是契约层，不承载平台类型）。

## 5. 最终验证结果

| 检查项 | 命令 | 结果 |
| ------ | ---- | ---- |
| Go 构建/静态检查 | `go work sync && go build ./... && go vet ./...` | ✅ |
| 构建 | `CI=true pnpm build` | ✅ 11/11（含 Next.js 优化构建） |
| 类型检查 | `CI=true pnpm typecheck` | ✅ 11/11 |
| Lint | `CI=true pnpm lint` | ✅ 11/11，0 错误 |
| 测试 | `CI=true pnpm test` | ✅ 16/16 |
| 架构约束 | `CI=true pnpm depcruise` | ✅ 11/11，0 违规 |
| 依赖一致性 | `CI=true pnpm syncpack` | ✅ No issues |
| 环境全局禁令 | 探针文件验证 `no-restricted-globals` | ✅ 拦截 `window` |

## 6. 遗留事项

- **sharp**：无预编译二进制时从源码构建失败，Next 图片优化在需要时再处理
- **Playwright 浏览器**：安装时以 `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` 跳过，跑 E2E 前需 `pnpm exec playwright install`
- **Electron 二进制**：`ELECTRON_SKIP_BINARY_DOWNLOAD=1` 跳过，运行 desktop 前需补装
- **fork 代码**：dispatcher（←Multica）、arkhiv（←EagleRAG）当前为占位，待法务确认后复制上游并写 REBASE 基线
- **执行机形态 / 事件总线时机 / 审批页托管**：见 `docs/monorepo文件结构.md` 第 6 节

## 7. 关联文档

- `docs/monorepo初始化方案.md`：前端部分的初始化计划（验收标准）
- `docs/monorepo文件结构.md`：含 OGAS 的完整目录结构与边界
- `docs/monorepo技术选型.md`：前端技术选型与 ADR 来源
- `docs/ogas技术选型.md`：OGAS 五组件选型
