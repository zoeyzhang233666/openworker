import { describe, expect, it } from "vitest";

const sources = import.meta.glob(["./App.tsx", "./components/**/*.tsx", "./providers/**/*.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const remainingVisibleEnglish: Array<[file: string, text: string]> = [
  ["App.tsx", "New session"],
  ["components/SessionIntro.tsx", "What should we produce?"],
  ["components/Composer.tsx", "No model connected"],
  ["components/Sidebar.tsx", "sidebar.localUser"],
  ["components/RightRail.tsx", "No previewable files yet."],
  ["components/SearchModal.tsx", "Search chats"],
  ["components/ScheduledView.tsx", "Recurring tasks ChemClaw runs on a schedule."],
  ["components/SettingsView.tsx", "Trusted workspaces"],
  ["components/InboxView.tsx", "Nothing pending."],
  [
    "components/IntegrationsView.tsx",
    "Apps and tools your coworkers can use. Connected ones come first.",
  ],
  ["components/AuditView.tsx", "No audit events yet."],
  ["components/ApprovalCard.tsx", "Always allow"],
  ["components/WorkspaceTrustPrompt.tsx", "Trust this workspace"],
  ["components/Onboarding.tsx", "Connect your everyday tools"],
  [
    "components/ManageTabs.tsx",
    "External tool servers (stdio or HTTP), shared across all agents. Enabled servers' tools are permission-gated. Changes apply to new sessions —",
  ],
  ["components/ModelChecklist.tsx", "Add another model…"],
  ["providers/ProviderSetup.tsx", "All providers"],
  ["components/SubscriptionsChip.tsx", "Channels this session listens to"],
  ["components/Transcript.tsx", "Copy message"],
];

describe("remaining ChemClaw interface localization", () => {
  it.each(remainingVisibleEnglish)(
    "moves %s copy behind the existing i18n layer",
    (relativePath, visibleEnglish) => {
      const source = sources[`./${relativePath}`];
      expect(source).toBeDefined();
      expect(source).toContain(`t(${JSON.stringify(visibleEnglish)})`);
    },
  );
});
