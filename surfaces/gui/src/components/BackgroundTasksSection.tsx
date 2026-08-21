import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getBackgroundTaskOutput,
  getBackgroundTasks,
  sendBackgroundTaskMessage,
  stopBackgroundTask,
  type BackgroundTask,
  type BackgroundTaskOutput,
  type BackgroundTaskOutputChunk,
  type BackgroundTaskStatus,
} from "../api";
import { useI18n, type MessageKey } from "../i18n";
import { Icon } from "./Icon";
import { Markdown } from "./Markdown";

interface Props {
  sessionId: string;
  refreshKey: number;
}

const ACTIVE_STATUSES = new Set<BackgroundTaskStatus>(["queued", "running"]);

export function BackgroundTasksSection({ sessionId, refreshKey }: Props) {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<BackgroundTask[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [output, setOutput] = useState<BackgroundTaskOutput | null>(null);
  const [open, setOpen] = useState(true);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState<"stop" | "send" | null>(null);
  const [error, setError] = useState("");

  const selected = useMemo(
    () => tasks.find((task) => task.id === selectedId) ?? null,
    [tasks, selectedId],
  );
  const hasActive = tasks.some((task) => ACTIVE_STATUSES.has(task.status));

  const loadTasks = useCallback(async () => {
    try {
      const next = await getBackgroundTasks(sessionId);
      setTasks(next);
      setSelectedId((current) =>
        current && next.some((task) => task.id === current) ? current : null,
      );
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [sessionId]);

  const loadOutput = useCallback(async () => {
    if (!selectedId) return;
    try {
      setOutput(await getBackgroundTaskOutput(sessionId, selectedId));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [sessionId, selectedId]);

  useEffect(() => {
    setTasks([]);
    setSelectedId(null);
    setOutput(null);
    setMessage("");
    setError("");
    void loadTasks();
  }, [sessionId, loadTasks]);

  useEffect(() => {
    void loadTasks();
    if (selectedId) void loadOutput();
  }, [refreshKey, loadTasks, loadOutput, selectedId]);

  useEffect(() => {
    const delay = hasActive ? 1000 : 5000;
    const timer = window.setInterval(() => {
      void loadTasks();
      if (selectedId) void loadOutput();
    }, delay);
    return () => window.clearInterval(timer);
  }, [hasActive, loadTasks, loadOutput, selectedId]);

  useEffect(() => {
    setOutput(null);
    setMessage("");
    if (selectedId) void loadOutput();
  }, [selectedId, loadOutput]);

  const stop = async () => {
    if (!selected) return;
    setBusy("stop");
    try {
      const next = await stopBackgroundTask(sessionId, selected.id);
      setTasks((current) => current.map((task) => (task.id === next.id ? next : task)));
      await loadOutput();
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const send = async () => {
    if (!selected || selected.kind !== "agent" || !message.trim()) return;
    setBusy("send");
    try {
      const next = await sendBackgroundTaskMessage(sessionId, selected.id, message.trim());
      setTasks((current) => current.map((task) => (task.id === next.id ? next : task)));
      setMessage("");
      await loadOutput();
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  if (!tasks.length) return null;

  return (
    <section className="rail-section background-tasks-section">
      <div className="rail-section-head">
        <button className="rail-section-toggle" onClick={() => setOpen((value) => !value)}>
          <Icon name={open ? "chevronDown" : "chevronRight"} size={14} className="rail-chev" />
          <span>{t("Subagents and background tasks ({count})", { count: tasks.length })}</span>
        </button>
        <button
          className="rail-mini-btn"
          onClick={(event) => {
            event.stopPropagation();
            void loadTasks();
            if (selectedId) void loadOutput();
          }}
          title={t("Refresh tasks")}
        >
          <Icon name="refresh" size={13} />
        </button>
      </div>
      {open && (
        <div className="rail-section-body">
          {selected ? (
            <TaskDetail
              task={selected}
              output={output}
              message={message}
              busy={busy}
              error={error}
              onMessage={setMessage}
              onBack={() => setSelectedId(null)}
              onStop={() => void stop()}
              onSend={() => void send()}
              t={t}
            />
          ) : (
            <div className="background-task-list">
              {tasks.map((task) => (
                <button
                  className="background-task-row"
                  key={task.id}
                  onClick={() => setSelectedId(task.id)}
                >
                  <span className={`background-task-status ${task.status}`} />
                  <span className="background-task-main">
                    <span className="background-task-title">
                      <Icon name={task.kind === "agent" ? "lobster" : "code"} size={14} />
                      {taskTitle(task, t)}
                    </span>
                    <span className="background-task-description">{task.description}</span>
                    <span className="background-task-meta">
                      {statusLabel(task.status, t)} · {formatDuration(task, t)}
                      {task.run_count > 1 ? ` · ${t("Run {count}", { count: task.run_count })}` : ""}
                    </span>
                  </span>
                  <Icon name="chevronRight" size={14} className="rail-chev" />
                </button>
              ))}
              {error && <div className="rail-error">{error}</div>}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function TaskDetail({
  task,
  output,
  message,
  busy,
  error,
  onMessage,
  onBack,
  onStop,
  onSend,
  t,
}: {
  task: BackgroundTask;
  output: BackgroundTaskOutput | null;
  message: string;
  busy: "stop" | "send" | null;
  error: string;
  onMessage: (value: string) => void;
  onBack: () => void;
  onStop: () => void;
  onSend: () => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
}) {
  return (
    <div className="background-task-detail">
      <button className="background-task-back" onClick={onBack}>
        <Icon name="arrowLeft" size={14} />
        {t("Back to task list")}
      </button>
      <div className="background-task-detail-head">
        <div>
          <div className="background-task-detail-title">{taskTitle(task, t)}</div>
          <div className="background-task-meta">
            {statusLabel(task.status, t)} · {formatDuration(task, t)}
          </div>
        </div>
        <span className={`background-task-status ${task.status}`} />
      </div>
      <div className="background-task-description detail">{task.description}</div>
      {task.error && <div className="rail-error">{t("Task failed:")} {task.error}</div>}
      <div className="background-task-output" aria-label={t("Task activity")}>
        {!output ? (
          <div className="rail-muted">{t("Loading task activity...")}</div>
        ) : output.chunks.length ? (
          output.chunks.map((chunk) => <TaskOutputLine key={chunk.seq} chunk={chunk} t={t} />)
        ) : (
          <div className="rail-muted">{t("No task activity yet.")}</div>
        )}
        {output?.truncated && (
          <div className="rail-muted">{t("Only the latest available task output is shown.")}</div>
        )}
      </div>
      <div className="background-task-actions">
        {ACTIVE_STATUSES.has(task.status) && (
          <button className="btn sm danger-btn" onClick={onStop} disabled={busy !== null}>
            <Icon name="stop" size={12} />
            {busy === "stop" ? t("Stopping...") : t("Stop task")}
          </button>
        )}
      </div>
      {task.kind === "agent" && (
        <div className="background-task-followup">
          <textarea
            value={message}
            onChange={(event) => onMessage(event.target.value)}
            placeholder={t("Add instructions for this subagent...")}
            rows={3}
          />
          <button
            className="btn sm primary"
            onClick={onSend}
            disabled={busy !== null || !message.trim()}
          >
            {busy === "send" ? t("Sending...") : t("Send instructions")}
          </button>
        </div>
      )}
      {error && <div className="rail-error">{error}</div>}
    </div>
  );
}

function TaskOutputLine({
  chunk,
  t,
}: {
  chunk: BackgroundTaskOutputChunk;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
}) {
  if (chunk.stream === "assistant") {
    return (
      <div className="background-task-report">
        <div className="background-task-output-label">{t("Subagent result")}</div>
        <Markdown text={chunk.text} renderMermaid={false} renderCharts={false} />
      </div>
    );
  }
  let text = chunk.text.trim();
  const tool = text.match(/^tool_(started|finished):(.+)$/);
  if (tool) {
    text = tool[1] === "started"
      ? t("Started tool: {name}", { name: tool[2] })
      : t("Finished tool: {name}", { name: tool[2] });
  }
  return text ? (
    <div className={`background-task-output-line ${chunk.stream}`}>{text}</div>
  ) : null;
}

function taskTitle(
  task: BackgroundTask,
  t: (key: MessageKey, vars?: Record<string, string | number>) => string,
): string {
  if (task.kind === "shell") return t("Background command");
  if (task.profile_id === "research") return t("Research subagent");
  if (task.profile_id === "explore") return t("Code exploration subagent");
  if (task.profile_id === "worker") return t("Worker subagent");
  return task.profile_title || t("Subagent");
}

function statusLabel(
  status: BackgroundTaskStatus,
  t: (key: MessageKey, vars?: Record<string, string | number>) => string,
): string {
  const labels: Record<BackgroundTaskStatus, MessageKey> = {
    queued: "Queued",
    running: "Running",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Stopped",
    interrupted: "Interrupted",
  };
  return t(labels[status]);
}

function formatDuration(
  task: BackgroundTask,
  t: (key: MessageKey, vars?: Record<string, string | number>) => string,
): string {
  const start = task.started_at ?? task.created_at;
  const end = task.finished_at ?? Date.now() / 1000;
  const seconds = Math.max(0, Math.round(end - start));
  if (seconds < 60) return t("{count}s", { count: seconds });
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return rest ? t("{minutes}m {seconds}s", { minutes, seconds: rest }) : t("{count}m", { count: minutes });
}
