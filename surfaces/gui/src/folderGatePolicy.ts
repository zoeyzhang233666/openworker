/**
 * D-082: project-scoped personas (Code) still need a real folder before tools run, but the
 * FolderGate modal must not block the empty-state chrome. Gate opens on send / suggestion /
 * explicit CTA; new-session creation never forces it open.
 */

export function needsWorkspaceBeforeSend(
  projectScoped: boolean,
  workspace: string | null | undefined,
): boolean {
  return projectScoped && !workspace;
}

/** New ▾ / 新建对话 for a gated persona: show empty state first (never open the overlay). */
export function openFolderGateOnNewSession(): boolean {
  return false;
}
