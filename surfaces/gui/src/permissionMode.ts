/** Composer permission modes mirrored from coworker.permissions.Mode. */
export const PERMISSION_MODES = ["discuss", "interactive", "auto"] as const;
export type PermissionMode = (typeof PERMISSION_MODES)[number];

/** GUI placeholder until /v1/health (or WS ready) supplies the remembered default. */
export const DEFAULT_PERMISSION_MODE: PermissionMode = "interactive";

export function isPermissionMode(value: unknown): value is PermissionMode {
  return (
    typeof value === "string" &&
    (PERMISSION_MODES as readonly string[]).includes(value)
  );
}

/** Prefer health/ready mode when valid; otherwise keep the current Composer value. */
export function resolvePermissionMode(
  candidate: unknown,
  fallback: PermissionMode = DEFAULT_PERMISSION_MODE,
): PermissionMode {
  return isPermissionMode(candidate) ? candidate : fallback;
}

/**
 * Boot contract: apply /v1/health.mode before clearing the splash so the first
 * visible Composer frame matches the server-remembered default (not a hard-coded
 * interactive flash waiting on WS ready).
 */
export function modeFromHealth(health: { mode?: string | null }): PermissionMode | null {
  return isPermissionMode(health.mode) ? health.mode : null;
}
