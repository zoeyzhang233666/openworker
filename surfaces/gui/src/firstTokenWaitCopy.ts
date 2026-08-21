/** First-token / post-align / planning-gap wait copy pools (D-076 / D-079 / D-176). English keys = en-US; zh via interfaceMessages. */

/** Interval between rotated lobster wait lines. */
export const FIRST_TOKEN_WAIT_ROTATE_MS = 3000;

/** @deprecated Use FIRST_TOKEN_WAIT_ROTATE_MS */
export const FIRST_TOKEN_WAIT_LATE_MS = FIRST_TOKEN_WAIT_ROTATE_MS;

export const FIRST_TOKEN_WAIT_EARLY_KEYS = [
  "Lobster's scratching its head…",
  "Lobster's breaking the question into bits…",
] as const;

export const FIRST_TOKEN_WAIT_LATE_KEYS = [
  "Still diving deep — bubbles soon…",
  "Thinking long — not napping…",
  "Still chewing on it — bubbles soon…",
  "Slow-cooking a good answer…",
] as const;

/** Early pool then late pool; used after a fresh user send (not post-align). */
export const FIRST_TOKEN_WAIT_ROTATION_KEYS = [
  ...FIRST_TOKEN_WAIT_EARLY_KEYS,
  ...FIRST_TOKEN_WAIT_LATE_KEYS,
] as const;

/** After the user picks ask_user options or sends a follow-up right after aligning (D-079 套1). */
export const FEEDBACK_WAIT_ROTATION_KEYS = [
  "Got it — Lobster's continuing with your pick…",
  "Folding your notes into the plan…",
  "Aligning — next step soon…",
  "Lobster noted that — carrying on~",
] as const;

/** After reasoning exists but tools/answer have not started yet (D-176 planning gap). */
export const PLANNING_WAIT_ROTATION_KEYS = [
  "Lobster is planning the next step…",
  "Mapping tools for what comes next…",
  "Still on it — next move soon…",
] as const;

export type FirstTokenWaitKey = (typeof FIRST_TOKEN_WAIT_ROTATION_KEYS)[number];
export type FeedbackWaitKey = (typeof FEEDBACK_WAIT_ROTATION_KEYS)[number];
export type PlanningWaitKey = (typeof PLANNING_WAIT_ROTATION_KEYS)[number];
export type WaitCopyPool = "first" | "feedback" | "planning";

export function nextFirstTokenWaitIndex(
  index: number,
  length: number = FIRST_TOKEN_WAIT_ROTATION_KEYS.length,
): number {
  if (length <= 0) return 0;
  return ((index % length) + length) % length;
}

export function advanceFirstTokenWaitIndex(
  index: number,
  length: number = FIRST_TOKEN_WAIT_ROTATION_KEYS.length,
): number {
  if (length <= 0) return 0;
  return (nextFirstTokenWaitIndex(index, length) + 1) % length;
}

export type WaitItem = {
  kind: string;
  resolved?: string;
  /** Assistant bubble / narration text (D-183 planning: empty+reasoning ≠ progress). */
  text?: string;
  /** Settled reasoning sidecar on an assistant item. */
  reasoning?: string;
};

/** Index of the latest user message or resolved ask_user question (whichever is later). */
export function waitAnchorIndex(items: WaitItem[]): number {
  let lastUser = -1;
  let lastResolvedQ = -1;
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if (it.kind === "user") lastUser = i;
    if (it.kind === "question" && it.resolved) lastResolvedQ = i;
  }
  return Math.max(lastUser, lastResolvedQ);
}

/** True when there is visible turn progress after the wait anchor. */
export function hasPostAnchorActivity(items: WaitItem[]): boolean {
  const anchor = waitAnchorIndex(items);
  for (let i = anchor + 1; i < items.length; i++) {
    if (items[i].kind === "notice") continue;
    return true;
  }
  return false;
}

/**
 * D-183: tools / approvals / non-empty assistant text after the anchor.
 * Reasoning-only assistants do not count — they are the settled thinking disclosure.
 */
export function hasPostAnchorProgress(items: WaitItem[]): boolean {
  const anchor = waitAnchorIndex(items);
  for (let i = anchor + 1; i < items.length; i++) {
    const it = items[i];
    if (it.kind === "notice") continue;
    if (it.kind === "tool" || it.kind === "approval") return true;
    if (it.kind === "assistant") {
      if ((it.text || "").trim()) return true;
      continue;
    }
    return true;
  }
  return false;
}

/** True when any assistant after the anchor carries non-empty reasoning. */
export function hasPostAnchorReasoning(items: WaitItem[]): boolean {
  const anchor = waitAnchorIndex(items);
  for (let i = anchor + 1; i < items.length; i++) {
    const it = items[i];
    if (it.kind === "assistant" && (it.reasoning || "").trim()) return true;
  }
  return false;
}

/** @deprecated Prefer hasPostAnchorActivity (D-079). */
export function hasPostUserTurnActivity(items: WaitItem[]): boolean {
  return hasPostAnchorActivity(items);
}

/** first vs feedback pool for empty-window lobster wait (not planning). */
export function waitCopyPool(items: WaitItem[]): WaitCopyPool {
  const anchor = waitAnchorIndex(items);
  if (anchor < 0) return "first";
  const at = items[anchor];
  if (at.kind === "question" && at.resolved) return "feedback";
  if (at.kind === "user") {
    for (let i = anchor - 1; i >= 0; i--) {
      if (items[i].kind === "notice") continue;
      if (items[i].kind === "question" && items[i].resolved) return "feedback";
      break;
    }
  }
  return "first";
}

export function waitRotationKeys(pool: WaitCopyPool): readonly string[] {
  if (pool === "feedback") return FEEDBACK_WAIT_ROTATION_KEYS;
  if (pool === "planning") return PLANNING_WAIT_ROTATION_KEYS;
  return FIRST_TOKEN_WAIT_ROTATION_KEYS;
}

/** Lobster wait: running, no compact/reasoning/stream, nothing after wait anchor yet. */
export function isFirstTokenEmptyWindow(
  items: WaitItem[],
  opts: {
    running: boolean;
    compacting: boolean;
    reasoningStream: string;
    streaming: string;
  },
): boolean {
  if (!opts.running || opts.compacting) return false;
  if (opts.reasoningStream || opts.streaming) return false;
  return !hasPostAnchorActivity(items);
}

/** Live ThinkingBlock defaultOpen: still before tools/answer bubbles (reasoning allowed). */
export function isFirstTokenThinkingOpen(items: WaitItem[]): boolean {
  return !hasPostAnchorActivity(items);
}

/**
 * D-176 + D-183: planning hint under thinking while awaiting tools/answer.
 * - Live: `reasoningStream` before any progress (tools / non-empty answer).
 * - Settled: live cleared but reasoning-only assistant already in items (collapse continuity).
 */
export function isPlanningWaitWindow(
  items: WaitItem[],
  opts: {
    running: boolean;
    compacting: boolean;
    reasoningStream: string;
    streaming: string;
  },
): boolean {
  if (!opts.running || opts.compacting) return false;
  if (opts.streaming) return false;
  if (hasPostAnchorProgress(items)) return false;
  return !!opts.reasoningStream || hasPostAnchorReasoning(items);
}
