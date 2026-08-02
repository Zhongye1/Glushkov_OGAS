import { z } from "zod";

// ---- 前端：SSE 与 Agent 步骤 ----
export const agentStepSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  kind: z.enum(["tool_call", "message", "state"]),
  payload: z.record(z.unknown()),
  ts: z.string(),
});

export const sseMessageSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("step"), step: agentStepSchema }),
  z.object({ type: z.literal("token"), text: z.string() }),
  z.object({ type: z.literal("done"), ok: z.boolean() }),
]);

export type SseMessage = z.infer<typeof sseMessageSchema>;

// ---- OGAS：任务状态机 ----
export const taskStatusSchema = z.enum([
  "queued",
  "dispatched",
  "running",
  "completed",
  "failed",
  "cancelled",
]);

export const taskSchema = z.object({
  id: z.string(),
  issue: z.string(),
  agent: z.string(),
  status: taskStatusSchema,
  retryExhausted: z.boolean().optional(),
});

// ---- OGAS：终态事件 ----
export const terminalEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("completed"), taskId: z.string() }),
  z.object({ type: z.literal("retry_exhausted"), taskId: z.string() }),
  z.object({ type: z.literal("cancelled"), taskId: z.string() }),
]);

export type TerminalEvent = z.infer<typeof terminalEventSchema>;

// ---- OGAS：DAG 定义 ----
export const dagNodeSchema = z.discriminatedUnion("type", [
  z.object({
    id: z.string(),
    type: z.literal("AGENT"),
    issue: z.string(),
    agent: z.string(),
    dependsOn: z.array(z.string()).optional(),
  }),
  z.object({
    id: z.string(),
    type: z.literal("GATE"),
    check: z.string(),
    dependsOn: z.array(z.string()).optional(),
  }),
  z.object({
    id: z.string(),
    type: z.literal("JOIN"),
    dependsOn: z.array(z.string()).optional(),
  }),
]);

export const dagSchema = z.object({ dag: z.array(dagNodeSchema) });

export type Dag = z.infer<typeof dagSchema>;

// ---- OGAS：ask 双向通道 ----
export const askMessageSchema = z.object({
  id: z.string(),
  taskId: z.string(),
  prompt: z.string(),
  risk: z.enum(["normal", "high"]),
  status: z.enum(["pending", "approved", "rejected", "timeout"]),
});

export type AskMessage = z.infer<typeof askMessageSchema>;
