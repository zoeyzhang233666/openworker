import type { MessageKey } from "./i18n";

const labels: Record<string, MessageKey> = {
  queued: "Queued", running: "Running", waiting_user: "Waiting for your response",
  waiting_children: "Subagents are still working", budget_paused: "Task budget paused",
  truncated: "Output incomplete", blocked: "Task blocked", completed: "Completed",
  ok: "Completed", failed: "Failed", error: "Failed", cancelled: "Stopped", interrupted: "Interrupted",
};

export function statusLabel(status: string, t: (key: MessageKey, vars?: Record<string, string | number>) => string): string {
  return t(labels[status] ?? "Task blocked");
}
