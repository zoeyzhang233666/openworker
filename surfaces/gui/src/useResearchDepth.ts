import { useCallback, useRef, useState } from "react";

export type ResearchDepth = "fast" | "deep";

/** Wait for server readiness so opening a legacy session cannot overwrite its depth. */
export function useResearchDepth(sessionId: string) {
  const choices = useRef(new Map<string, { depth: ResearchDepth; pending: boolean }>());
  const [, render] = useState(0);
  const selectResearchDepth = useCallback((id: string, depth: ResearchDepth) => {
    choices.current.set(id, { depth, pending: true });
    render(v => v + 1);
  }, []);
  const acceptResearchDepth = useCallback((id: string, depth: unknown, force = false): ResearchDepth | undefined => {
    if (depth !== "fast" && depth !== "deep") return undefined;
    const current = choices.current.get(id);
    if (!force && current?.pending && current.depth !== depth) return current.depth;
    choices.current.set(id, { depth, pending: false });
    render(v => v + 1);
    return undefined;
  }, []);
  return { researchDepth: choices.current.get(sessionId)?.depth, selectResearchDepth, acceptResearchDepth };
}
