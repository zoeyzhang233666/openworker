import { useMemo, useState } from "react";
import { useI18n } from "../i18n";

export type LeadRow = {
  company: string;
  customer_type?: string;
  fit_score?: number | string | null;
  evidence_confidence?: number | string | null;
  match_reason?: string;
  next_action?: string;
  sales_status: string;
  notes?: string;
  exclude_reason?: string;
};

type LeadListDoc = {
  list_id?: string;
  title?: string;
  sku_summary?: string;
  market_summary?: string;
  leads: LeadRow[];
};

const STORAGE_KEY = "chemclaw.leadList.v1";

function loadStored(): LeadListDoc {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { title: "客户清单", leads: [] };
    const parsed = JSON.parse(raw) as LeadListDoc;
    if (!parsed || !Array.isArray(parsed.leads)) return { title: "客户清单", leads: [] };
    return parsed;
  } catch {
    return { title: "客户清单", leads: [] };
  }
}

function toCsv(leads: LeadRow[]): string {
  const headers = [
    "company",
    "customer_type",
    "fit_score",
    "evidence_confidence",
    "match_reason",
    "next_action",
    "sales_status",
    "notes",
    "exclude_reason",
  ];
  const esc = (v: unknown) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [headers.join(",")];
  for (const row of leads) {
    lines.push(headers.map((h) => esc((row as Record<string, unknown>)[h])).join(","));
  }
  return lines.join("\n") + "\n";
}

export function LeadsWorkbench() {
  const { t } = useI18n();
  const [doc, setDoc] = useState<LeadListDoc>(() => loadStored());
  const [importError, setImportError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "contactable" | "needs_review" | "excluded">(
    "all",
  );

  const counts = useMemo(() => {
    let contactable = 0;
    let needs_review = 0;
    let excluded = 0;
    for (const lead of doc.leads) {
      if (lead.sales_status === "excluded") excluded += 1;
      else if (
        lead.sales_status === "contactable" ||
        lead.sales_status === "contacted" ||
        lead.sales_status === "replied" ||
        lead.sales_status === "opportunity"
      ) {
        contactable += 1;
      } else needs_review += 1;
    }
    return { contactable, needs_review, excluded, total: doc.leads.length };
  }, [doc.leads]);

  const visible = useMemo(() => {
    return doc.leads.filter((lead) => {
      if (filter === "all") return true;
      if (filter === "excluded") return lead.sales_status === "excluded";
      if (filter === "contactable") {
        return ["contactable", "contacted", "replied", "opportunity"].includes(
          lead.sales_status,
        );
      }
      return ["new", "needs_review"].includes(lead.sales_status);
    });
  }, [doc.leads, filter]);

  const persist = (next: LeadListDoc) => {
    setDoc(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const onImportFile = async (file: File) => {
    setImportError(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as LeadListDoc;
      if (!parsed || !Array.isArray(parsed.leads)) {
        setImportError(t("leads.importInvalid"));
        return;
      }
      for (const lead of parsed.leads) {
        if (!lead?.company || !lead?.sales_status) {
          setImportError(t("leads.importInvalid"));
          return;
        }
      }
      persist({
        list_id: parsed.list_id || "imported",
        title: parsed.title || t("leads.title"),
        sku_summary: parsed.sku_summary || "",
        market_summary: parsed.market_summary || "",
        leads: parsed.leads,
      });
    } catch {
      setImportError(t("leads.importInvalid"));
    }
  };

  const exportCsv = () => {
    const blob = new Blob([toCsv(doc.leads)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.list_id || "lead-list"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const setStatus = (index: number, sales_status: string) => {
    const leads = doc.leads.map((lead, i) =>
      i === index
        ? {
            ...lead,
            sales_status,
            exclude_reason:
              sales_status === "excluded"
                ? lead.exclude_reason || t("leads.defaultExcludeReason")
                : lead.exclude_reason,
          }
        : lead,
    );
    persist({ ...doc, leads });
  };

  const setNote = (index: number, notes: string) => {
    const leads = doc.leads.map((lead, i) => (i === index ? { ...lead, notes } : lead));
    persist({ ...doc, leads });
  };

  return (
    <div className="flex-1 min-h-0 overflow-auto p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-[20px] font-semibold mb-1">{t("leads.title")}</h1>
        <p className="text-[13px] text-inkMuted mb-4">{t("leads.subtitle")}</p>

        <div className="flex flex-wrap gap-2 mb-4 items-center">
          <label className="text-[12.5px] px-3 py-2 rounded-lg border border-line bg-paper cursor-pointer hover:border-lineStrong">
            {t("leads.importJson")}
            <input
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void onImportFile(f);
                e.target.value = "";
              }}
            />
          </label>
          <button
            type="button"
            className="text-[12.5px] px-3 py-2 rounded-lg bg-accent text-white disabled:opacity-40"
            disabled={doc.leads.length === 0}
            onClick={exportCsv}
          >
            {t("leads.exportCsv")}
          </button>
          <span className="text-[12px] text-inkMuted">
            {t("leads.counts", {
              contactable: counts.contactable,
              needsReview: counts.needs_review,
              excluded: counts.excluded,
              total: counts.total,
            })}
          </span>
        </div>

        {importError ? (
          <div className="text-[12.5px] text-red-700 mb-3">{importError}</div>
        ) : null}

        <div className="flex gap-2 mb-3">
          {(
            [
              ["all", "leads.filterAll"],
              ["contactable", "leads.filterContactable"],
              ["needs_review", "leads.filterNeedsReview"],
              ["excluded", "leads.filterExcluded"],
            ] as const
          ).map(([id, key]) => (
            <button
              key={id}
              type="button"
              className={`text-[12px] px-2.5 py-1 rounded-lg border ${
                filter === id ? "border-accent text-accent" : "border-line text-inkMuted"
              }`}
              onClick={() => setFilter(id)}
            >
              {t(key)}
            </button>
          ))}
        </div>

        {visible.length === 0 ? (
          <div className="text-[13px] text-inkMuted border border-dashed border-line rounded-lg p-8">
            {t("leads.empty")}
          </div>
        ) : (
          <div className="overflow-x-auto border border-line rounded-lg">
            <table className="w-full text-[12.5px]">
              <thead className="bg-paper border-b border-line text-left">
                <tr>
                  <th className="p-2 font-medium">{t("leads.col.company")}</th>
                  <th className="p-2 font-medium">{t("leads.col.type")}</th>
                  <th className="p-2 font-medium">{t("leads.col.fit")}</th>
                  <th className="p-2 font-medium">{t("leads.col.conf")}</th>
                  <th className="p-2 font-medium">{t("leads.col.next")}</th>
                  <th className="p-2 font-medium">{t("leads.col.status")}</th>
                  <th className="p-2 font-medium">{t("leads.col.notes")}</th>
                  <th className="p-2 font-medium">{t("leads.col.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((lead) => {
                  const index = doc.leads.indexOf(lead);
                  return (
                    <tr key={`${lead.company}-${index}`} className="border-b border-line/70">
                      <td className="p-2 align-top">{lead.company}</td>
                      <td className="p-2 align-top">{lead.customer_type || "—"}</td>
                      <td className="p-2 align-top">{lead.fit_score ?? "—"}</td>
                      <td className="p-2 align-top">{lead.evidence_confidence ?? "—"}</td>
                      <td className="p-2 align-top max-w-[14rem]">{lead.next_action || "—"}</td>
                      <td className="p-2 align-top">{lead.sales_status}</td>
                      <td className="p-2 align-top">
                        <input
                          className="w-full min-w-[8rem] border border-line rounded px-1.5 py-1 bg-transparent"
                          value={lead.notes || ""}
                          onChange={(e) => setNote(index, e.target.value)}
                          aria-label={t("leads.col.notes")}
                        />
                      </td>
                      <td className="p-2 align-top whitespace-nowrap">
                        <button
                          type="button"
                          className="text-accent mr-2 disabled:opacity-40"
                          disabled={lead.sales_status === "contactable"}
                          onClick={() => setStatus(index, "contactable")}
                        >
                          {t("leads.markContactable")}
                        </button>
                        <button
                          type="button"
                          className="text-inkMuted mr-2"
                          onClick={() => setStatus(index, "needs_review")}
                        >
                          {t("leads.markNeedsReview")}
                        </button>
                        <button
                          type="button"
                          className="text-red-700"
                          onClick={() => setStatus(index, "excluded")}
                        >
                          {t("leads.markExcluded")}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-[11.5px] text-inkMuted mt-4">{t("leads.footer")}</p>
      </div>
    </div>
  );
}
