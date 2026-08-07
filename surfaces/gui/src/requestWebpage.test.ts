import { describe, expect, it } from "vitest";
import { webpageAlignIntentMessage } from "./requestWebpage";

describe("webpageAlignIntentMessage", () => {
  it("includes title and path for align-then-generate", () => {
    const msg = webpageAlignIntentMessage("乙烯", "reports/乙烯.md");
    expect(msg).toContain("《乙烯》");
    expect(msg).toContain("reports/乙烯.md");
    expect(msg).toContain("先与我对齐网页细节再生成网页版");
  });

  it("falls back when title/path empty", () => {
    const msg = webpageAlignIntentMessage("", "");
    expect(msg).toContain("《报告》");
    expect(msg).toContain("report.md");
  });
});
