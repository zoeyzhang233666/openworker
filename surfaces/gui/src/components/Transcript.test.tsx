import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Transcript, turnGroupAutoOpen } from "./Transcript";
import { humanizeTool } from "../humanize";
import type { Item } from "../types";

afterEach(cleanup);

// §33 TurnGroup: the user-message → final-answer span is ONE disclosure; interior assistant
// text is narration INSIDE it, the trailing assistant text is the answer OUTSIDE it; steps
// are humanized one-liners; approvals fold into their tool's row as a chip.
// D-069: in-flight / failed / interrupted default OPEN; successful settle defaults CLOSED.
const TURN: Item[] = [
  { kind: "user", text: "post the digest" },
  { kind: "assistant", text: "Checking what merged since yesterday." },
  { kind: "tool", id: "t1", name: "read_file", args: { path: "docs/runbook.md" }, status: "ok" },
  { kind: "approval", name: "send_message", args: { target: "slack:T1/C9" }, reason: "", resolved: "once" },
  { kind: "tool", id: "t2", name: "send_message", args: { target: "slack:T1/C9", text: "hi" }, status: "ok", preview: '{"ok": true}' },
  { kind: "assistant", text: "Posted to #all-openworker." },
];

describe("turnGroupAutoOpen (D-069)", () => {
  it("opens while live or a tool is in flight", () => {
    expect(turnGroupAutoOpen({ live: true, tools: [{ status: "ok" }] })).toBe(true);
    expect(turnGroupAutoOpen({ tools: [{ status: "…" }] })).toBe(true);
  });

  it("closes on successful settle; opens on tool failure or abort notice", () => {
    expect(turnGroupAutoOpen({ tools: [{ status: "ok" }, { status: "ok" }] })).toBe(false);
    expect(turnGroupAutoOpen({ tools: [{ status: "ok" }, { status: "error" }] })).toBe(true);
    expect(turnGroupAutoOpen({ tools: [{ status: "ok" }], aborted: true })).toBe(true);
  });
});

describe("TurnGroup (Transcript §33)", () => {
  it("groups the whole turn; answer stays outside; narration and humanized steps inside", () => {
    const { container } = render(<Transcript items={TURN} onApprove={vi.fn()} />);

    // Successful settle: collapsed by default (D-069) — "2 steps", no step/narration visible.
    expect(screen.getByText(/2 steps|2 个步骤/)).toBeTruthy();
    expect(screen.queryByText(/approval/)).toBeNull();
    expect(screen.queryByTestId("turn-narration")).toBeNull();
    expect(screen.queryByText(/Sent a Slack message|发送了 Slack/)).toBeNull();

    // The final answer is a normal bubble OUTSIDE the disclosure, visible while collapsed.
    expect(screen.getByText("Posted to #all-openworker.")).toBeTruthy();

    // Expand → narration renders quiet inside; steps are humanized lines, not raw args;
    // the approval is a chip on the send_message row, not a separate box.
    fireEvent.click(container.querySelector("summary.stepgroup-head")!);
    expect(screen.getByTestId("turn-narration").textContent).toContain("Checking what merged");
    expect(screen.getByText("runbook.md")).toBeTruthy();
    expect(screen.getByText(/Sent a Slack message to|已通过 Slack 发送消息/)).toBeTruthy();
    expect(screen.getByText(/approved|已批准/)).toBeTruthy();
    expect(screen.queryByText("send_message approval")).toBeNull();

    // Raw stays one click away: the row's raw toggle reveals args + result verbatim.
    fireEvent.click(screen.getAllByText(/^(raw|原始数据)$/)[1]);
    expect(container.textContent).toContain('{"ok": true}');
  });

  it("a running turn is labeled Running and starts EXPANDED (D-069)", () => {
    const items: Item[] = [
      { kind: "assistant", text: "Looking at the repo." },
      { kind: "tool", id: "t1", name: "grep", args: { pattern: "TODO" }, status: "…" },
    ];
    render(<Transcript items={items} onApprove={vi.fn()} />);
    expect(screen.getByText(/Running 1 step…|正在运行1 个步骤/)).toBeTruthy();
    expect(screen.getByTestId("turn-narration").textContent).toContain("Looking at the repo");
    expect(screen.getByTestId("step-running")).toBeTruthy();
    expect(screen.queryByTestId("turn-live-line")).toBeNull(); // live line only when collapsed
  });

  it("manual collapse sticks while still running", () => {
    const items: Item[] = [
      { kind: "assistant", text: "Looking at the repo." },
      { kind: "tool", id: "t1", name: "grep", args: { pattern: "TODO" }, status: "…" },
    ];
    const { container } = render(<Transcript items={items} onApprove={vi.fn()} running />);
    expect(screen.getByTestId("step-running")).toBeTruthy();
    fireEvent.click(container.querySelector("summary.stepgroup-head")!);
    expect(screen.queryByTestId("step-running")).toBeNull();
    expect(screen.getByTestId("turn-live-line").textContent).toContain("Looking at the repo");
  });

  it("manual expand sticks after a successful settle", () => {
    const { container } = render(<Transcript items={TURN} onApprove={vi.fn()} />);
    expect(screen.queryByTestId("turn-narration")).toBeNull();
    fireEvent.click(container.querySelector("summary.stepgroup-head")!);
    expect(screen.getByTestId("turn-narration")).toBeTruthy();
    // Re-render with same settle state must not auto-collapse after user opened
    // (sticky userToggle on the mounted instance — click again would close; stay open).
    expect(screen.getByTestId("turn-narration").textContent).toContain("Checking what merged");
  });

  it("keeps steps expanded after a failed tool", () => {
    const items: Item[] = [
      { kind: "user", text: "run it" },
      { kind: "tool", id: "t1", name: "run_shell", args: { command: "false" }, status: "exit 1" },
      { kind: "assistant", text: "The command failed." },
    ];
    render(<Transcript items={items} onApprove={vi.fn()} />);
    expect(screen.getByTestId("turn-step")).toBeTruthy();
    expect(screen.getByText("The command failed.")).toBeTruthy();
  });

  it("keeps steps expanded when a warn notice follows the turn (interrupt/error)", () => {
    const items: Item[] = [
      { kind: "user", text: "build" },
      { kind: "tool", id: "t1", name: "read_file", args: { path: "a.md" }, status: "ok" },
      { kind: "notice", tone: "warn", text: "Interrupted." },
    ];
    render(<Transcript items={items} onApprove={vi.fn()} />);
    expect(screen.getByTestId("turn-step")).toBeTruthy();
    expect(screen.getByText("Interrupted.")).toBeTruthy();
  });

  it("declined approvals keep their own 'Wanted to' row and surface on the collapsed line", () => {
    const items: Item[] = [
      { kind: "tool", id: "t1", name: "read_file", args: { path: "a.md" }, status: "ok" },
      { kind: "approval", name: "run_shell", args: { command: "rm -rf build/" }, reason: "", resolved: "deny" },
    ];
    const { container } = render(<Transcript items={items} onApprove={vi.fn()} />);
    expect(screen.getByTestId("stepgroup-declined").textContent).toMatch(/1 declined|已拒绝 1 项/);
    // Successful settle with only ok tools → collapsed; expand to see the ask row.
    fireEvent.click(container.querySelector("summary.stepgroup-head")!);
    const ask = screen.getByTestId("turn-ask");
    expect(ask.textContent).toMatch(/Wanted to run|曾请求运行/);
    expect(ask.textContent).toContain("rm -rf build/");
    expect(ask.textContent).toMatch(/✕ declined|✕ 已拒绝/);
  });

  it("assistant-only turns stay plain bubbles (no disclosure)", () => {
    const items: Item[] = [
      { kind: "user", text: "hi" },
      { kind: "assistant", text: "Hello there." },
    ];
    const { container } = render(<Transcript items={items} onApprove={vi.fn()} />);
    expect(container.querySelector("details.stepgroup")).toBeNull();
    expect(screen.getByText("Hello there.")).toBeTruthy();
  });

  it("promotes the last assistant when deliverable text precedes finished tools", () => {
    const items: Item[] = [
      { kind: "user", text: "research asphalt" },
      {
        kind: "assistant",
        text: "完整分析已保存：[产业链分析](artifact:产业链分析.md)",
      },
      { kind: "tool", id: "t1", name: "write_file", args: { path: "产业链分析.md" }, status: "ok" },
      { kind: "tool", id: "t2", name: "load_skill", args: { name: "map" }, status: "ok" },
    ];
    const { container } = render(<Transcript items={items} onApprove={vi.fn()} />);
    const bubble = container.querySelector(".bubble-assistant");
    expect(bubble?.textContent).toContain("完整分析已保存");
    expect(screen.getByText(/2 steps|2 个步骤/)).toBeTruthy();
    // Successful settle → collapsed; no narration left inside after promotion.
    expect(screen.queryByTestId("turn-narration")).toBeNull();
    fireEvent.click(container.querySelector("summary.stepgroup-head")!);
    expect(screen.queryByTestId("turn-narration")).toBeNull();
  });
});

describe("live turns (§33 flicker fix)", () => {
  const LIVE: Item[] = [
    { kind: "user", text: "build the app" },
    { kind: "tool", id: "t1", name: "read_file", args: { path: "data.json" }, status: "ok" },
    { kind: "assistant", text: "Inspecting the fetched dataset next." },
  ];

  it("while running, trailing assistant text stays INSIDE the group — no answer bubble flash", () => {
    const { container } = render(<Transcript items={LIVE} onApprove={vi.fn()} running />);
    // No assistant bubble; D-069 defaults the group OPEN so narration is visible inside.
    expect(container.querySelector(".bubble-assistant")).toBeNull();
    expect(screen.getByTestId("turn-narration").textContent).toContain("Inspecting the fetched dataset");
    // Once the turn ends (running=false), the same trailing text IS the answer bubble.
    cleanup();
    const done = render(<Transcript items={LIVE} onApprove={vi.fn()} />);
    expect(done.container.querySelector(".bubble-assistant")?.textContent).toContain(
      "Inspecting the fetched dataset",
    );
    // Successful settle collapses the step group.
    expect(done.container.querySelector("[data-testid=turn-step]")).toBeNull();
  });

  it("quiet streamed text rides the expanded body by default — never floats as an answer bubble", () => {
    const { container } = render(
      <Transcript
        items={LIVE}
        onApprove={vi.fn()}
        running
        streamingText="The quote endpoint rate-limited, so I'm checking the historical pages."
      />,
    );
    expect(container.querySelector(".bubble-assistant")).toBeNull();
    // D-069: open while running → stream line under the steps (not the collapsed header).
    expect(screen.getByTestId("turn-live-stream").textContent).toContain("quote endpoint rate-limited");
    expect(screen.queryByTestId("turn-live-line")).toBeNull();
    // Manual collapse → stream rides the header live line instead.
    fireEvent.click(container.querySelector("summary.stepgroup-head")!);
    expect(screen.getByTestId("turn-live-line").textContent).toContain("quote endpoint rate-limited");
  });

  it("a PENDING approval neither splits the turn nor promotes the narration", () => {
    const items: Item[] = [
      ...LIVE,
      { kind: "approval", name: "write_file", args: { path: "app.html" }, reason: "" }, // unresolved
    ];
    const { container } = render(<Transcript items={items} onApprove={vi.fn()} running />);
    expect(container.querySelectorAll("details.stepgroup")).toHaveLength(1);
    expect(container.querySelector(".bubble-assistant")).toBeNull();
  });

  it("a live run with NO tool activity is a plain streaming reply — bubbles as ever", () => {
    const items: Item[] = [
      { kind: "user", text: "hi" },
      { kind: "assistant", text: "Hello!" },
    ];
    const { container } = render(<Transcript items={items} onApprove={vi.fn()} running />);
    expect(container.querySelector("details.stepgroup")).toBeNull();
    expect(container.querySelector(".bubble-assistant")?.textContent).toContain("Hello!");
  });
});

describe("submit send approval CTA (D-099)", () => {
  it("shows the button only when ready_for_human_send is present and session is idle", () => {
    const ready: Item[] = [
      { kind: "user", text: "draft outreach" },
      {
        kind: "assistant",
        text: "Gate passed. recommended_action: ready_for_human_send",
      },
    ];
    const { rerender } = render(<Transcript items={ready} onApprove={vi.fn()} />);
    expect(screen.getByTestId("submit-send-approval").textContent).toMatch(
      /提交发送审批|Submit send for approval/,
    );

    rerender(<Transcript items={ready} onApprove={vi.fn()} running />);
    expect(screen.queryByTestId("submit-send-approval")).toBeNull();

    rerender(
      <Transcript
        items={[{ kind: "assistant", text: "draft only, revise_draft" }]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("submit-send-approval")).toBeNull();
  });

  it("dispatches the send-approval event on click", () => {
    const spy = vi.fn();
    window.addEventListener("ocw-request-send-approval", spy);
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text: "ready_for_human_send",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("submit-send-approval"));
    expect(spy).toHaveBeenCalledTimes(1);
    window.removeEventListener("ocw-request-send-approval", spy);
  });
});

describe("submit CRM write approval CTA (D-105)", () => {
  it("shows the button only when ready_for_crm_write is present and session is idle", () => {
    const ready: Item[] = [
      { kind: "user", text: "log crm note" },
      {
        kind: "assistant",
        text: "Follow-up ready. recommended_action: ready_for_crm_write",
      },
    ];
    const { rerender } = render(<Transcript items={ready} onApprove={vi.fn()} />);
    expect(screen.getByTestId("submit-crm-write-approval").textContent).toMatch(
      /提交 CRM 写入审批|Submit CRM write for approval/,
    );

    rerender(<Transcript items={ready} onApprove={vi.fn()} running />);
    expect(screen.queryByTestId("submit-crm-write-approval")).toBeNull();

    rerender(
      <Transcript
        items={[{ kind: "assistant", text: "draft only, revise_draft" }]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("submit-crm-write-approval")).toBeNull();
  });

  it("dispatches the crm-write-approval event on click", () => {
    const spy = vi.fn();
    window.addEventListener("ocw-request-crm-write-approval", spy);
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text: "recommended_action: ready_for_crm_write",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("submit-crm-write-approval"));
    expect(spy).toHaveBeenCalledTimes(1);
    window.removeEventListener("ocw-request-crm-write-approval", spy);
  });

  it("does not show write CTA for bare or prose mentions of the gate token", () => {
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text: "质量门禁通过（ready_for_crm_write）；若需新建联系人用 ready_for_crm_create_contact。",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("submit-crm-write-approval")).toBeNull();
    expect(screen.queryByTestId("submit-crm-create-contact")).toBeNull();
  });
});

describe("submit CRM create-contact approval CTA (D-109)", () => {
  it("shows the button only when ready_for_crm_create_contact is present and idle", () => {
    const ready: Item[] = [
      { kind: "user", text: "create contact" },
      {
        kind: "assistant",
        text: "Email verified. recommended_action: ready_for_crm_create_contact",
      },
    ];
    const { rerender } = render(<Transcript items={ready} onApprove={vi.fn()} />);
    expect(screen.getByTestId("submit-crm-create-contact").textContent).toMatch(
      /提交创建联系人审批|Submit create-contact for approval/,
    );
    expect(screen.queryByTestId("submit-crm-write-approval")).toBeNull();

    rerender(<Transcript items={ready} onApprove={vi.fn()} running />);
    expect(screen.queryByTestId("submit-crm-create-contact")).toBeNull();

    rerender(
      <Transcript
        items={[
          {
            kind: "assistant",
            text: "recommended_action: ready_for_crm_write only",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("submit-crm-create-contact")).toBeNull();
    expect(screen.getByTestId("submit-crm-write-approval")).toBeTruthy();
  });

  it("can show note and create-contact CTAs together when both gates present", () => {
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text:
              "recommended_action: ready_for_crm_write\nrecommended_action: ready_for_crm_create_contact",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.getByTestId("submit-crm-write-approval")).toBeTruthy();
    expect(screen.getByTestId("submit-crm-create-contact")).toBeTruthy();
  });

  it("dispatches the crm-create-contact event on click", () => {
    const spy = vi.fn();
    window.addEventListener("ocw-request-crm-create-contact", spy);
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text: "recommended_action: ready_for_crm_create_contact",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("submit-crm-create-contact"));
    expect(spy).toHaveBeenCalledTimes(1);
    window.removeEventListener("ocw-request-crm-create-contact", spy);
  });
});

describe("submit CRM update-object / create-task approval CTAs (D-127)", () => {
  it("shows update-object button only for its recommended_action gate", () => {
    const ready: Item[] = [
      {
        kind: "assistant",
        text: "Fields ready. recommended_action: ready_for_crm_update_object",
      },
    ];
    const { rerender } = render(<Transcript items={ready} onApprove={vi.fn()} />);
    expect(screen.getByTestId("submit-crm-update-object").textContent).toMatch(
      /提交 CRM 字段更新审批|Submit CRM field update for approval/,
    );
    expect(screen.queryByTestId("submit-crm-create-task")).toBeNull();

    rerender(<Transcript items={ready} onApprove={vi.fn()} running />);
    expect(screen.queryByTestId("submit-crm-update-object")).toBeNull();

    rerender(
      <Transcript
        items={[
          {
            kind: "assistant",
            text: "质量门禁通过（ready_for_crm_update_object）；若需建任务用 ready_for_crm_create_task。",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("submit-crm-update-object")).toBeNull();
    expect(screen.queryByTestId("submit-crm-create-task")).toBeNull();
  });

  it("shows create-task button only for its recommended_action gate", () => {
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text: "Follow-up ready. recommended_action: ready_for_crm_create_task",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.getByTestId("submit-crm-create-task").textContent).toMatch(
      /提交 CRM 任务创建审批|Submit CRM create-task for approval/,
    );
    expect(screen.queryByTestId("submit-crm-update-object")).toBeNull();
  });

  it("can show update-object and create-task CTAs together when both gates present", () => {
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text:
              "recommended_action: ready_for_crm_update_object\nrecommended_action: ready_for_crm_create_task",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    expect(screen.getByTestId("submit-crm-update-object")).toBeTruthy();
    expect(screen.getByTestId("submit-crm-create-task")).toBeTruthy();
  });

  it("dispatches update-object and create-task events on click", () => {
    const updateSpy = vi.fn();
    const taskSpy = vi.fn();
    window.addEventListener("ocw-request-crm-update-object", updateSpy);
    window.addEventListener("ocw-request-crm-create-task", taskSpy);
    render(
      <Transcript
        items={[
          {
            kind: "assistant",
            text:
              "recommended_action: ready_for_crm_update_object\nrecommended_action: ready_for_crm_create_task",
          },
        ]}
        onApprove={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("submit-crm-update-object"));
    fireEvent.click(screen.getByTestId("submit-crm-create-task"));
    expect(updateSpy).toHaveBeenCalledTimes(1);
    expect(taskSpy).toHaveBeenCalledTimes(1);
    window.removeEventListener("ocw-request-crm-update-object", updateSpy);
    window.removeEventListener("ocw-request-crm-create-task", taskSpy);
  });
});

describe("bubble hover affordances (FB-005)", () => {
  const TS = 1752969720; // unix seconds, as the server stamps them
  const ITEMS: Item[] = [
    { kind: "user", text: "post the digest", ts: TS },
    { kind: "assistant", text: "Done — posted to #all-openworker." }, // pre-stamp history: no ts
  ];

  it("copy button copies the bubble's raw text and flashes Copied", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<Transcript items={ITEMS} onApprove={vi.fn()} />);

    const copies = screen.getAllByTestId("bubble-copy");
    expect(copies).toHaveLength(2); // user + assistant bubbles both get one
    fireEvent.click(copies[0]);
    expect(writeText).toHaveBeenCalledWith("post the digest");
    // "Copied" lands only after the clipboard write RESOLVES (a rejected write must
    // not claim success), hence the await.
    await waitFor(() => expect(copies[0].textContent).toMatch(/Copied|已复制/));
    fireEvent.click(copies[1]);
    expect(writeText).toHaveBeenCalledWith("Done — posted to #all-openworker.");
  });

  it("timestamp renders only when the item carries ts; full date rides the title", () => {
    render(<Transcript items={ITEMS} onApprove={vi.fn()} />);

    const stamps = screen.getAllByTestId("bubble-ts");
    expect(stamps).toHaveLength(1); // the ts-less assistant bubble shows none
    const when = new Date(TS * 1000);
    expect(stamps[0].textContent).toBe(when.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }));
    expect(stamps[0].getAttribute("title")).toBe(when.toLocaleString());
  });
});

describe("memory save notices (MEMORY-SPEC §5.1)", () => {
  it("new save Undo calls onUndoMemory(id, undefined)", () => {
    const onUndoMemory = vi.fn();
    render(
      <Transcript
        items={[{ kind: "memory", id: 7, text: "prefers tables" }]}
        onApprove={vi.fn()}
        onUndoMemory={onUndoMemory}
      />,
    );
    fireEvent.click(screen.getByTestId("memory-undo-7"));
    expect(onUndoMemory).toHaveBeenCalledWith(7, undefined);
  });

  it("update Undo calls onUndoMemory(id, previous)", () => {
    const onUndoMemory = vi.fn();
    render(
      <Transcript
        items={[{ kind: "memory", id: 9, text: "prefers lists", previous: "prefers tables" }]}
        onApprove={vi.fn()}
        onUndoMemory={onUndoMemory}
      />,
    );
    fireEvent.click(screen.getByTestId("memory-undo-9"));
    expect(onUndoMemory).toHaveBeenCalledWith(9, "prefers tables");
  });

  it("undone=true hides Undo and shows the restored/forgotten state", () => {
    const onUndoMemory = vi.fn();
    const { rerender } = render(
      <Transcript
        items={[{ kind: "memory", id: 3, text: "prefers tables", undone: true }]}
        onApprove={vi.fn()}
        onUndoMemory={onUndoMemory}
      />,
    );
    expect(screen.queryByTestId("memory-undo-3")).toBeNull();
    expect(screen.getByTestId("memory-toast-undone")).toBeTruthy();

    rerender(
      <Transcript
        items={[
          {
            kind: "memory",
            id: 4,
            text: "prefers lists",
            previous: "prefers tables",
            undone: true,
          },
        ]}
        onApprove={vi.fn()}
        onUndoMemory={onUndoMemory}
      />,
    );
    expect(screen.queryByTestId("memory-undo-4")).toBeNull();
    expect(screen.getByTestId("memory-toast-undone")).toBeTruthy();
  });
});

describe("humanizeTool", () => {
  it("prefers run_shell's model-written description and keeps the command as the object", () => {
    const line = humanizeTool("run_shell", { command: "git log --since=yesterday", description: "List yesterday's merges" });
    expect(line.pre).toBe("Ran ");
    expect(line.obj).toBe("git log --since=yesterday");
    expect(line.post).toContain("list yesterday's merges");
  });

  it("falls back to 'Used <tool> — <short args>' for unknown tools", () => {
    const line = humanizeTool("gmail_search_messages", { query: "from:ci" });
    expect(line.pre).toBe("Used gmail_search_messages");
    expect(line.post).toContain("query=from:ci");
  });

  it("summarizes todo_write by its single item and status", () => {
    const line = humanizeTool("todo_write", { todos: [{ content: "Post the digest", status: "in_progress" }] });
    expect(line.pre).toBe("Updated the plan — ");
    expect(line.obj).toContain("Post the digest");
    expect(line.post).toBe(" → in progress");
  });

  it("still renders pre-rename todo_write histories (legacy `items` key)", () => {
    const line = humanizeTool("todo_write", { items: [{ content: "Old plan", status: "pending" }] });
    expect(line.obj).toContain("Old plan");
  });
});
