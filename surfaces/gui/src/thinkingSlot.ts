/**
 * D-186: keep a single thinking chrome slot through live → early answer stream → settle → tools.
 * Pure helpers (no React) so hold-gap / handoff behavior is unit-testable.
 */

export type ThinkingSlotItem = {
  kind: string;
  text?: string;
  reasoning?: string;
};

/** Latest non-empty assistant.reasoning after the last user (or any trailing assistant). */
export function trailingSettledReasoning(items: ThinkingSlotItem[]): string {
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i];
    if (it.kind === "user") break;
    if (it.kind === "assistant" && (it.reasoning || "").trim()) return it.reasoning!.trim();
  }
  return "";
}

/**
 * True when Transcript TurnGroup will already render ThinkingBlock above steps
 * (tools/approvals present with reasoning on an assistant in the open turn).
 */
export function turnAlreadyShowsReasoning(items: ThinkingSlotItem[]): boolean {
  let hasToolOrApproval = false;
  let reasoning = "";
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i];
    if (it.kind === "user" || it.kind === "notice" || it.kind === "question") break;
    if (it.kind === "tool" || it.kind === "approval") hasToolOrApproval = true;
    if (it.kind === "assistant" && (it.reasoning || "").trim() && !reasoning) {
      reasoning = it.reasoning!.trim();
    }
  }
  return hasToolOrApproval && !!reasoning;
}

/** Non-empty assistant answer bubble already carries ThinkingBlock in Transcript. */
export function answerBubbleShowsReasoning(items: ThinkingSlotItem[]): boolean {
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i];
    if (it.kind === "user") break;
    if (it.kind === "assistant" && (it.text || "").trim() && (it.reasoning || "").trim()) return true;
  }
  return false;
}

export type ThinkingSlotOpts = {
  running: boolean;
  reasoningStream: string;
  streaming: string;
  /** Prefer explicit trailing buffer; falls back to scanning items. */
  settledReasoning?: string;
  items: ThinkingSlotItem[];
};

export type ThinkingSlotView = {
  text: string;
  /** Live pulse + forceOpen only while stream is the sole source and no answer text yet. */
  live: boolean;
  forceOpen: boolean;
} | null;

/**
 * What the App-level ThinkingBlock slot should render (null = hide; Turn/bubble owns it or nothing).
 */
export function thinkingSlotView(opts: ThinkingSlotOpts): ThinkingSlotView {
  if (!opts.running) return null;
  if (turnAlreadyShowsReasoning(opts.items)) return null;

  const settled =
    (opts.settledReasoning || "").trim() || trailingSettledReasoning(opts.items);
  const liveText = (opts.reasoningStream || "").trim();
  const text = liveText || settled;
  if (!text) return null;

  // Answer bubble in Transcript already shows reasoning — don't duplicate (unless still live-streaming thought).
  if (!liveText && answerBubbleShowsReasoning(opts.items)) return null;

  // Still receiving reasoning (and no answer stream yet): D-178 forceOpen.
  if (liveText && !opts.streaming) {
    return { text: liveText, live: true, forceOpen: true };
  }
  // Early assistant_delta (hold) or post-assistant_message settle: keep chrome, collapsed.
  return { text, live: false, forceOpen: false };
}
