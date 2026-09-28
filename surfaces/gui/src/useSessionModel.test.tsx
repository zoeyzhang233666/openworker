import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useSessionModel } from "./useSessionModel";
import { Session } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("keeps the chosen model through delayed settings and repeated outgoing messages", async () => {
  const { result } = renderHook(() => useSessionModel("one"));
  let resolveSettings!: (model: string) => void;
  const delayedSettings = new Promise<string>((resolve) => { resolveSettings = resolve; });
  const refresh = delayedSettings.then((model) => result.current.setDefaultModel(model));
  act(() => result.current.acceptSessionModel("one", "initial"));
  act(() => result.current.selectModel("one", "chosen"));
  act(() => result.current.acceptSessionModel("one", "chosen"));
  await act(async () => { resolveSettings("global-default"); await refresh; });
  expect(result.current.model).toBe("chosen");

  class Socket {
    static OPEN = 1;
    static CONNECTING = 0;
    readyState = 1;
    send = vi.fn();
  }
  vi.stubGlobal("WebSocket", Socket);
  const session = new Session("one", "", "cowork", { onEvent: vi.fn() });
  session.userMessage("first question", undefined, result.current.model);
  session.userMessage("next question", undefined, result.current.model);
  const ws = (session as unknown as { ws: Socket }).ws;
  expect(ws.send.mock.calls.map(([payload]) => JSON.parse(payload).model)).toEqual(["chosen", "chosen"]);
});

it("keeps separate conversation choices and uses defaults only before a session is bound", () => {
  const { result, rerender } = renderHook(({ id }) => useSessionModel(id), { initialProps: { id: "one" } });
  act(() => result.current.setDefaultModel("default-a"));
  act(() => result.current.acceptSessionModel("one", "model-one"));
  rerender({ id: "two" });
  expect(result.current.model).toBe("default-a");
  act(() => result.current.acceptSessionModel("two", "model-two"));
  act(() => result.current.setDefaultModel("default-b"));
  expect(result.current.model).toBe("model-two");
  rerender({ id: "one" });
  expect(result.current.model).toBe("model-one");
  rerender({ id: "new" });
  expect(result.current.model).toBe("default-b");
});

it("does not let a stale ready or older acknowledgement undo a new selection", () => {
  const { result } = renderHook(() => useSessionModel("one"));
  act(() => result.current.selectModel("one", "first-choice"));
  act(() => result.current.selectModel("one", "latest-choice"));
  let retry: string | undefined;
  act(() => { retry = result.current.acceptSessionModel("one", "default"); });
  expect(retry).toBe("latest-choice");
  act(() => result.current.acceptSessionModel("one", "first-choice"));
  expect(result.current.model).toBe("latest-choice");
  act(() => result.current.acceptSessionModel("one", "latest-choice"));
  // Once acknowledged, a later server-authoritative choice (e.g. another client) applies.
  act(() => result.current.acceptSessionModel("one", "server-choice"));
  expect(result.current.model).toBe("server-choice");
});
