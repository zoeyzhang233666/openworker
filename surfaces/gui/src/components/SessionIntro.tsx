import { useState } from "react";
import type { Attachment } from "../types";
import { useRoots } from "../useRoots";
import { useI18n, type MessageKey } from "../i18n";
import { AddFolderForm } from "./AddFolderForm";

// Empty-state starters:
// - cowork (D-080): chemical knowledge-work deliverables
// - chain-lobster (D-072): value-chain starters
// - chat (D-083): lightweight Q&A, no workspace
// - platform-rewrite: chem multi-platform rewrite starters
// App supplies the hero title (hideGreeting); per-agent greeting override for chat.

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
  /** cowork | chain-lobster | chat | platform-rewrite */
  variant?: "cowork" | "chain-lobster" | "chat" | "platform-rewrite";
}) {
  const { t } = useI18n();
  const { roots, busy, error, addRoot } = useRoots(sessionId);
  const [addingFolder, setAddingFolder] = useState(false);

  const shared = roots.filter((r) => !r.primary && r.removable !== false);
  const ledeKey = (
    variant === "chat"
      ? "intro.chat.lede"
      : variant === "platform-rewrite"
        ? "intro.rewrite.lede"
        : "intro.lede"
  ) as MessageKey;

  const pickFolder = () => {
    // A shared folder already exists → straight to the prompt; otherwise share one first.
    if (shared.length > 0) onPrefill(t("intro.task.folder.prompt"));
    else setAddingFolder((v) => !v);
  };

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

      {variant === "chain-lobster" ? (
        <div className="intro-tasks" data-testid="intro-tasks-chain-lobster">
          <button
            className="task-card"
            data-testid="intro-task-chain-map"
            onClick={() => onPrefill(t("intro.chain.task1.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.chain.task1.title")}</span>
              <span className="task-card-sub">{t("intro.chain.task1.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
          <button
            className="task-card"
            data-testid="intro-task-chain-scarce"
            onClick={() => onPrefill(t("intro.chain.task2.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.chain.task2.title")}</span>
              <span className="task-card-sub">{t("intro.chain.task2.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
          <button
            className="task-card"
            data-testid="intro-task-chain-equity"
            onClick={() => onPrefill(t("intro.chain.task3.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.chain.task3.title")}</span>
              <span className="task-card-sub">{t("intro.chain.task3.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
        </div>
      ) : variant === "platform-rewrite" ? (
        <div className="intro-tasks" data-testid="intro-tasks-platform-rewrite">
          <button
            className="task-card"
            data-testid="intro-task-rewrite-xhs"
            onClick={() => onPrefill(t("intro.rewrite.task1.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.rewrite.task1.title")}</span>
              <span className="task-card-sub">{t("intro.rewrite.task1.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
          <button
            className="task-card"
            data-testid="intro-task-rewrite-douyin"
            onClick={() => onPrefill(t("intro.rewrite.task2.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.rewrite.task2.title")}</span>
              <span className="task-card-sub">{t("intro.rewrite.task2.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
          <button
            className="task-card"
            data-testid="intro-task-rewrite-gate"
            onClick={() => onPrefill(t("intro.rewrite.task3.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.rewrite.task3.title")}</span>
              <span className="task-card-sub">{t("intro.rewrite.task3.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
        </div>
      ) : variant === "chat" ? (
        <div className="intro-tasks" data-testid="intro-tasks-chat">
          <button
            className="task-card"
            data-testid="intro-task-chat-explain"
            onClick={() => onPrefill(t("intro.chat.task1.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.chat.task1.title")}</span>
              <span className="task-card-sub">{t("intro.chat.task1.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
          <button
            className="task-card"
            data-testid="intro-task-chat-compare"
            onClick={() => onPrefill(t("intro.chat.task2.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.chat.task2.title")}</span>
              <span className="task-card-sub">{t("intro.chat.task2.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
          <button
            className="task-card"
            data-testid="intro-task-chat-checklist"
            onClick={() => onPrefill(t("intro.chat.task3.prompt"))}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.chat.task3.title")}</span>
              <span className="task-card-sub">{t("intro.chat.task3.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
        </div>
      ) : (
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
      )}
    </div>
  );
}
