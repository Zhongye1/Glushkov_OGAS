# 分享页 — 设计

## 影响的包

| 包 | 涉及内容 |
|---|---|
| apps/web | Next.js App Router 下的 share/[token] 路由，服务端组件直出首屏，负责元信息与 OG 卡片 |
| packages/features | 对话回放的消息渲染组件（messages 下的 agent-message、markdown、tool-render），环境无关 |
| packages/core | 拉取已定稿对话的 API 封装、消息实体的类型与选择器 |
| shared | 对话数据的契约 schema |

## 关键设计

分享页是 SSR 的典型受益场景，落在唯一的 Web target 上。路由用 App Router 的 share/[token]/page.tsx，作为服务端组件在请求期从后端按 token 拉取已定稿对话，直接把完整对话渲染进首屏 HTML，不经过客户端二次请求。元信息与 Open Graph 卡片在同一服务端组件里通过 Next 的 metadata 机制生成，保证抓取器在不执行 JavaScript 时也能拿到标题与摘要。

对话主体复用 packages/features 里的消息渲染组件。这些组件必须是环境无关的：它们只接收数据、不摸 window、不发起客户端专属请求，因此既能在服务端组件里渲染，也能在应用内的客户端场景复用。凡是分享页用到的渲染组件，若含有交互态或副作用，需拆出纯展示部分供 SSR 使用。

数据获取走 packages/core 的 API 层，只读已落库的定稿数据，不触发任何生成逻辑。token 校验在服务端完成，失效或越权时返回失效页面，不渲染任何对话内容。

## 与流式的边界

分享页只呈现静态定稿内容，与 agentic-stream 严格分离。它不承载实时生成、编辑或再对话；这些交互一旦需要，引导用户跳转进应用主流程，由客户端接管。

## 风险

复用的消息组件如果混入了 SSR 不友好的写法（首屏就读 localStorage 或摸 window），会在服务端渲染时报错。需通过 lint 规则（no-restricted-globals）在 features 层拦截，并在设计评审时确认分享页所用组件的纯展示性。
