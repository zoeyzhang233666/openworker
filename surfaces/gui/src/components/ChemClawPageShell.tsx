import type { ReactNode } from "react";

/** Full-bleed ChemClaw management surface — matches ScheduledView / IntegrationsView shell. */
export function ChemClawPageShell({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <main className={`chemclaw-page flex-1 min-w-0 flex flex-col min-h-0 ${className}`.trim()}>
      <div className="flex-1 min-w-0 overflow-y-auto hairline-scroll">{children}</div>
    </main>
  );
}
