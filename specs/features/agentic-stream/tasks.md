# Agentic 流式渲染 — 任务

以下任务完成后不删除，作为已交付记录保留。

- [ ] 在 shared 用 Zod 定义 SSE 消息、Agent 中间步骤、OpenUI 卡片的 schema
- [ ] 在 packages/core 实现 SSE 解析与恢复流的纯逻辑、message-adapter 与运行时校验
- [ ] 在 packages/core 建立 Jotai 运行时状态与消息实体缓存及选择器
- [ ] 在 packages/features/stream 实现发消息、消费流、增量写入缓存的单向数据链路
- [ ] 在 packages/features/chat 实现消息渲染、工具调用轨迹、检索来源与状态卡片
- [ ] 在 packages/features 实现 generative-ui（OpenUI 卡片）渲染
- [ ] 在 packages/platform 定义中断、复制、打开外链的接口
- [ ] 在 apps/web 用 "use client" 边界挂载流式区，服务端只直出外壳
- [ ] 在 apps/desktop 与 apps/extension 注入各自 platform 实现并复用流式组件
- [ ] 实现中断、重连与异常状态处理，避免半截无反馈界面
- [ ] 补充 Vitest 单测覆盖流式状态机的中断、重连、乱序到达
- [ ] 补充 Playwright E2E 验证三端流式一致性与引用可展开
