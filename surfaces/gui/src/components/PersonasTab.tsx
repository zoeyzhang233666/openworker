import { useEffect, useState } from "react";
import {
  deletePersona,
  getPersonas,
  getSessions,
  installPersona,
  updatePersona,
  type Persona,
  type PersonaConsent,
} from "../api";
import { useI18n, type MessageKey } from "../i18n";
import type { SessionInfo } from "../types";
import { Icon } from "./Icon";

// Personas management: enable a persona, choose whether it shows in the new-session picker,
// set the default, and install more from a local directory or a GitHub repo (snapshotted).
// Re-skinned to the mock's Tailwind card idiom (§ Settings-as-page); the page title supplies the
// heading, so this drops its own "Personas" sub-header.
const CARD = "rounded-xl2 border border-line bg-panel";
const SEC_H = "text-[11px] uppercase tracking-[0.05em] text-faint font-semibold";
const CHECK = "flex items-center gap-1.5 text-[12.5px] text-muted select-none shrink-0";
const SELECT = "px-2.5 py-2 rounded-lg border border-line bg-paper text-[13px] text-ink shrink-0";
const INPUT =
  "flex-1 min-w-0 px-3 py-2 rounded-lg border border-line bg-paper text-[13px] text-ink outline-none focus:border-accent";
const BTN_ACCENT = "text-[12.5px] px-3 py-2 rounded-lg bg-accent text-white shrink-0 disabled:opacity-40";
const BTN_BORDERED =
  "text-[12.5px] px-2.5 py-1.5 rounded-lg border border-line bg-paper hover:border-lineStrong shrink-0 disabled:opacity-40 disabled:hover:border-line";

const BUILTIN_IDS = new Set(["cowork", "code", "chat", "ops"]);

function personaLabel(
  t: (key: MessageKey, values?: Record<string, string | number>) => string,
  p: Persona,
  kind: "name" | "tagline",
): string {
  if (BUILTIN_IDS.has(p.id)) {
    return t(`experts.persona.${p.id}.${kind}` as MessageKey);
  }
  return kind === "name" ? p.name : p.tagline;
}

export function PersonasTab({ onOpenPersona }: { onOpenPersona?: (id: string) => void }) {
  const { t } = useI18n();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [mode, setMode] = useState<"git" | "dir">("git");
  const [src, setSrc] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [consent, setConsent] = useState<PersonaConsent[] | null>(null);
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  // Disabling archives the persona's conversations (server-side), so when there are any we
  // arm an inline confirm (same two-step idiom as delete) instead of flipping immediately.
  const [confirmOff, setConfirmOff] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);

  const reload = () => getPersonas().then(setPersonas).catch(() => {});
  const reloadSessions = () => getSessions().then(setSessions).catch(() => {});
  useEffect(() => {
    reload();
    reloadSessions();
  }, []);

  // Real conversations the disable would archive (unarchived; run sessions are server-hidden).
  const liveCount = (id: string) =>
    sessions.filter((s) => s.agent === id && !s.archived).length;

  const toggle = async (
    id: string,
    body: { enabled?: boolean; surfaced?: boolean; default?: boolean },
  ) => {
    const r = await updatePersona(id, body);
    if (r.personas) setPersonas(r.personas);
    else reload();
    if (body.enabled === false) reloadSessions(); // counts just changed
  };

  const requestDisable = (p: Persona) => {
    if (liveCount(p.id) > 0) setConfirmOff(p.id);
    else toggle(p.id, { enabled: false });
  };

  const remove = async (id: string) => {
    setConfirmDel(null);
    const r = await deletePersona(id);
    if (!r.ok) {
      setMsg(r.error || t("experts.deleteFailed"));
      return;
    }
    if (r.personas) setPersonas(r.personas);
    else reload();
  };

  const install = async () => {
    if (!src.trim()) return;
    setBusy(true);
    setMsg(null);
    setConsent(null);
    const r = await installPersona(
      mode === "git" ? { git_url: src.trim() } : { dir: src.trim() },
    );
    setBusy(false);
    if (!r.ok) {
      setMsg(r.error || t("experts.installFailed"));
      return;
    }
    setConsent(r.consent || []);
    if (r.personas) setPersonas(r.personas);
    setMsg(t("experts.installed", { count: (r.consent || []).length }));
    setSrc("");
  };

  return (
    <div>
      <p className="text-[12.5px] text-muted mb-3 leading-relaxed">{t("experts.enableHint")}</p>

      <div className={CARD + " divide-y divide-line mb-6"}>
        {personas.map((p) => {
          const displayName = personaLabel(t, p, "name");
          return (
          <div key={p.id} className="px-4 py-3">
            <div className="flex items-center gap-4">
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] font-medium flex items-center gap-1.5">
                <span className="truncate">{displayName}</span>
                {p.default && <span className="text-accent" title={t("experts.defaultTitle")}>★</span>}
                {p.builtin && <span className="text-[11px] text-faint font-normal">· {t("experts.builtin")}</span>}
              </div>
              <div className="text-[12px] text-muted truncate">{personaLabel(t, p, "tagline")}</div>
            </div>
            <label className={CHECK}>
              <input
                type="checkbox"
                checked={p.enabled}
                onChange={(e) =>
                  e.target.checked ? toggle(p.id, { enabled: true }) : requestDisable(p)
                }
              />
              {t("experts.enabled")}
            </label>
            <label className={CHECK + (p.enabled ? "" : " opacity-40")}>
              <input
                type="checkbox"
                checked={p.surfaced}
                disabled={!p.enabled}
                onChange={(e) => toggle(p.id, { surfaced: e.target.checked })}
              />
              {t("experts.inPicker")}
            </label>
            <button
              className={BTN_BORDERED}
              disabled={p.default || !p.enabled}
              onClick={() => toggle(p.id, { default: true })}
            >
              {t("experts.setDefault")}
            </button>
            {onOpenPersona && (
              <button
                className="text-faint hover:text-ink shrink-0 p-1"
                title={t("experts.configure", { name: displayName })}
                aria-label={t("experts.configure", { name: displayName })}
                data-testid={`persona-configure-${p.id}`}
                onClick={() => onOpenPersona(p.id)}
              >
                <Icon name="sliders" size={15} />
              </button>
            )}
            {!p.builtin &&
              (confirmDel === p.id ? (
                <span className="flex items-center gap-1.5 shrink-0">
                  <button
                    className="text-[12px] px-2 py-1.5 rounded-lg bg-danger text-white"
                    data-testid={`persona-delete-confirm-${p.id}`}
                    onClick={() => remove(p.id)}
                  >
                    {t("experts.delete")}
                  </button>
                  <button className={BTN_BORDERED} onClick={() => setConfirmDel(null)}>
                    {t("experts.keep")}
                  </button>
                </span>
              ) : (
                <button
                  className="text-faint hover:text-danger shrink-0 p-1"
                  title={t("experts.deleteTitle")}
                  aria-label={`${t("experts.delete")} ${displayName}`}
                  data-testid={`persona-delete-${p.id}`}
                  onClick={() => setConfirmDel(p.id)}
                >
                  <Icon name="trash" size={14} />
                </button>
              ))}
            </div>
            {confirmOff === p.id && (
              <div
                className="mt-2 flex items-center gap-2.5 text-[12px] text-muted"
                data-testid={`persona-disable-warning-${p.id}`}
              >
                <span className="min-w-0">
                  {t("experts.disableWarning", { count: liveCount(p.id) })}
                </span>
                <button
                  className="text-[12px] px-2.5 py-1.5 rounded-lg bg-accent text-white shrink-0"
                  data-testid={`persona-disable-confirm-${p.id}`}
                  onClick={() => {
                    setConfirmOff(null);
                    toggle(p.id, { enabled: false });
                  }}
                >
                  {t("experts.disable")}
                </button>
                <button className={BTN_BORDERED} onClick={() => setConfirmOff(null)}>
                  {t("experts.keepEnabled")}
                </button>
              </div>
            )}
          </div>
          );
        })}
      </div>

      <div className={SEC_H + " mb-1.5"}>{t("experts.add")}</div>
      <p className="text-[12px] text-muted mb-3 leading-relaxed">{t("experts.addHint")}</p>
      <div className="flex items-center gap-2">
        <select className={SELECT} value={mode} onChange={(e) => setMode(e.target.value as "git" | "dir")}>
          <option value="git">{t("experts.sourceGit")}</option>
          <option value="dir">{t("experts.sourceDir")}</option>
        </select>
        <input
          className={INPUT}
          placeholder={mode === "git" ? t("experts.placeholderGit") : t("experts.placeholderDir")}
          value={src}
          onChange={(e) => setSrc(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && install()}
        />
        <button className={BTN_ACCENT} disabled={busy || !src.trim()} onClick={install}>
          {busy ? t("experts.installing") : t("experts.install")}
        </button>
      </div>
      {msg && <div className="text-[12.5px] text-muted mt-2.5">{msg}</div>}

      {consent && consent.length > 0 && (
        <div className="mt-4 space-y-2">
          {consent.map((c) => (
            <div key={c.id} className={CARD + " p-3.5"}>
              <div className="text-[13.5px] font-medium">{c.name}</div>
              <div className="text-[12px] text-muted mt-0.5 mb-2">{c.description}</div>
              <div className="text-[12px] text-ink">
                {t("experts.tools", { tools: c.tools.join(", ") || "—" })}
              </div>
              <div className="text-[12px] text-ink">
                {t("experts.risk", { risk: c.risk.join(", ") || "read" })}
                {c.connectors ? t("experts.connectors") : ""}
                {c.messaging ? t("experts.messaging") : ""}
                {c.mcp.length ? t("experts.mcp", { mcp: c.mcp.join(", ") }) : ""}
              </div>
              <div className="text-[12px] text-faint mt-1">
                {t("experts.recommendedMode", { mode: c.recommended_mode })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
