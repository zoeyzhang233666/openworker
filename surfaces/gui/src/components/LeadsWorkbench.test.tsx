import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { LocaleProvider } from "../i18n";
import { LeadsWorkbench } from "./LeadsWorkbench";
import { REQUEST_LEAD_FOLLOWUP_EVENT } from "../requestLeadFollowup";

afterEach(() => {
  cleanup();
  localStorage.clear();
});

function renderLeads() {
  return render(
    <LocaleProvider>
      <LeadsWorkbench />
    </LocaleProvider>,
  );
}

describe("LeadsWorkbench advanced UX (D-102)", () => {
  it("expands detail and dispatches research follow-up", async () => {
    const spy = vi.fn();
    window.addEventListener(REQUEST_LEAD_FOLLOWUP_EVENT, spy as EventListener);

    localStorage.setItem(
      "chemclaw.leadList.v1",
      JSON.stringify({
        title: "测试清单",
        run_id: "run-1",
        stage: "rank",
        budget: "3",
        sku_summary: "苯甲酸钠",
        leads: [
          {
            company: "示例化工",
            sales_status: "needs_review",
            match_reason: "SKU 匹配",
            key_evidence: "官网产品页",
            next_action: "补登记",
          },
        ],
      }),
    );

    renderLeads();

    expect(screen.getByTestId("leads-run-summary").textContent).toMatch(/run-1/);
    fireEvent.click(screen.getByTestId("leads-expand-0"));
    expect(screen.getByTestId("leads-detail-row-0").textContent).toContain("SKU 匹配");
    expect(screen.getByTestId("leads-detail-row-0").textContent).toContain("官网产品页");

    fireEvent.click(screen.getByTestId("leads-research-0"));
    expect(spy).toHaveBeenCalled();
    const detail = (spy.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.kind).toBe("research");
    expect(detail.company).toBe("示例化工");

    fireEvent.click(screen.getByTestId("leads-rescore"));
    const rescore = (spy.mock.calls[1][0] as CustomEvent).detail;
    expect(rescore.kind).toBe("rescore");
    expect(rescore.skuSummary).toBe("苯甲酸钠");

    expect(screen.queryByRole("button", { name: /发送|Send email/i })).toBeNull();
    window.removeEventListener(REQUEST_LEAD_FOLLOWUP_EVENT, spy as EventListener);
  });

  it("hides run summary when checkpoint fields are absent", () => {
    localStorage.setItem(
      "chemclaw.leadList.v1",
      JSON.stringify({
        leads: [{ company: "A", sales_status: "contactable" }],
      }),
    );
    renderLeads();
    expect(screen.queryByTestId("leads-run-summary")).toBeNull();
  });
});
