import { useRef, useState } from "react";
import { useEffect } from "react";
import {
  createSkill,
  deleteSkill,
  listSkills,
  revealSkill,
  stageSkillUpload,
  confirmSkillUpload,
  updateSkill,
  type SkillRow,
  type SkillUploadPreview,
} from "../api";
import { useI18n } from "../i18n";
import { Icon } from "./Icon";

const CARD = "rounded-xl2 border border-line bg-panel";
const FIELD_LABEL = "text-[12.5px] font-medium text-ink";
const INPUT =
  "w-full min-w-0 px-3 py-2 rounded-lg border border-line bg-paper text-[13px] text-ink outline-none focus:border-accent";
const BTN_ACCENT =
  "text-[12.5px] px-3 py-2 rounded-lg bg-accent text-white shrink-0 disabled:opacity-40";
const BTN_BORDERED =
  "text-[12.5px] px-3 py-2 rounded-lg border border-line bg-paper hover:border-lineStrong shrink-0";
const BADGE =
  "text-[11px] px-2 py-0.5 rounded-full border border-line bg-paper text-muted shrink-0";

type Editor = {
  mode: "new" | "edit";
  name: string;
  description: string;
  instructions: string;
};

const emptyEditor = (): Editor => ({
  mode: "new",
  name: "",
  description: "",
  instructions: "",
});

async function fileToB64(file: File): Promise<string> {
  const buf =
    typeof file.arrayBuffer === "function"
      ? await file.arrayBuffer()
      : await new Promise<ArrayBuffer>((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(r.result as ArrayBuffer);
          r.onerror = () => reject(r.error);
          r.readAsArrayBuffer(file);
        });
  const bytes = new Uint8Array(buf);
  let bin = "";
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

export function SkillsTab({
  onCreateSkill,
  hideHeader = false,
}: {
  onCreateSkill?: (description: string) => void;
  hideHeader?: boolean;
}) {
  const { t } = useI18n();
  const [rows, setRows] = useState<SkillRow[]>([]);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [upload, setUpload] = useState<SkillUploadPreview | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [armedDelete, setArmedDelete] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState<{ name: string; text: string; tone: "ok" | "warn" } | null>(
    null,
  );
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = () => listSkills().then(setRows);
  useEffect(() => {
    refresh();
  }, []);

  const fail = (res: { ok?: boolean; error?: string }) => {
    setNotice(null);
    if (res.ok === false) {
      setError(res.error || t("skills.errorGeneric"));
      return true;
    }
    setError("");
    return false;
  };

  const save = async () => {
    if (!editor) return;
    const res =
      editor.mode === "new"
        ? await createSkill({
            name: editor.name.trim(),
            description: editor.description.trim(),
            instructions: editor.instructions,
          })
        : await updateSkill(editor.name, {
            description: editor.description.trim(),
            instructions: editor.instructions,
          });
    if (fail(res)) return;
    setEditor(null);
    if (editor.mode === "new")
      setNotice({ name: editor.name.trim(), text: t("skills.confirmReady"), tone: "ok" });
    refresh();
  };

  const onPickFile = async (file: File | undefined) => {
    if (!file) return;
    const res = await stageSkillUpload(await fileToB64(file), file.name);
    if (fail(res)) return;
    setUpload(res);
  };

  const confirmUpload = async () => {
    if (!upload?.token) return;
    const res = await confirmSkillUpload(upload.token);
    if (fail(res)) return;
    setUpload(null);
    setNotice({ name: upload.name || t("skills.title"), text: t("skills.confirmReady"), tone: "ok" });
    refresh();
  };

  const remove = async (row: SkillRow) => {
    if (armedDelete !== row.name) {
      setArmedDelete(row.name);
      return;
    }
    setArmedDelete(null);
    const res = await deleteSkill(row.name);
    if (fail(res)) return;
    setNotice({ name: row.name, text: t("skills.confirmDeleted"), tone: "warn" });
    refresh();
  };

  return (
    <section>
      {!hideHeader ? (
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h2 className="text-[16px] font-semibold">{t("skills.title")}</h2>
            <p className="text-[12.5px] text-muted mt-1 leading-relaxed">{t("skills.subtitle")}</p>
          </div>
          <div className="relative shrink-0">
            <button
              className={BTN_ACCENT}
              aria-haspopup="menu"
              aria-expanded={addOpen}
              onClick={() => setAddOpen((v) => !v)}
            >
              <span className="inline-flex items-center gap-1.5">
                <Icon name="plus" size={13} /> {t("skills.add")}
              </span>
            </button>
            {addOpen ? (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setAddOpen(false)} />
                <div
                  role="menu"
                  className="absolute right-0 top-full mt-1.5 w-80 rounded-xl2 border border-line bg-panel shadow-xl z-20 p-1.5"
                  onKeyDown={(e) => e.key === "Escape" && setAddOpen(false)}
                >
                  <button
                    role="menuitem"
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-paper"
                    onClick={() => {
                      setAddOpen(false);
                      setEditor(emptyEditor());
                    }}
                  >
                    <div className="text-[13px] font-medium">{t("skills.writeMyself")}</div>
                    <div className="text-[11.5px] text-muted">{t("skills.writeMyselfHint")}</div>
                  </button>
                  <button
                    role="menuitem"
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-paper"
                    onClick={() => {
                      setAddOpen(false);
                      fileInput.current?.click();
                    }}
                  >
                    <div className="text-[13px] font-medium">{t("skills.importFile")}</div>
                    <div className="text-[11.5px] text-muted">{t("skills.importFileHint")}</div>
                  </button>
                  <button
                    role="menuitem"
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-paper disabled:opacity-40"
                    disabled={!onCreateSkill}
                    onClick={() => {
                      setAddOpen(false);
                      onCreateSkill?.("");
                    }}
                  >
                    <div className="text-[13px] font-medium">{t("skills.createWithChemClaw")}</div>
                    <div className="text-[11.5px] text-muted">{t("skills.createWithChemClawHint")}</div>
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="flex justify-end mb-4">
          <div className="relative shrink-0">
            <button
              className={BTN_ACCENT}
              aria-haspopup="menu"
              aria-expanded={addOpen}
              onClick={() => setAddOpen((v) => !v)}
            >
              <span className="inline-flex items-center gap-1.5">
                <Icon name="plus" size={13} /> {t("skills.add")}
              </span>
            </button>
            {addOpen ? (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setAddOpen(false)} />
                <div
                  role="menu"
                  className="absolute right-0 top-full mt-1.5 w-80 rounded-xl2 border border-line bg-panel shadow-xl z-20 p-1.5"
                  onKeyDown={(e) => e.key === "Escape" && setAddOpen(false)}
                >
                  <button
                    role="menuitem"
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-paper"
                    onClick={() => {
                      setAddOpen(false);
                      setEditor(emptyEditor());
                    }}
                  >
                    <div className="text-[13px] font-medium">{t("skills.writeMyself")}</div>
                    <div className="text-[11.5px] text-muted">{t("skills.writeMyselfHint")}</div>
                  </button>
                  <button
                    role="menuitem"
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-paper"
                    onClick={() => {
                      setAddOpen(false);
                      fileInput.current?.click();
                    }}
                  >
                    <div className="text-[13px] font-medium">{t("skills.importFile")}</div>
                    <div className="text-[11.5px] text-muted">{t("skills.importFileHint")}</div>
                  </button>
                  <button
                    role="menuitem"
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-paper disabled:opacity-40"
                    disabled={!onCreateSkill}
                    onClick={() => {
                      setAddOpen(false);
                      onCreateSkill?.("");
                    }}
                  >
                    <div className="text-[13px] font-medium">{t("skills.createWithChemClaw")}</div>
                    <div className="text-[11.5px] text-muted">{t("skills.createWithChemClawHint")}</div>
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}
      <input
        ref={fileInput}
        type="file"
        accept=".zip,.md"
        className="hidden"
        aria-label={t("skills.importFile")}
        onChange={(e) => {
          onPickFile(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      {error ? (
        <div className="text-[12.5px] text-red-500 mb-3" role="alert">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div
          role="status"
          className={
            "mb-3 flex items-start gap-2 rounded-lg border px-3 py-2 text-[12.5px] " +
            (notice.tone === "ok"
              ? "bg-tealSoft/70 text-tealInk border-tealInk/20"
              : "bg-warnSoft/70 text-warnInk border-warnInk/20")
          }
        >
          <span className="min-w-0">
            <b>{notice.name}</b> {notice.text}
          </span>
          <button
            className="ml-auto shrink-0 opacity-60 hover:opacity-100"
            aria-label={t("Dismiss")}
            onClick={() => setNotice(null)}
          >
            ✕
          </button>
        </div>
      ) : null}

      {upload ? (
        <div className={`${CARD} p-4 mb-4`}>
          <div className="text-[13px] font-medium mb-1">{t("skills.reviewTitle")}</div>
          <p className="text-[12.5px] text-muted mb-3">{t("skills.reviewIntro")}</p>
          <div className="text-[13px] mb-1">
            <span className="font-medium">{upload.name}</span>
            <span className="text-muted"> — {upload.description || t("skills.noDescription")}</span>
          </div>
          <pre className="text-[12px] bg-paper border border-line rounded-lg p-3 whitespace-pre-wrap max-h-64 overflow-y-auto mb-2">
            {upload.instructions}
          </pre>
          {upload.files?.length ? (
            <div className="text-[12px] text-muted mb-2">
              {t("skills.bundledFiles")}: {upload.files.join(", ")}
            </div>
          ) : null}
          <div className="flex gap-2 mt-3">
            <button className={BTN_ACCENT} onClick={confirmUpload}>
              {t("skills.install")}
            </button>
            <button className={BTN_BORDERED} onClick={() => setUpload(null)}>
              {t("Cancel")}
            </button>
          </div>
        </div>
      ) : null}

      {editor ? (
        <div className={`${CARD} p-4 mb-4`}>
          <div className="text-[13px] font-medium mb-3">
            {editor.mode === "new" ? t("skills.newSkill") : `${t("Edit")} ${editor.name}`}
          </div>
          <label className={FIELD_LABEL} htmlFor="skill-name">
            {t("skills.fieldName")}
          </label>
          <input
            id="skill-name"
            className={`${INPUT} mt-1 mb-3`}
            value={editor.name}
            disabled={editor.mode === "edit"}
            placeholder="weekly-report"
            onChange={(e) => setEditor({ ...editor, name: e.target.value })}
          />
          <label className={FIELD_LABEL} htmlFor="skill-desc">
            {t("skills.fieldDescription")}
          </label>
          <input
            id="skill-desc"
            className={`${INPUT} mt-1 mb-3`}
            value={editor.description}
            placeholder={t("skills.fieldDescriptionHint")}
            onChange={(e) => setEditor({ ...editor, description: e.target.value })}
          />
          <label className={FIELD_LABEL} htmlFor="skill-instructions">
            {t("skills.fieldInstructions")}
          </label>
          <textarea
            id="skill-instructions"
            className={`${INPUT} mt-1 mb-3 min-h-[140px] font-mono`}
            value={editor.instructions}
            onChange={(e) => setEditor({ ...editor, instructions: e.target.value })}
          />
          <div className="flex gap-2 mt-3">
            <button
              className={BTN_ACCENT}
              disabled={!editor.name.trim() || !editor.instructions.trim()}
              onClick={save}
            >
              {t("skills.saveSkill")}
            </button>
            <button className={BTN_BORDERED} onClick={() => setEditor(null)}>
              {t("Cancel")}
            </button>
          </div>
        </div>
      ) : null}

      <div className={`${CARD} divide-y divide-line`}>
        {rows.length === 0 && !editor ? (
          <div className="p-5 text-[13px] text-muted">{t("skills.noSkills")}</div>
        ) : null}
        {rows.map((row) => (
          <div key={row.name} className="flex items-center gap-3 px-4 py-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-[13px] font-medium ${row.enabled ? "" : "text-muted"}`}>
                  {row.name}
                </span>
                {row.source !== "local" ? <span className={BADGE}>{row.source}</span> : null}
                {row.files ? (
                  <button
                    className="inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded-md border border-line bg-paper text-muted hover:text-ink hover:border-lineStrong shrink-0"
                    title={t("skills.showFolder")}
                    onClick={() => revealSkill(row.name)}
                  >
                    <Icon name="folder" size={11} /> {t("skills.files", { count: row.files })}
                  </button>
                ) : null}
              </div>
              <div className="text-[12px] text-muted leading-relaxed">{row.description}</div>
            </div>
            <button
              className={BTN_BORDERED}
              title={t("Edit")}
              onClick={() =>
                setEditor({
                  mode: "edit",
                  name: row.name,
                  description: row.description,
                  instructions: row.instructions,
                })
              }
            >
              <Icon name="pencil" size={13} />
            </button>
            <button
              className={BTN_BORDERED}
              aria-label={`${t("Delete")} ${row.name}`}
              onClick={() => remove(row)}
              onBlur={() => setArmedDelete(null)}
            >
              {armedDelete === row.name ? t("skills.confirmDelete") : <Icon name="trash" size={13} />}
            </button>
            <label className="inline-flex items-center gap-1.5 text-[12px] text-muted">
              <input
                type="checkbox"
                role="switch"
                aria-label={`${row.name} ${t("skills.enabled")}`}
                checked={row.enabled}
                onChange={(e) => {
                  const on = e.target.checked;
                  updateSkill(row.name, { enabled: on }).then((res) => {
                    if (!fail(res))
                      setNotice({
                        name: row.name,
                        text: on ? t("skills.confirmReady") : t("skills.confirmOff"),
                        tone: on ? "ok" : "warn",
                      });
                    refresh();
                  });
                }}
              />
              {t("skills.enabled")}
            </label>
          </div>
        ))}
      </div>
    </section>
  );
}
