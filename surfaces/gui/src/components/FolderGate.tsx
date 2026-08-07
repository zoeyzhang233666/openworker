import { useEffect, useState } from "react";
import { getRecentWorkspaces, openWorkspace, type RecentWorkspace } from "../api";
import { chooseFolder } from "../tauri";
import { useI18n } from "../i18n";

// The workspace picker for project-scoped personas (D-082). New Code sessions show the empty
// state first; this overlay opens on send / suggestion / explicit CTA. Always offer 关闭 so the
// user is never trapped without a folder (owner: cancel must dismiss even when workspace is null).
interface Props {
  onChoose: (path: string, branch?: string | null) => void;
  onCancel?: () => void;
  create?: boolean; // "New project" mode: create the folder if missing
}

export function FolderGate({ onChoose, onCancel, create }: Props) {
  const { t } = useI18n();
  const [recents, setRecents] = useState<RecentWorkspace[]>([]);
  const [path, setPath] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getRecentWorkspaces().then(setRecents).catch(() => {});
  }, []);

  const open = async (p: string, doCreate = false) => {
    setError("");
    const res = await openWorkspace(p.trim(), doCreate);
    if (res.ok) onChoose(res.path, res.git_branch);
    else setError(res.error || t("could not open that folder"));
  };

  const browse = async () => {
    const picked = await chooseFolder();
    if (picked) {
      setPath(picked);
      open(picked, create); // a picked folder already exists; create flag is harmless
    }
  };

  return (
    <div className="gate-overlay">
      <div className="gate">
        <div className="gate-mark">✦</div>
        <h2>{t(create ? "New project" : "Choose a project folder")}</h2>
        <p className="gate-sub">
          {create
            ? t("Pick a folder or enter a path. If the path doesn't exist, it will be created.")
            : t("This coworker needs a workspace to read, edit, and run in.")}
        </p>

        <div className="gate-input">
          <input
            placeholder="/path/to/your/project"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && open(path, create)}
            autoFocus
          />
          <button className="btn" onClick={browse} title={t("Pick a folder")}>
            {t("Browse…")}
          </button>
          <button className="btn primary" onClick={() => open(path, create)} disabled={!path.trim()}>
            {t(create ? "Create" : "Open")}
          </button>
        </div>
        {error && <div className="gate-error">{error}</div>}

        {recents.length > 0 && (
          <>
            <div className="gate-label">{t("Recent")}</div>
            <div className="gate-recents">
              {recents.map((w) => (
                <div className="gate-recent" key={w.path} onClick={() => open(w.path)} title={w.path}>
                  <span className="folder">📁 {w.name}</span>
                  <span className="dim">{w.path}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {onCancel && (
          <div className="gate-foot">
            <button className="btn gate-cancel" onClick={onCancel}>
              {t("gate.close")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
