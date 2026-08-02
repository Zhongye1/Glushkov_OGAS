import { Hono } from "hono";

// OGAS-Gate：飞书事件回调 → Dispatcher facade；状态事件 → 群消息
export const app = new Hono();

app.get("/health", (c) => c.json({ ok: true, service: "gate" }));

// 飞书事件订阅挂载点（@larksuiteoapi/node-sdk 事件回调）
app.post("/feishu/events", (c) => c.json({ ok: true }));

export default app;
