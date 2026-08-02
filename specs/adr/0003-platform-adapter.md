# ADR-0003：用 platform adapter 抽象层吸收三端环境差异

- 日期：2026-08-01
- 状态：Accepted

## 背景

Web、Electron、扩展三端复用业务代码时，最大的障碍是环境能力不一致：打开外链在 Web 是 window.open、在 Electron 是 IPC 转主进程、在扩展是 chrome.tabs.create；存储、文件访问、窗口控制同理。如果组件直接调用这些环境全局，就被绑死在某个宿主上，无法复用，而且直接摸 window 还会让 SSR 端出错。

## 决策

复用按程度切成三层。第一层是纯逻辑，包括业务逻辑、API 请求封装、Jotai store、实体缓存、类型、message-adapter、SSE 解析，它们与渲染环境彻底无关，抽到 packages/core，三端共用一份。第二层是 React 组件（packages/ui 与 packages/features），组件不许直接摸 window、Node、Electron IPC 或 chrome，所有环境能力通过 platform adapter 注入。第三层是各 app 的入口壳，各写各的，只负责组装、注入 platform 实现、挂载。

platform adapter 是整套方案的枢纽，位于依赖链底层。packages/platform 只导出接口和 context，不含任何实现。每个 app 在自己的入口处注入对应实现：组件调用 usePlatform().openExternal(url)，Web 注入的实现是 window.open，Electron 注入的是 IPC 调用，扩展注入的是 chrome API。这样下层组件依赖的是抽象而非具体宿主，符合单向依赖原则。

## 后果

正面：同一套组件三端都能挂；SSR 端因为组件不直接摸环境全局而不会崩；新增一个宿主只需实现一份 adapter，不动业务代码。

负面：所有环境能力都要先在 PlatformAPI 接口里定义再各端实现，前期有一次性的接口设计成本；组件里想图快直接用 window 会被 lint 拦截，需要团队习惯养成。

## 约束落地

在 core、ui、features 三层里出现 window、document、chrome、process 或 Electron 相关标识一律 lint 报错（no-restricted-globals 加自定义规则），需要环境能力时只能走 usePlatform()。这条是保证「同一份组件三端都能跑且 SSR 端不炸」的底线。
