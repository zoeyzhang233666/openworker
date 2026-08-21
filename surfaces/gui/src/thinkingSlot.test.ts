import { describe, expect, it } from "vitest";
import {
  answerBubbleShowsReasoning,
  thinkingSlotView,
  trailingSettledReasoning,
  turnAlreadyShowsReasoning,
} from "./thinkingSlot";

describe("thinkingSlot (D-186)", () => {
  const user = { kind: "user", text: "hi" };

  it("forceOpens while live reasoning streams with no answer text", () => {
    expect(
      thinkingSlotView({
        running: true,
        reasoningStream: "weigh options",
        streaming: "",
        items: [user],
      }),
    ).toEqual({ text: "weigh options", live: true, forceOpen: true });
  });

  it("keeps collapsed chrome when early assistant_delta arrives (hold gap)", () => {
    expect(
      thinkingSlotView({
        running: true,
        reasoningStream: "weigh options",
        streaming: "Checking…",
        items: [user],
      }),
    ).toEqual({ text: "weigh options", live: false, forceOpen: false });
  });

  it("keeps collapsed settled thinking after assistant_message clears the live stream", () => {
    const items = [
      user,
      { kind: "assistant", text: "", reasoning: "weigh options" },
    ];
    expect(trailingSettledReasoning(items)).toBe("weigh options");
    expect(
      thinkingSlotView({
        running: true,
        reasoningStream: "",
        streaming: "",
        items,
      }),
    ).toEqual({ text: "weigh options", live: false, forceOpen: false });
  });

  it("hides the App slot once TurnGroup owns reasoning above steps", () => {
    const items = [
      user,
      { kind: "assistant", text: "", reasoning: "pick tools" },
      { kind: "tool", text: "" },
    ];
    expect(turnAlreadyShowsReasoning(items)).toBe(true);
    expect(
      thinkingSlotView({
        running: true,
        reasoningStream: "",
        streaming: "",
        items,
      }),
    ).toBeNull();
  });

  it("does not duplicate when an answer bubble already shows reasoning", () => {
    const items = [
      user,
      { kind: "assistant", text: "Here is the answer.", reasoning: "done thinking" },
    ];
    expect(answerBubbleShowsReasoning(items)).toBe(true);
    expect(
      thinkingSlotView({
        running: true,
        reasoningStream: "",
        streaming: "",
        items,
      }),
    ).toBeNull();
  });

  it("hides when not running", () => {
    expect(
      thinkingSlotView({
        running: false,
        reasoningStream: "x",
        streaming: "",
        items: [user],
      }),
    ).toBeNull();
  });
});
