import { act, cleanup, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useResearchDepth } from "./useResearchDepth";
import { Session } from "./api";
import { Composer } from "./components/Composer";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("waits for ready and isolates sessions, reconnects and pending choices", () => {
  const { result, rerender } = renderHook(({ id }) => useResearchDepth(id), { initialProps: { id: "old" } });
  expect(result.current.researchDepth).toBeUndefined();
  act(() => result.current.acceptResearchDepth("old", "deep"));
  expect(result.current.researchDepth).toBe("deep");
  rerender({ id: "new" });
  expect(result.current.researchDepth).toBeUndefined();
  act(() => result.current.acceptResearchDepth("new", "fast"));
  act(() => result.current.selectResearchDepth("new", "deep"));
  let pending: unknown;
  act(() => { pending = result.current.acceptResearchDepth("new", "fast"); });
  expect(pending).toBe("deep");
  expect(result.current.researchDepth).toBe("deep");
  act(() => result.current.acceptResearchDepth("new", "deep"));
  act(() => result.current.acceptResearchDepth("new", "fast"));
  expect(result.current.researchDepth).toBe("fast");
  rerender({ id: "old" });
  expect(result.current.researchDepth).toBe("deep");
});

it("accepts authoritative rejection or running reconnect", () => {
  const { result } = renderHook(() => useResearchDepth("s"));
  act(() => result.current.selectResearchDepth("s", "deep"));
  act(() => result.current.acceptResearchDepth("s", "fast", true));
  expect(result.current.researchDepth).toBe("fast");
});

it("sends the visible choice with messages and explicit continue independently of permission mode", () => {
  class Socket {
    static OPEN = 1;
    static CONNECTING = 0;
    readyState = 1;
    send = vi.fn();
  }
  vi.stubGlobal("WebSocket", Socket);
  const session = new Session("s", "", "cowork", { onEvent: vi.fn() });
  session.setResearchDepth("fast");
  session.userMessage("业务概览", undefined, "chosen", undefined, undefined, "fast");
  session.retry("deep");
  const ws = (session as unknown as { ws: Socket }).ws;
  const frames = ws.send.mock.calls.map(([payload]) => JSON.parse(payload));
  expect(frames.map(f => f.research_depth)).toEqual(["fast", "fast", "deep"]);
  expect(frames.every(f => f.mode === undefined)).toBe(true);
  expect(frames[1].model).toBe("chosen");
});

it("renders a working picker and locks it during execution or disconnect", () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({}) })));
  const props = { mode: "interactive", model: "test", connected: true, running: false,
    onSend: vi.fn(), onInterrupt: vi.fn(), onModeChange: vi.fn(), onModelChange: vi.fn(),
    researchDepth: "fast" as const, onResearchDepthChange: vi.fn() };
  const { rerender } = render(<Composer {...props} />);
  const picker = screen.getByRole("combobox", { name: /研究深度|Research depth/ }) as HTMLSelectElement;
  fireEvent.change(picker, { target: { value: "deep" } });
  expect(props.onResearchDepthChange).toHaveBeenCalledWith("deep");
  expect(props.onModeChange).not.toHaveBeenCalled();
  rerender(<Composer {...props} running />);
  expect(picker.disabled).toBe(true);
  rerender(<Composer {...props} connected={false} />);
  expect(picker.disabled).toBe(true);
});
