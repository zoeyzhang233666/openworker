import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { BackgroundTask } from "../api";
import {
  getBackgroundTaskOutput,
  getBackgroundTasks,
  sendBackgroundTaskMessage,
  stopBackgroundTask,
} from "../api";
import { LocaleProvider } from "../i18n";
import { BackgroundTasksSection } from "./BackgroundTasksSection";

vi.mock("../api", () => ({
  getBackgroundTaskOutput: vi.fn(),
  getBackgroundTasks: vi.fn(),
  sendBackgroundTaskMessage: vi.fn(),
  stopBackgroundTask: vi.fn(),
}));

vi.mock("./Markdown", () => ({
  Markdown: ({ text }: { text: string }) => <div>{text}</div>,
}));

const task: BackgroundTask = {
  version: 1,
  id: "task-1",
  kind: "agent",
  status: "running",
  owner_session_id: "session-1",
  description: "调查甲醇上游原料",
  profile_id: "research",
  profile_title: "研究子智能体",
  child_session_id: "child-1",
  parent_task_id: null,
  parent_trace_id: "trace-1",
  model: "test-model",
  created_at: Date.now() / 1000 - 2,
  updated_at: Date.now() / 1000 - 1,
  started_at: Date.now() / 1000 - 2,
  finished_at: null,
  run_count: 1,
  output_size: 80,
  exit_code: null,
  error: null,
  metadata: {},
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("BackgroundTasksSection", () => {
  it("stays hidden when the current session has no background tasks", async () => {
    vi.mocked(getBackgroundTasks).mockResolvedValue([]);

    const { container } = render(
      <LocaleProvider>
        <BackgroundTasksSection sessionId="session-empty" refreshKey={0} />
      </LocaleProvider>,
    );

    await waitFor(() => expect(getBackgroundTasks).toHaveBeenCalled());
    expect(container.querySelector(".background-tasks-section")).toBeNull();
  });

  it("shows subagent activity and lets the user steer and stop it", async () => {
    vi.mocked(getBackgroundTasks).mockResolvedValue([task]);
    vi.mocked(getBackgroundTaskOutput).mockResolvedValue({
      version: 1,
      task_id: task.id,
      chunks: [
        {
          version: 1,
          task_id: task.id,
          seq: 1,
          stream: "event",
          text: "tool_started:web_search",
          created_at: 101,
        },
        {
          version: 1,
          task_id: task.id,
          seq: 2,
          stream: "assistant",
          text: "已找到上游原料分支结论。",
          created_at: 102,
        },
      ],
      next_cursor: 2,
      truncated: false,
    });
    vi.mocked(sendBackgroundTaskMessage).mockResolvedValue({ ...task, run_count: 2 });
    vi.mocked(stopBackgroundTask).mockResolvedValue({
      ...task,
      status: "cancelled",
      finished_at: 103,
    });

    render(
      <LocaleProvider>
        <BackgroundTasksSection sessionId="session-1" refreshKey={0} />
      </LocaleProvider>,
    );

    expect(await screen.findByText("子智能体与后台任务（1）")).toBeTruthy();
    fireEvent.click(screen.getByText("研究子智能体"));

    expect(await screen.findByText("开始使用工具：web_search")).toBeTruthy();
    expect(screen.getByText("已找到上游原料分支结论。")).toBeTruthy();

    fireEvent.change(screen.getByPlaceholderText("向这个子智能体补充要求…"), {
      target: { value: "补充中国煤制甲醇数据" },
    });
    fireEvent.click(screen.getByText("发送要求"));
    await waitFor(() =>
      expect(sendBackgroundTaskMessage).toHaveBeenCalledWith(
        "session-1",
        "task-1",
        "补充中国煤制甲醇数据",
      ),
    );

    fireEvent.click(screen.getByText("停止任务"));
    await waitFor(() =>
      expect(stopBackgroundTask).toHaveBeenCalledWith("session-1", "task-1"),
    );
  });

  it("does not show agent steering controls for a shell task", async () => {
    vi.mocked(getBackgroundTasks).mockResolvedValue([
      {
        ...task,
        id: "shell-1",
        kind: "shell",
        description: "运行数据整理脚本",
        profile_id: null,
        profile_title: "",
        child_session_id: null,
      },
    ]);
    vi.mocked(getBackgroundTaskOutput).mockResolvedValue({
      version: 1,
      task_id: "shell-1",
      chunks: [],
      next_cursor: 0,
      truncated: false,
    });

    render(
      <LocaleProvider>
        <BackgroundTasksSection sessionId="session-1" refreshKey={0} />
      </LocaleProvider>,
    );

    fireEvent.click(await screen.findByText("后台命令"));
    await screen.findByText("暂无任务工作记录。");
    expect(screen.queryByText("发送要求")).toBeNull();
    expect(screen.queryByPlaceholderText("向这个子智能体补充要求…")).toBeNull();
  });
});
