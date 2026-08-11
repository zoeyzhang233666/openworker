import { useCallback, useEffect, useState } from "react";
import {
  listPublicApiLookups,
  setPublicApiLookup,
  type PublicApiLookup,
} from "../api";
import { useI18n } from "../i18n";

function statusLabel(
  row: PublicApiLookup,
  t: (k: string) => string,
): string {
  if (row.kind === "free") return t("Ready · no API key");
  if (row.kind === "workspace_file") return t("Workspace file · no API key");
  if (row.configured) return t("Configured");
  return t("Not configured");
}

function pick(
  localeZh: boolean,
  zh: string | undefined,
  en: string | undefined,
): string {
  return (localeZh ? zh : en) || zh || en || "";
}

function LookupCard({
  row,
  localeZh,
  onSaved,
}: {
  row: PublicApiLookup;
  localeZh: boolean;
  onSaved: () => void;
}) {
  const { t } = useI18n();
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(row.base_url || "");
  const [provider, setProvider] = useState(row.provider || "duckduckgo");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setBaseUrl(row.base_url || "");
    setProvider(row.provider || "duckduckgo");
    setApiKey("");
    setMsg(null);
    setErr(null);
  }, [row.id, row.base_url, row.provider, row.has_api_key, row.configured]);

  const title = pick(localeZh, row.label_zh, row.label_en);
  const summary = pick(localeZh, row.summary_zh, row.summary_en);
  const purpose = pick(localeZh, row.purpose_zh, row.purpose_en);
  const usedBy = pick(localeZh, row.used_by_zh, row.used_by_en);
  const setup = pick(localeZh, row.setup_zh, row.setup_en);
  const writable =
    row.kind === "secret" || row.kind === "optional_secret";

  async function save(clearKey = false) {
    setBusy(true);
    setMsg(null);
    setErr(null);
    const body: Record<string, unknown> = {};
    if (row.id === "web_search") body.provider = provider;
    if (row.id === "cn_registry") body.base_url = baseUrl;
    if (clearKey) body.clear_api_key = true;
    else if (apiKey.trim()) body.api_key = apiKey.trim();
    const res = await setPublicApiLookup(row.id, body);
    setBusy(false);
    if (!res.ok) {
      setErr(res.error || t("Could not load public API lookups."));
      return;
    }
    setApiKey("");
    setMsg(t("Saved."));
    onSaved();
  }

  return (
    <article
      className="rounded-xl border border-line bg-panel/30 p-4 space-y-3"
      data-testid={`public-api-lookup-${row.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[14px] font-semibold text-ink">{title}</h3>
          <p className="text-[12px] text-muted mt-0.5">{summary}</p>
          <p className="text-[11px] text-faint mt-1">
            {t("Tool: {name}").replace("{name}", row.tool)}
          </p>
        </div>
        <span
          className={
            "shrink-0 text-[11px] px-2 py-0.5 rounded-full border " +
            (row.ready || row.kind === "optional_secret"
              ? "border-accent/30 text-accent"
              : "border-line text-muted")
          }
        >
          {statusLabel(row, t)}
        </span>
      </div>

      <div
        className="rounded-lg bg-paper/80 border border-line/50 px-3 py-2.5 space-y-2 text-[12.5px] leading-relaxed"
        data-testid={`public-api-lookup-help-${row.id}`}
      >
        {purpose && (
          <div>
            <div className="text-[11px] font-medium text-faint uppercase tracking-wide">
              {t("What it does")}
            </div>
            <p className="text-ink mt-0.5">{purpose}</p>
          </div>
        )}
        {usedBy && (
          <div>
            <div className="text-[11px] font-medium text-faint uppercase tracking-wide">
              {t("Who uses it")}
            </div>
            <p className="text-ink mt-0.5">{usedBy}</p>
          </div>
        )}
        {setup && (
          <div>
            <div className="text-[11px] font-medium text-faint uppercase tracking-wide">
              {t("How to set up")}
            </div>
            <p className="text-ink mt-0.5 whitespace-pre-wrap">{setup}</p>
          </div>
        )}
        {(row.docs_url || row.signup_url) && (
          <div className="flex flex-wrap gap-x-3 gap-y-1 pt-0.5">
            {row.docs_url ? (
              <a
                className="text-accent underline underline-offset-2"
                href={row.docs_url}
                target="_blank"
                rel="noopener noreferrer"
                data-testid={`public-api-lookup-docs-${row.id}`}
              >
                {t("Open docs")}
              </a>
            ) : null}
            {row.signup_url ? (
              <a
                className="text-accent underline underline-offset-2"
                href={row.signup_url}
                target="_blank"
                rel="noopener noreferrer"
                data-testid={`public-api-lookup-signup-${row.id}`}
              >
                {t("Open signup page")}
              </a>
            ) : null}
          </div>
        )}
      </div>

      {writable && (
        <div className="pt-1 space-y-2 border-t border-line/60">
          <p className="text-[12px] text-muted pt-2">
            {t("Paste the key from the signup page into the field below.")}
          </p>
          {row.id === "web_search" && (
            <label className="block text-[12px] text-muted">
              {t("Search provider")}
              <select
                className="mt-1 w-full rounded-lg border border-line bg-paper px-2.5 py-1.5 text-[13px] text-ink"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                {(row.providers?.length ? row.providers : ["duckduckgo"]).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
          )}
          {row.id === "cn_registry" && (
            <label className="block text-[12px] text-muted">
              {t("Service base URL")}
              <input
                className="mt-1 w-full rounded-lg border border-line bg-paper px-2.5 py-1.5 text-[13px] text-ink"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://…"
                autoComplete="off"
              />
            </label>
          )}
          <label className="block text-[12px] text-muted">
            {row.id === "cn_registry" ? t("Optional API key") : t("API key")}
            <input
              type="password"
              className="mt-1 w-full rounded-lg border border-line bg-paper px-2.5 py-1.5 text-[13px] text-ink"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                row.has_api_key
                  ? t("Leave blank to keep the current key")
                  : undefined
              }
              autoComplete="off"
            />
          </label>
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="button"
              disabled={busy}
              className="px-3 py-1.5 rounded-lg text-[12.5px] bg-accent text-white disabled:opacity-50"
              onClick={() => void save(false)}
            >
              {t("Save")}
            </button>
            {row.has_api_key && (
              <button
                type="button"
                disabled={busy}
                className="px-3 py-1.5 rounded-lg text-[12.5px] border border-line text-muted hover:text-ink disabled:opacity-50"
                onClick={() => void save(true)}
              >
                {t("Clear saved API key")}
              </button>
            )}
          </div>
          {msg && <p className="text-[12px] text-accent">{msg}</p>}
          {err && <p className="text-[12px] text-red-600">{err}</p>}
        </div>
      )}
    </article>
  );
}

export function PublicApiLookupsSection() {
  const { t, locale } = useI18n();
  const localeZh = locale === "zh-CN";
  const [rows, setRows] = useState<PublicApiLookup[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    listPublicApiLookups()
      .then((list) => {
        setRows(list);
        setError(null);
      })
      .catch(() => {
        setError(t("Could not load public API lookups."));
        setRows([]);
      });
  }, [t]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (rows == null) {
    return (
      <p className="text-[13px] text-muted" data-testid="public-api-lookups-loading">
        {t("Loading public API lookups…")}
      </p>
    );
  }
  if (error) {
    return <p className="text-[13px] text-red-600">{error}</p>;
  }

  return (
    <div className="space-y-3" data-testid="public-api-lookups">
      {rows.map((row) => (
        <LookupCard
          key={row.id}
          row={row}
          localeZh={localeZh}
          onSaved={reload}
        />
      ))}
    </div>
  );
}
