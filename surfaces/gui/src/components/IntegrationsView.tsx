import { useEffect, useState } from "react";
import { getConnectors } from "../api";
import { McpTab } from "./ManageTabs";
import { ConnectorsSection } from "./connectors/ConnectorsSection";
import { PublicApiLookupsSection } from "./PublicApiLookupsSection";
import { Icon } from "./Icon";
import { useI18n } from "../i18n";

// Connectors · MCP · API public lookups. Messaging routing lives under Inbox.
type IntTab = "connectors" | "mcp" | "public-api-lookups";

const INT_TABS: {
  key: IntTab;
  label: "Connectors" | "MCP servers" | "API public lookups";
  icon: "plug" | "code" | "search";
}[] = [
  { key: "connectors", label: "Connectors", icon: "plug" },
  { key: "mcp", label: "MCP servers", icon: "code" },
  { key: "public-api-lookups", label: "API public lookups", icon: "search" },
];

export function IntegrationsView() {
  const { t } = useI18n();
  const [tab, setTab] = useState<IntTab>("connectors");
  const [connCount, setConnCount] = useState<number | null>(null);

  useEffect(() => {
    const load = () => {
      getConnectors().then((cs) => setConnCount(cs.length)).catch(() => {});
    };
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <main className="flex-1 min-w-0 flex bg-paper">
      <nav className="page-subnav w-[208px] shrink-0 border-r border-line bg-panel/40 px-3 py-4">
        <div className="px-2 text-[13.5px] font-semibold mb-3 flex items-center gap-2">
          <Icon name="plug" size={16} /> {t("Connectors")}
        </div>
        {INT_TABS.map((tabItem) => {
          const active = tab === tabItem.key;
          return (
            <button
              key={tabItem.key}
              className={
                "w-full text-left px-2.5 py-2 rounded-lg text-[13px] flex items-center justify-between " +
                (active
                  ? "bg-paper text-accent font-medium"
                  : "text-muted hover:bg-paper hover:text-ink")
              }
              onClick={() => setTab(tabItem.key)}
            >
              <span className="flex items-center gap-2 min-w-0">
                <Icon name={tabItem.icon} size={15} /> {t(tabItem.label)}
              </span>
              {tabItem.key === "connectors" && connCount != null && (
                <span className={"text-[11px] shrink-0 " + (active ? "text-accent" : "text-faint")}>
                  {connCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="flex-1 min-w-0 overflow-y-auto hairline-scroll">
        <div className="max-w-4xl mx-auto px-7 py-6">
          {tab === "connectors" ? (
            <section>
              <PanelHead
                title={t("Connectors")}
                sub={t("Apps and tools your coworkers can use. Connected ones come first.")}
              />
              <ConnectorsSection />
            </section>
          ) : tab === "mcp" ? (
            <section>
              <PanelHead
                title={t("MCP servers")}
                sub={t("External tool servers (stdio or HTTP), shared across all agents.")}
              />
              <McpTab />
            </section>
          ) : (
            <section>
              <PanelHead
                title={t("API public lookups")}
                sub={t("Built-in read-only Providers used by Skills and Agents. Free ones need no key; others you configure here.")}
              />
              <PublicApiLookupsSection />
            </section>
          )}
        </div>
      </div>
    </main>
  );
}

export function PanelHead({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-[18px] font-semibold tracking-tight">{title}</h2>
      <p className="text-[12.5px] text-muted mt-0.5">{sub}</p>
    </div>
  );
}
