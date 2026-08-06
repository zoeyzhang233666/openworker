import { useEffect, useState } from "react";
import { getConnectors, getSessionConnections } from "../api";
import type { Attachment } from "../types";
import { ConnectorIcon } from "../connectors/ConnectorIcon";
import { indexConnectors, visualFor, type ConnectorMap } from "../connectors/visuals";
import { useRoots } from "../useRoots";
import { useI18n } from "../i18n";
import { AddFolderForm } from "./AddFolderForm";

// Empty-state for a fresh Cowork session (§27): a greeting, exactly three concrete template
// tasks, and the composer — nothing else. Each task carries its own setup: no icon tiles (the
// title is the row), connector dots on the sub-line (brand color = connected and enabled for
// this session, grayscale = not — §23's vocabulary), and sub-line copy that is always the task's
// OUTCOME, never connection state. Sources ready → "Start →" on hover, click prefills the
// composer. Not ready → "Configure ›" always visible (for a gated row the setup action IS the
// row's meaning), opening the §23 Session settings drawer — no second setup surface here.
//
// chain-lobster variant (D-072): three chemical value-chain starters; no fixed product name.

const FOLDER_PROMPT = "Analyze the files in this folder and summarize what matters.";
const HUBSPOT_PROMPT =
  "Create a report on my recent HubSpot leads: sources, stages, and who needs follow-up.";
const GH_SLACK_PROMPT =
  "Set up a weekly progress report: summarize activity in my GitHub repos and post it to Slack every Friday morning.";

const CHAIN_PROMPT_1 =
  "请帮我拆解一个化工品从原料到最终用途的上下游关系，并说明相关企业；需要时画出带关系标签的产业链图。请先问清楚品种、用途边界和范围。";
const CHAIN_PROMPT_2 =
  "请帮我找出某条化工产业链里最稀缺的环节，并给证据定级。请先问清楚主题边界和范围，再区分事实与推测。";
const CHAIN_PROMPT_3 =
  "请从化工产业链的稀缺环节出发，分析可能对应哪些上市公司机会。请先把产业环节说清楚，再映射到公司和行情，并标明不确定处。";

export function SessionIntro({
  sessionId,
  onOpenSessionSettings,
  onPrefill,
  hideGreeting = false,
  variant = "cowork",
}: {
  sessionId: string;
  // Opens the §23 Session settings drawer (sources section) — the gated rows' Configure target.
  onOpenSessionSettings: () => void;
  onPrefill: (text: string, attachments?: Attachment[]) => void;
  /** When true, skip the local h1 — App already shows「与 xxx 畅谈」(D-067). */
  hideGreeting?: boolean;
  /** cowork = folder/HubSpot/GitHub; chain-lobster = chemical value-chain starters. */
  variant?: "cowork" | "chain-lobster";
}) {
  const { t } = useI18n();
  const { roots, busy, error, addRoot } = useRoots(sessionId);
  const [live, setLive] = useState<Set<string>>(new Set());
  const [byName, setByName] = useState<ConnectorMap>({});
  const [addingFolder, setAddingFolder] = useState(false);

  useEffect(() => {
    // Live = what this session can touch right now (connected AND not muted here) — the same
    // truth the §23 glance renders, so the dots here can never disagree with the row above.
    getSessionConnections(sessionId)
      .then((c) => setLive(new Set(c.connected.filter((x) => x.enabled).map((x) => x.connector))))
      .catch(() => {});
    getConnectors()
      .then((list) => setByName(indexConnectors(list)))
      .catch(() => {});
  }, [sessionId]);

  const shared = roots.filter((r) => !r.primary);
  const hubspotReady = live.has("hubspot");
  const ghSlackReady = live.has("github") && live.has("slack");

  const dot = (name: string, on: boolean) => (
    <span className={"task-dot" + (on ? "" : " off")} key={name}>
      <ConnectorIcon connector={visualFor(name, "connector", byName)} size={12} />
    </span>
  );

  const pickFolder = () => {
    // A shared folder already exists → straight to the prompt; otherwise share one first.
    if (shared.length > 0) onPrefill(FOLDER_PROMPT);
    else setAddingFolder((v) => !v);
  };

  return (
    <div className={hideGreeting ? "intro intro-tasks-only" : "intro"}>
      {!hideGreeting && (
        <>
          <h1 className="greeting">
            <span className="mark">✦</span> {t("What should we produce?")}
          </h1>
          <p className="intro-lede">{t("intro.lede")}</p>
        </>
      )}
      {hideGreeting && <p className="intro-lede mt-2">{t("intro.lede")}</p>}

      {variant === "chain-lobster" ? (
        <div className="intro-tasks" data-testid="intro-tasks-chain-lobster">
          <button
            className="task-card"
            data-testid="intro-task-chain-map"
            onClick={() => onPrefill(CHAIN_PROMPT_1)}
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
            onClick={() => onPrefill(CHAIN_PROMPT_2)}
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
            onClick={() => onPrefill(CHAIN_PROMPT_3)}
          >
            <span className="task-card-body">
              <span className="task-card-title">{t("intro.chain.task3.title")}</span>
              <span className="task-card-sub">{t("intro.chain.task3.sub")}</span>
            </span>
            <span className="task-card-act">{t("intro.act.start")}</span>
          </button>
        </div>
      ) : (
      <div className="intro-tasks">
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
                if (ok !== false) onPrefill(FOLDER_PROMPT);
                return ok;
              }}
              onDismiss={() => setAddingFolder(false)}
            />
            {error && <div className="roots-err">{error}</div>}
          </div>
        )}

        <button
          className={"task-card" + (hubspotReady ? "" : " gated")}
          data-testid="intro-task-hubspot"
          onClick={() => (hubspotReady ? onPrefill(HUBSPOT_PROMPT) : onOpenSessionSettings())}
        >
          <span className="task-card-body">
            <span className="task-card-title">{t("intro.task.hubspot.title")}</span>
            <span className="task-card-sub">
              {dot("hubspot", hubspotReady)}
              {t("intro.task.hubspot.sub")}
            </span>
          </span>
          <span className="task-card-act">
            {hubspotReady ? t("intro.act.start") : t("intro.act.configure")}
          </span>
        </button>

        <button
          className={"task-card" + (ghSlackReady ? "" : " gated")}
          data-testid="intro-task-github-slack"
          onClick={() => (ghSlackReady ? onPrefill(GH_SLACK_PROMPT) : onOpenSessionSettings())}
        >
          <span className="task-card-body">
            <span className="task-card-title">{t("intro.task.github.title")}</span>
            <span className="task-card-sub">
              {dot("github", live.has("github"))}
              {dot("slack", live.has("slack"))}
              {t("intro.task.github.sub")}
            </span>
          </span>
          <span className="task-card-act">
            {ghSlackReady ? t("intro.act.start") : t("intro.act.configure")}
          </span>
        </button>
      </div>
      )}
    </div>
  );
}
