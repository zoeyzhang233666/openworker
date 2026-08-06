/** First-token wait copy pools (D-076). English keys = en-US display; zh via interfaceMessages. */

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

/** Early pool then late pool; FirstTokenWaitLabel rotates through this in order. */
export const FIRST_TOKEN_WAIT_ROTATION_KEYS = [
  ...FIRST_TOKEN_WAIT_EARLY_KEYS,
  ...FIRST_TOKEN_WAIT_LATE_KEYS,
] as const;

export type FirstTokenWaitKey = (typeof FIRST_TOKEN_WAIT_ROTATION_KEYS)[number];

export function nextFirstTokenWaitIndex(index: number, length = FIRST_TOKEN_WAIT_ROTATION_KEYS.length): number {
  if (length <= 0) return 0;
  return ((index % length) + length) % length;
}

export function advanceFirstTokenWaitIndex(index: number, length = FIRST_TOKEN_WAIT_ROTATION_KEYS.length): number {
  if (length <= 0) return 0;
  return (nextFirstTokenWaitIndex(index, length) + 1) % length;
}

type WaitItem = { kind: string };

/** True when transcript has tool/approval/assistant (etc.) after the latest user message. */
export function hasPostUserTurnActivity(items: WaitItem[]): boolean {
  let lastUser = -1;
  for (let i = 0; i < items.length; i++) {
    if (items[i].kind === "user") lastUser = i;
  }
  for (let i = lastUser + 1; i < items.length; i++) {
    if (items[i].kind === "notice") continue;
    return true;
  }
  return false;
}

/** Lobster wait: running, no compact/reasoning/stream, nothing after last user yet. */
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
  return !hasPostUserTurnActivity(items);
}

/** Live ThinkingBlock defaultOpen: still before tools/answer bubbles (reasoning allowed). */
export function isFirstTokenThinkingOpen(items: WaitItem[]): boolean {
  return !hasPostUserTurnActivity(items);
}
