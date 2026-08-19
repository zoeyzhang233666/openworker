import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { McpTab } from "./ManageTabs";
import { LocaleProvider } from "../i18n";

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
        builtin: true,
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

describe("McpTab builtin row", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows builtin badge and hides remove", async () => {
    render(
      <LocaleProvider>
        <McpTab />
      </LocaleProvider>,
    );
    expect(await screen.findByTestId("mcp-builtin-chem-data-hub")).toBeTruthy();
    expect(screen.getByTestId("mcp-builtin-badge").textContent).toMatch(/内置|Built-in/);
    expect(screen.queryByRole("button", { name: /remove|删除|移除/i })).toBeNull();
  });
});
