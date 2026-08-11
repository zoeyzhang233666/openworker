import { useState, type ReactNode } from "react";
import type { Attachment } from "../types";
import { useRoots } from "../useRoots";
import { useI18n, type MessageKey } from "../i18n";
import { AddFolderForm } from "./AddFolderForm";

// Empty-state starters:
// - cowork (D-080): chemical knowledge-work deliverables
// - chain-lobster (D-072): value-chain starters
// - chat (D-083): lightweight Q&A, no workspace
// - platform-rewrite: chem multi-platform rewrite starters
// - export/domestic/radar/engagement (D-122): sales lobster starters
// App supplies the hero title (hideGreeting); per-agent greeting override for chat.

export type SessionIntroVariant =
  | "cowork"
  | "chain-lobster"
  | "chat"
  | "platform-rewrite"
  | "export-sales"
  | "domestic-sales"
  | "opportunity-radar"
  | "export-engagement";

type TaskCardSpec = {
  testId: string;
  titleKey: MessageKey;
  subKey: MessageKey;
  promptKey: MessageKey;
};

function TaskCards({
  groupTestId,
  cards,
  onPrefill,
  t,
}: {
  groupTestId: string;
  cards: TaskCardSpec[];
  onPrefill: (text: string, attachments?: Attachment[]) => void;
  t: (key: MessageKey) => string;
}) {
  return (
    <div className="intro-tasks" data-testid={groupTestId}>
      {cards.map((card) => (
        <button
          key={card.testId}
          className="task-card"
          data-testid={card.testId}
          onClick={() => onPrefill(t(card.promptKey))}
        >
          <span className="task-card-body">
            <span className="task-card-title">{t(card.titleKey)}</span>
            <span className="task-card-sub">{t(card.subKey)}</span>
          </span>
          <span className="task-card-act">{t("intro.act.start")}</span>
        </button>
      ))}
    </div>
  );
}

const CHAIN_CARDS: TaskCardSpec[] = [
  {
    testId: "intro-task-chain-map",
    titleKey: "intro.chain.task1.title",
    subKey: "intro.chain.task1.sub",
    promptKey: "intro.chain.task1.prompt",
  },
  {
    testId: "intro-task-chain-scarce",
    titleKey: "intro.chain.task2.title",
    subKey: "intro.chain.task2.sub",
    promptKey: "intro.chain.task2.prompt",
  },
  {
    testId: "intro-task-chain-equity",
    titleKey: "intro.chain.task3.title",
    subKey: "intro.chain.task3.sub",
    promptKey: "intro.chain.task3.prompt",
  },
];

const REWRITE_CARDS: TaskCardSpec[] = [
  {
    testId: "intro-task-rewrite-xhs",
    titleKey: "intro.rewrite.task1.title",
    subKey: "intro.rewrite.task1.sub",
    promptKey: "intro.rewrite.task1.prompt",
  },
  {
    testId: "intro-task-rewrite-douyin",
    titleKey: "intro.rewrite.task2.title",
    subKey: "intro.rewrite.task2.sub",
    promptKey: "intro.rewrite.task2.prompt",
  },
  {
    testId: "intro-task-rewrite-gate",
    titleKey: "intro.rewrite.task3.title",
    subKey: "intro.rewrite.task3.sub",
    promptKey: "intro.rewrite.task3.prompt",
  },
];

const CHAT_CARDS: TaskCardSpec[] = [
  {
    testId: "intro-task-chat-explain",
    titleKey: "intro.chat.task1.title",
    subKey: "intro.chat.task1.sub",
    promptKey: "intro.chat.task1.prompt",
  },
  {
    testId: "intro-task-chat-compare",
    titleKey: "intro.chat.task2.title",
    subKey: "intro.chat.task2.sub",
    promptKey: "intro.chat.task2.prompt",
  },
  {
    testId: "intro-task-chat-checklist",
    titleKey: "intro.chat.task3.title",
    subKey: "intro.chat.task3.sub",
    promptKey: "intro.chat.task3.prompt",
  },
];

const EXPORT_SALES_CARDS: TaskCardSpec[] = [
  {
    testId: "intro-task-export-sales-prospect",
    titleKey: "intro.export.task1.title",
    subKey: "intro.export.task1.sub",
    promptKey: "intro.export.task1.prompt",
  },
  {
    testId: "intro-task-export-sales-customs",
    titleKey: "intro.export.task2.title",
    subKey: "intro.export.task2.sub",
    promptKey: "intro.export.task2.prompt",
  },
  {
    testId: "intro-task-export-sales-score",
    titleKey: "intro.export.task3.title",
    subKey: "intro.export.task3.sub",
    promptKey: "intro.export.task3.prompt",
  },
];

const DOMESTIC_SALES_CARDS: TaskCardSpec[] = [
  {
    testId: "intro-task-domestic-sales-prospect",
    titleKey: "intro.domestic.task1.title",
    subKey: "intro.domestic.task1.sub",
    promptKey: "intro.domestic.task1.prompt",
  },
  {
    testId: "intro-task-domestic-sales-verify",
    titleKey: "intro.domestic.task2.title",
    subKey: "intro.domestic.task2.sub",
    promptKey: "intro.domestic.task2.prompt",
  },
  {
    testId: "intro-task-domestic-sales-list",
    titleKey: "intro.domestic.task3.title",
    subKey: "intro.domestic.task3.sub",
    promptKey: "intro.domestic.task3.prompt",
  },
];

const RADAR_CARDS: TaskCardSpec[] = [
  {
    testId: "intro-task-radar-tenders",
    titleKey: "intro.radar.task1.title",
    subKey: "intro.radar.task1.sub",
    promptKey: "intro.radar.task1.prompt",
  },
  {
    testId: "intro-task-radar-signals",
    titleKey: "intro.radar.task2.title",
    subKey: "intro.radar.task2.sub",
    promptKey: "intro.radar.task2.prompt",
  },
  {
    testId: "intro-task-radar-score",
    titleKey: "intro.radar.task3.title",
    subKey: "intro.radar.task3.sub",
    promptKey: "intro.radar.task3.prompt",
  },
];

const ENGAGEMENT_CARDS: TaskCardSpec[] = [
  {
    testId: "intro-task-engagement-outreach",
    titleKey: "intro.engagement.task1.title",
    subKey: "intro.engagement.task1.sub",
    promptKey: "intro.engagement.task1.prompt",
  },
  {
    testId: "intro-task-engagement-quote",
    titleKey: "intro.engagement.task2.title",
    subKey: "intro.engagement.task2.sub",
    promptKey: "intro.engagement.task2.prompt",
  },
  {
    testId: "intro-task-engagement-gate",
    titleKey: "intro.engagement.task3.title",
    subKey: "intro.engagement.task3.sub",
    promptKey: "intro.engagement.task3.prompt",
  },
];

function ledeForVariant(variant: SessionIntroVariant): MessageKey {
  switch (variant) {
    case "chat":
      return "intro.chat.lede";
    case "platform-rewrite":
      return "intro.rewrite.lede";
    case "export-sales":
      return "intro.export.lede";
    case "domestic-sales":
      return "intro.domestic.lede";
    case "opportunity-radar":
      return "intro.radar.lede";
    case "export-engagement":
      return "intro.engagement.lede";
    default:
      return "intro.lede";
  }
}

/** Map agent id → SessionIntro variant; null means use code SUGGESTIONS path. */
export function introVariantForAgent(agent: string): SessionIntroVariant | null {
  switch (agent) {
    case "cowork":
      return "cowork";
    case "chain-lobster":
      return "chain-lobster";
    case "chat":
      return "chat";
    case "platform-rewrite-lobster":
      return "platform-rewrite";
    case "export-sales-lobster":
      return "export-sales";
    case "domestic-sales-lobster":
      return "domestic-sales";
    case "opportunity-radar-lobster":
      return "opportunity-radar";
    case "export-engagement-lobster":
      return "export-engagement";
    default:
      return null;
  }
}

export function SessionIntro({
  sessionId,
  onOpenSessionSettings: _onOpenSessionSettings,
  onPrefill,
  hideGreeting = false,
  variant = "cowork",
}: {
  sessionId: string;
  // Kept for App call-site compatibility; cowork starters no longer open session settings.
  onOpenSessionSettings: () => void;
  onPrefill: (text: string, attachments?: Attachment[]) => void;
  /** When true, skip the local h1 — App already shows the hero greeting (D-067 / D-083). */
  hideGreeting?: boolean;
  variant?: SessionIntroVariant;
}) {
  const { t } = useI18n();
  const { roots, busy, error, addRoot } = useRoots(sessionId);
  const [addingFolder, setAddingFolder] = useState(false);

  const shared = roots.filter((r) => !r.primary && r.removable !== false);
  const ledeKey = ledeForVariant(variant);

  const pickFolder = () => {
    // A shared folder already exists → straight to the prompt; otherwise share one first.
    if (shared.length > 0) onPrefill(t("intro.task.folder.prompt"));
    else setAddingFolder((v) => !v);
  };

  let tasks: ReactNode;
  if (variant === "chain-lobster") {
    tasks = (
      <TaskCards groupTestId="intro-tasks-chain-lobster" cards={CHAIN_CARDS} onPrefill={onPrefill} t={t} />
    );
  } else if (variant === "platform-rewrite") {
    tasks = (
      <TaskCards
        groupTestId="intro-tasks-platform-rewrite"
        cards={REWRITE_CARDS}
        onPrefill={onPrefill}
        t={t}
      />
    );
  } else if (variant === "chat") {
    tasks = <TaskCards groupTestId="intro-tasks-chat" cards={CHAT_CARDS} onPrefill={onPrefill} t={t} />;
  } else if (variant === "export-sales") {
    tasks = (
      <TaskCards
        groupTestId="intro-tasks-export-sales"
        cards={EXPORT_SALES_CARDS}
        onPrefill={onPrefill}
        t={t}
      />
    );
  } else if (variant === "domestic-sales") {
    tasks = (
      <TaskCards
        groupTestId="intro-tasks-domestic-sales"
        cards={DOMESTIC_SALES_CARDS}
        onPrefill={onPrefill}
        t={t}
      />
    );
  } else if (variant === "opportunity-radar") {
    tasks = (
      <TaskCards groupTestId="intro-tasks-opportunity-radar" cards={RADAR_CARDS} onPrefill={onPrefill} t={t} />
    );
  } else if (variant === "export-engagement") {
    tasks = (
      <TaskCards
        groupTestId="intro-tasks-export-engagement"
        cards={ENGAGEMENT_CARDS}
        onPrefill={onPrefill}
        t={t}
      />
    );
  } else {
    tasks = (
      <div className="intro-tasks" data-testid="intro-tasks-cowork">
        <button
          className="task-card"
          data-testid="intro-task-memo"
          onClick={() => onPrefill(t("intro.task.memo.prompt"))}
        >
          <span className="task-card-body">
            <span className="task-card-title">{t("intro.task.memo.title")}</span>
            <span className="task-card-sub">{t("intro.task.memo.sub")}</span>
          </span>
          <span className="task-card-act">{t("intro.act.start")}</span>
        </button>

        <button
          className="task-card"
          data-testid="intro-task-price"
          onClick={() => onPrefill(t("intro.task.price.prompt"))}
        >
          <span className="task-card-body">
            <span className="task-card-title">{t("intro.task.price.title")}</span>
            <span className="task-card-sub">{t("intro.task.price.sub")}</span>
          </span>
          <span className="task-card-act">{t("intro.act.start")}</span>
        </button>

        <button className="task-card" data-testid="intro-task-folder" onClick={pickFolder}>
          <span className="task-card-body">
            <span className="task-card-title">{t("intro.task.folder.title")}</span>
            <span className="task-card-sub">{t("intro.task.folder.sub")}</span>
          </span>
          <span className="task-card-act">{t("intro.task.folder.act")}</span>
        </button>
        {addingFolder && (
          <div className="intro-addfolder">
            <AddFolderForm
              startOpen
              busy={busy}
              onAdd={async (path, writable) => {
                const ok = await addRoot(path, writable);
                if (ok !== false) onPrefill(t("intro.task.folder.prompt"));
                return ok;
              }}
              onDismiss={() => setAddingFolder(false)}
            />
            {error && <div className="roots-err">{error}</div>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={hideGreeting ? "intro intro-tasks-only" : "intro"}>
      {!hideGreeting && (
        <>
          <h1 className="greeting">
            <span className="mark">✦</span> {t("What should we produce?")}
          </h1>
          <p className="intro-lede">{t(ledeKey)}</p>
        </>
      )}
      {hideGreeting && <p className="intro-lede mt-2">{t(ledeKey)}</p>}
      {tasks}
    </div>
  );
}
