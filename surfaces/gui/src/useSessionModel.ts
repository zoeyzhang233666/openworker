import { useCallback, useRef, useState } from "react";

/** Global settings seed new sessions; an established session owns its model. */
export function useSessionModel(sessionId: string) {
  const [defaultModel, setDefaultModel] = useState("gpt-5.6-sol");
  const choices = useRef(new Map<string, { model: string; pending: boolean }>());
  const [, render] = useState(0);

  const selectModel = useCallback((id: string, model: string) => {
    choices.current.set(id, { model, pending: true });
    render((version) => version + 1);
  }, []);

  // A late ready/ack must not undo a newer explicit selection. Return the pending
  // choice so a reconnected socket can submit it again before the next message.
  const acceptSessionModel = useCallback((id: string, model: string): string | undefined => {
    const current = choices.current.get(id);
    if (current?.pending && current.model !== model) return current.model;
    choices.current.set(id, { model, pending: false });
    render((version) => version + 1);
    return undefined;
  }, []);

  return {
    model: choices.current.get(sessionId)?.model ?? defaultModel,
    setDefaultModel,
    selectModel,
    acceptSessionModel,
  };
}
