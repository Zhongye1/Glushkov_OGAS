# Agentic 流式渲染 — 设计

## 影响的包

| 包 | 涉及内容 |
|---|---|
| packages/core | SSE 解析与恢复流的纯逻辑、message-adapter、Jotai 运行时状态与实体缓存、TanStack Query client |
| packages/features | stream 模块（发消息、恢复流、消费 SSE）、chat 下的消息与工具渲染、检索轨迹与状态卡片、generative-ui |
| packages/ui | prompt-input、editor 等交互组件 |
| packages/platform | 中断、复制、打开来源链接等环境能力的接口 |
| apps/web | 客户端边界（"use client"）挂载流式区，服务端只直出外壳 |
| apps/desktop、apps/extension | 各自注入 platform 实现，复用同一套流式渲染 |
| shared | SSE 消息、Agent 中间步骤、OpenUI 卡片的 Zod schema |

## 关键设计

流式渲染横跨三端，因此几乎全部逻辑与组件都下沉到 packages。SSE 解析、恢复流、消息适配这些纯逻辑放在 packages/core，与渲染环境无关。发消息、消费流、把流增量写入实体缓存这一链路放在 packages/features 的 stream 模块，驱动 packages/features/chat 下的消息渲染、工具调用轨迹和状态卡片。

数据流是单向的：UI 事件触发 hook，hook 调 core 的 API 发起请求，服务端以 SSE 或 RSC streaming 返回，features/stream 消费流并写入 core 的实体缓存与 Jotai 运行时状态，消息列表据此渲染。

在 Web 端，流式区必须在客户端边界（"use client"）内，服务端至多直出对话外壳骨架，不参与流式内容生成——这与 ADR-0002 一致。Electron 与扩展是纯 CSR，直接客户端挂载同一套组件。

环境相关能力（中断当前生成、复制内容、打开引用来源的外链）不在组件里直接调用宿主 API，而是通过 packages/platform 的接口，由各 app 注入实现。这样同一套流式组件三端通用，符合 ADR-0003。

后端往往没有为 SSE 流、Agent 中间步骤和 OpenUI 卡片提供正式契约，这部分用 Zod 在 shared 手写 schema，并在 message-adapter 里做运行时校验——这恰恰是最容易出错的地方，运行时校验价值最大。

## 风险

流式状态机的复杂度集中在 features/stream，中断、重连、乱序到达的处理需要充分测试。SSE 消息 schema 与后端的口径漂移只能靠运行时校验和契约同步来控制，需在 CI 里保证 schema 与后端约定一致。
