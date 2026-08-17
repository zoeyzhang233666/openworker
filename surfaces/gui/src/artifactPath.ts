/** Workspace-relative artifact identity. Security still belongs on the server. */

export function normalizeSeparators(path: string): string {
  return String(path || "").replace(/\\/g, "/");
}

/**
 * Turn a chip path (relative, artifact:, or absolute under `workspace`) into the
 * relative identity used by /artifacts/read. Does not use basename matching.
 */
export function artifactIdentity(path: string, workspace?: string): string {
  let p = normalizeSeparators(path).trim();
  if (p.toLowerCase().startsWith("artifact:")) {
    p = p.slice("artifact:".length);
  }
  const ws = normalizeSeparators(workspace || "").replace(/\/+$/, "");
  if (ws) {
    const prefix = ws.endsWith(":") ? ws : ws + "/";
    if (p.length >= prefix.length && p.slice(0, prefix.length).toLowerCase() === prefix.toLowerCase()) {
      return p.slice(prefix.length);
    }
    if (p.toLowerCase() === ws.toLowerCase()) {
      return "";
    }
  }
  return p.replace(/^\/+/, "");
}
