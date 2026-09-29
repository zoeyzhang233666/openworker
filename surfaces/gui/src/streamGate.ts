import type { Item } from "./types";

// Text must not wait for a language-dependent word threshold. If a tool call
// follows, normal event handling archives the narration in its tool group.
export type StreamMode = "none" | "hold" | "quiet" | "answer";

export function streamMode(streaming: string, _items: Item[], _running: boolean): StreamMode {
  return streaming.trim() ? "answer" : "none";
}
