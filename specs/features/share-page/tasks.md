# 分享页 — 任务

以下任务完成后不删除，作为已交付记录保留。

- [ ] 在 shared 定义已定稿对话的契约 schema（消息、引用来源、工具调用结果）
- [ ] 在 packages/core 实现按 token 拉取定稿对话的只读 API 封装与消息实体类型
- [ ] 审查 packages/features 的消息渲染组件，拆出纯展示部分供 SSR 使用，确认无 window/localStorage 直接访问
- [ ] 在 apps/web 建立 share/[token]/page.tsx 服务端组件，直出对话首屏
- [ ] 用 Next metadata 生成标题、摘要与 Open Graph 卡片
- [ ] 实现 token 服务端校验，失效或越权返回失效页面且不泄露内容
- [ ] 补充 Playwright E2E：验证首屏 HTML 含完整对话、禁用 JS 时主体可读、失效 token 返回失效页
- [ ] 引导「继续对话」跳转到应用主流程
