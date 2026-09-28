import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { McpTab } from "./ManageTabs";
import { LocaleProvider } from "../i18n";
import { getMcpServers } from "../api";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    getMcpServers: vi.fn(async () => [
      {
        name: "chem-data-hub",
        enabled: true,
        transport: "http",
        requires_approval: true,
        status: "configured",
        tool_count: null,
        builtin: false,
        config: { headers: { Authorization: "***" } },
      },
    ]),
    patchMcpServer: vi.fn(),
    deleteMcpServer: vi.fn(),
    reloadMcp: vi.fn(),
    addMcpServer: vi.fn(),
    connectMcp: vi.fn(),
    getMcpTools: vi.fn(),
    signoutMcp: vi.fn(),
  };
});

describe("McpTab user-added row", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows remove for user-managed servers", async () => {
    render(
      <LocaleProvider>
        <McpTab />
      </LocaleProvider>,
    );
    expect(await screen.findByText("chem-data-hub")).toBeTruthy();
    expect(screen.queryByTestId("mcp-builtin-badge")).toBeNull();
    expect(screen.getByRole("button", { name: /remove|删除|移除/i })).toBeTruthy();
  });

  it("refreshes a background connection until its tools are available", async () => {
    const row = { name: "slow", enabled: true, transport: "http", requires_approval: true,
      status: "connecting", tool_count: null, config: {} };
    vi.mocked(getMcpServers).mockResolvedValueOnce([row]).mockResolvedValueOnce([
      { ...row, status: "connected", tool_count: 2 },
    ]);
    let poll: (() => void) | undefined;
    const timer = vi.spyOn(window, "setInterval").mockImplementation((callback) => {
      poll = callback as () => void;
      return 123;
    });
    const view = render(<LocaleProvider><McpTab /></LocaleProvider>);
    try {
      expect(await screen.findByText(/http · (connecting|正在连接)/)).toBeTruthy();
      expect(poll).toBeDefined();
      await act(async () => { await poll?.(); });
      expect(await screen.findByText(/http · .*2 (tools|个工具)/)).toBeTruthy();
    } finally {
      view.unmount();
      timer.mockRestore();
    }
  });
});
