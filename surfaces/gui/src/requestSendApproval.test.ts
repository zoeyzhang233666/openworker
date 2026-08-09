import { describe, expect, it } from "vitest";
import {
  READY_FOR_HUMAN_SEND,
  isReadyForHumanSend,
  sendApprovalIntentMessage,
} from "./requestSendApproval";

describe("requestSendApproval", () => {
  it("detects ready_for_human_send in assistant text", () => {
    expect(isReadyForHumanSend(null)).toBe(false);
    expect(isReadyForHumanSend("draft only")).toBe(false);
    expect(isReadyForHumanSend(`verdict=pass\n${READY_FOR_HUMAN_SEND}`)).toBe(true);
  });

  it("builds an intent that requires email_send and human approval", () => {
    const msg = sendApprovalIntentMessage();
    expect(msg).toContain("email_send");
    expect(msg).toContain(READY_FOR_HUMAN_SEND);
    expect(msg).toMatch(/审批|连接/);
    expect(msg).not.toMatch(/自动发送|skip approval/i);
  });
});
