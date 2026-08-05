/**
 * Helpers for keeping an in-flight turn alive across nav / conversation switches.
 * The server does not cancel on WS disconnect; the UI must not wipe or forget `running`.
 */

/** True when clicking the already-active session — only surface should change. */
export function shouldSkipSessionReselect(
  id: string,
  currentId: string,
  opts?: { agent?: string; currentAgent?: string; workspace?: string; currentWorkspace?: string | null },
): boolean {
  if (id !== currentId) return false;
  if (opts?.agent && opts.currentAgent && opts.agent !== opts.currentAgent) return false;
  if (
    opts?.workspace !== undefined &&
    opts.workspace &&
    opts.currentWorkspace !== undefined &&
    opts.workspace !== (opts.currentWorkspace || "")
  ) {
    return false;
  }
  return true;
}

/** Restore Stop/spinner from the WS `ready` payload after reconnect. */
export function runningFromReady(data: { running?: unknown } | null | undefined): boolean {
  return data?.running === true;
}

/** Turn events that imply a live turn even if we missed `turn_start`. */
const LIVE_TURN_EVENTS = new Set([
  "assistant_delta",
  "reasoning_delta",
  "tool_proposed",
  "tool_finished",
  "permission_required",
  "directory_requested",
  "plan_proposed",
  "question_requested",
  "compacting",
  "compacted",
]);

export function eventImpliesRunning(type: string): boolean {
  return LIVE_TURN_EVENTS.has(type);
}

/**
 * Guard a stale async `getSessionMessages` result: only apply if this select
 * generation is still current and targets the same session.
 */
export function shouldApplySessionMessages(
  generation: number,
  currentGeneration: number,
  expectedSessionId: string,
  currentSessionId: string,
): boolean {
  return generation === currentGeneration && expectedSessionId === currentSessionId;
}

/**
 * Guard live WS events: after switching chats the old socket is closed, but an
 * in-flight `onmessage` can still run and must not paint error/interrupted onto
 * the newly selected session.
 */
export function shouldHandleSessionEvent(
  boundSessionId: string,
  currentSessionId: string,
): boolean {
  return boundSessionId === currentSessionId;
}
