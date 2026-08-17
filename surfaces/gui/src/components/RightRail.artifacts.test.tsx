import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { RightRail } from "./RightRail";
import { LocaleProvider } from "../i18n";

function stubFetch(routes: { match: string; method?: string; json: any }[]) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const method = (init?.method || "GET").toUpperCase();
    for (const r of routes) {
      if (url.includes(r.match) && (!r.method || r.method === method)) {
        return { ok: true, json: async () => r.json } as Response;
      }
    }
    return { ok: true, json: async () => ({}) } as Response;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("RightRail artifacts panel", () => {
  it("shows empty state when there are no previewable artifacts", async () => {
    const sessionId = "s-absent";
    stubFetch([
      {
        match: `/v1/sessions/${sessionId}/artifacts`,
        method: "GET",
        json: { artifacts: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/roots`,
        method: "GET",
        json: { roots: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/connections`,
        method: "GET",
        json: { connected: [], recommended: [], attention: 0 },
      },
      {
        match: `/v1/connectors`,
        method: "GET",
        json: [],
      },
    ]);

    render(
      <LocaleProvider>
        <RightRail
          active={true}
          sessionId={sessionId}
          refreshKey={0}
          toolNames={[]}
          todo={[]}
          running={false}
          onPreviewChange={() => {}}
        />
      </LocaleProvider>,
    );

    await screen.findByText("暂无可预览文件。");
    expect(screen.queryByText("查看任务进度")).toBeNull();
  });

  it("filters internal ._chemclaw artifacts and lists normal deliverables", async () => {
    const sessionId = "s-1";
    stubFetch([
      {
        match: `/v1/sessions/${sessionId}/artifacts`,
        method: "GET",
        json: {
          artifacts: [
            {
              path: "._chemclaw/outbound-clip/clip-1.txt",
              name: "clip-1.txt",
              kind: "text",
              size: 10,
              modified_at: 1,
            },
            {
              path: "normal.md",
              name: "normal.md",
              kind: "markdown",
              size: 10,
              modified_at: 1,
            },
          ],
        },
      },
      {
        match: `/v1/sessions/${sessionId}/roots`,
        method: "GET",
        json: { roots: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/connections`,
        method: "GET",
        json: { connected: [], recommended: [], attention: 0 },
      },
      {
        match: `/v1/connectors`,
        method: "GET",
        json: [],
      },
    ]);

    render(
      <LocaleProvider>
        <RightRail
          active={true}
          sessionId={sessionId}
          refreshKey={0}
          toolNames={[]}
          todo={[]}
          running={false}
          onPreviewChange={() => {}}
        />
      </LocaleProvider>,
    );

    await screen.findByText("normal.md");
    expect(screen.queryByText("clip-1.txt")).toBeNull();
    expect(screen.queryByText("查看任务进度")).toBeNull();
  });

  it("lists more than 16 deliverables instead of silently truncating", async () => {
    const sessionId = "s-many";
    const artifacts = Array.from({ length: 20 }, (_, i) => ({
      path: `report-${String(i + 1).padStart(2, "0")}.md`,
      name: `report-${String(i + 1).padStart(2, "0")}.md`,
      kind: "markdown",
      size: 10,
      modified_at: 20 - i,
    }));
    stubFetch([
      {
        match: `/v1/sessions/${sessionId}/artifacts`,
        method: "GET",
        json: { artifacts },
      },
      {
        match: `/v1/sessions/${sessionId}/roots`,
        method: "GET",
        json: { roots: [] },
      },
      {
        match: `/v1/sessions/${sessionId}/connections`,
        method: "GET",
        json: { connected: [], recommended: [], attention: 0 },
      },
      {
        match: `/v1/connectors`,
        method: "GET",
        json: [],
      },
    ]);

    render(
      <LocaleProvider>
        <RightRail
          active={true}
          sessionId={sessionId}
          refreshKey={0}
          toolNames={[]}
          todo={[]}
          running={false}
          onPreviewChange={() => {}}
        />
      </LocaleProvider>,
    );

    await screen.findByText("report-01.md");
    expect(screen.getByText("report-17.md")).toBeTruthy();
    expect(screen.getByText("report-18.md")).toBeTruthy();
    expect(screen.getByText("report-19.md")).toBeTruthy();
    expect(screen.getByText("report-20.md")).toBeTruthy();
  });
});
