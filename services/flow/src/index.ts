import { Hono } from "hono";
import { dagSchema } from "@ogas/shared";

// OGAS-Flow：DAG 编排器。消费 Dispatcher 终态事件，next_ready 纯函数推进。
export const app = new Hono();

app.get("/health", (c) => c.json({ ok: true, service: "flow" }));

app.post("/dag/validate", async (c) => {
  const body = await c.req.json();
  const parsed = dagSchema.safeParse(body);
  return c.json({ ok: parsed.success, errors: parsed.success ? [] : parsed.error.issues });
});

export default app;
