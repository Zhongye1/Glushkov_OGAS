import { Button } from "@ogas/ui";
import { askMessageSchema } from "@ogas/shared";

export function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100">
      <div className="rounded-lg bg-white p-8 shadow">
        <h1 className="mb-4 text-lg font-semibold">高危操作审批</h1>
        <p className="mb-4 text-sm text-slate-600">
          ask 消息 schema 校验：{askMessageSchema.description ?? "pending"}
        </p>
        <Button label="批准" onClick={() => alert("批准确认")} />
      </div>
    </main>
  );
}
