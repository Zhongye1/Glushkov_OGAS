# ADR-0002：SSR 只在 Web target，Electron 与扩展保持纯 CSR

- 日期：2026-08-01
- 状态：Accepted

## 背景

Agentic RAG 应用里，Agent 的推理、检索、工具调用和流式输出本质上都是运行时动态生成的内容，天然属于客户端或边缘实时流，SSR 帮不上忙。但一个应用不止有对话流，外围还有大量「进入页面时数据就已确定」的内容，这些才是 SSR 的用武之地。

与此同时，我们有三个宿主。Electron 从本地 file:// 加载页面，请求期没有服务端，天生做不了 SSR，也不需要——它没有 SEO 和冷启动白屏被搜索引擎抓取的问题。浏览器扩展同理。所以「三端复用同一套 SSR」是伪命题。

## 决策

SSR 能力收敛在唯一一个 Web target 上，采用 Next.js App Router 而非 Pages Router。App Router 的 React Server Components 加 streaming 模型与 agentic RAG 的数据形态最贴合：外壳和历史回放用服务端组件直出，实时对话区标 "use client" 接管流式，「检索结果先到、生成内容后到」可以做在同一条流里，这是 Pages Router 的 getServerSideProps 那套做不到的。

适合 SSR 的内容限定为四类：应用外壳与导航骨架、已完成对话的静态回放与分享页、知识库与文档的浏览检索落地页、静态配置与元信息。可选的进阶是对可预测查询在服务端预跑一次检索，把候选文档作为首屏 SSR 出来——注意这里 SSR 的是检索结果，不是 Agent 的生成内容。

不适合 SSR、必须走客户端流式的内容：LLM 逐 token 的流式回答、Agent 的中间步骤与工具调用轨迹、动态引用锚定、强交互组件。这些走 SSE 或 RSC streaming，而非传统 SSR。

Electron renderer 用 Vite 打包的纯 CSR，扩展同理。它们复用 Web 端除 SSR 入口以外的一切。

## 后果

正面：SSR 只服务真正受益的少数页面，避免为了「看起来完整」而全站 SSR 带来的复杂度；三端渲染策略边界清晰。

负面：同一套 React 组件要同时支持 Next.js SSR 和 Vite CSR，任何 SSR 不友好的写法（首次渲染就摸 window、直接读 localStorage）都会在 SSR 端出错，需要用 useEffect 或 "use client" 隔离，并由 lint 规则兜底。

## 备选与放弃理由

Pages Router：只在团队已有大量老代码、迁移成本高时才作为退路，当前从零起步选 App Router。

全站 SSR：主体是多运行时 CSR 应用，全站 SSR 收益低而约束大，放弃。局部 SSR 页面甚至可以只复用逻辑层的 core，用相对独立的一套轻组件实现，以免为了迁就 SSR 去约束整个组件库的写法。
