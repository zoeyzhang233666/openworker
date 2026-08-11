import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, fireEvent } from "@testing-library/react";
import { PublicApiLookupsSection } from "./PublicApiLookupsSection";
import { LocaleProvider } from "../i18n";

vi.mock("../api", () => ({
  listPublicApiLookups: vi.fn(),
  setPublicApiLookup: vi.fn(),
}));

import { listPublicApiLookups, setPublicApiLookup } from "../api";

const listMock = listPublicApiLookups as unknown as ReturnType<typeof vi.fn>;
const setMock = setPublicApiLookup as unknown as ReturnType<typeof vi.fn>;

const samRow = {
  id: "sam",
  kind: "secret" as const,
  label_zh: "SAM.gov",
  label_en: "SAM.gov",
  tool: "search_sam_opportunities",
  summary_zh: "需密钥",
  summary_en: "needs key",
  purpose_zh: "检索美国联邦公开采购机会。",
  purpose_en: "Search US federal opportunities.",
  used_by_zh: "商机雷达龙虾",
  used_by_en: "Opportunity radar",
  setup_zh: "在 sam.gov 申请 Public API Key 后粘贴保存。",
  setup_en: "Request a Public API Key on sam.gov, then paste and save.",
  docs_url: "https://open.gsa.gov/api/get-opportunities-public-api/",
  signup_url: "https://sam.gov/",
  ready: false,
  configured: false,
  has_api_key: false,
};

describe("PublicApiLookupsSection", () => {
  beforeEach(() => {
    listMock.mockReset();
    setMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders free and secret cards from the catalog", async () => {
    listMock.mockResolvedValue([
      {
        id: "pubchem",
        kind: "free",
        label_zh: "PubChem 化学身份",
        label_en: "PubChem chemical identity",
        tool: "lookup_chemical_identity",
        summary_zh: "已内置",
        summary_en: "Built-in",
        purpose_zh: "查询化学身份。",
        purpose_en: "Chemical identity.",
        used_by_zh: "外贸拓客",
        used_by_en: "Export prospecting",
        setup_zh: "无需操作。",
        setup_en: "No setup.",
        docs_url: "https://pubchem.ncbi.nlm.nih.gov/",
        signup_url: "",
        ready: true,
        configured: true,
        has_api_key: false,
      },
      samRow,
    ]);

    render(
      <LocaleProvider>
        <PublicApiLookupsSection />
      </LocaleProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("public-api-lookup-pubchem")).toBeTruthy();
      expect(screen.getByTestId("public-api-lookup-sam")).toBeTruthy();
    });
    expect(screen.getByText(/PubChem/)).toBeTruthy();
    expect(screen.getByText("SAM.gov")).toBeTruthy();
    expect(screen.getByText("检索美国联邦公开采购机会。")).toBeTruthy();
  });

  it("shows SAM signup link and saves api key", async () => {
    listMock.mockResolvedValue([samRow]);
    setMock.mockResolvedValue({ ok: true, id: "sam" });

    render(
      <LocaleProvider>
        <PublicApiLookupsSection />
      </LocaleProvider>,
    );

    await waitFor(() => screen.getByTestId("public-api-lookup-sam"));
    const signup = screen.getByTestId("public-api-lookup-signup-sam") as HTMLAnchorElement;
    expect(signup.getAttribute("href")).toBe("https://sam.gov/");
    expect(screen.getByText("打开申请页")).toBeTruthy();

    const input = screen.getByTestId("public-api-lookup-sam").querySelector(
      'input[type="password"]',
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "sam-key-1" } });
    fireEvent.click(screen.getByText("保存"));

    await waitFor(() => {
      expect(setMock).toHaveBeenCalledWith("sam", { api_key: "sam-key-1" });
    });
  });
});
