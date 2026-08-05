import { describe, expect, it } from "vitest";
import { rankSlashSkills, scoreSlashSkill } from "./slashSkillMatch";

const price = {
  name: "chem-price-daily",
  description: "行情服务工具。按品种分区域自动生成价格日报/周报，含涨跌与样本量。",
};
const supplier = {
  name: "chem-supplier-match",
  description: "根据询单匹配合适的供应商与报价渠道。",
};
const pdf = {
  name: "pdf",
  description: "Comprehensive PDF manipulation toolkit for extracting text and tables.",
};
const greet = {
  name: "greet",
  description: "says hello",
};

describe("scoreSlashSkill", () => {
  it("scores a Chinese description substring highest", () => {
    expect(scoreSlashSkill(price, "价格")).toBe(100);
    expect(scoreSlashSkill(price, "日报")).toBe(100);
  });

  it("scores a description char subsequence below continuous substring", () => {
    expect(scoreSlashSkill(price, "价报")).toBe(60);
  });

  it("still scores English name prefix / substring", () => {
    expect(scoreSlashSkill(price, "chem-pri")).toBe(50);
    expect(scoreSlashSkill(price, "price")).toBe(30);
    // "pdf" also appears in the description → description substring wins (100).
    expect(scoreSlashSkill(pdf, "pdf")).toBe(100);
    expect(scoreSlashSkill(greet, "gre")).toBe(50);
  });

  it("returns 0 when nothing matches", () => {
    expect(scoreSlashSkill(greet, "价格")).toBe(0);
  });
});

describe("rankSlashSkills", () => {
  const menu = [greet, supplier, price, pdf];

  it("keeps all skills in original order when the query is empty", () => {
    expect(rankSlashSkills(menu, "").map((s) => s.name)).toEqual([
      "greet",
      "chem-supplier-match",
      "chem-price-daily",
      "pdf",
    ]);
  });

  it("ranks Chinese description hits above unrelated skills", () => {
    expect(rankSlashSkills(menu, "价格").map((s) => s.name)).toEqual(["chem-price-daily"]);
    expect(rankSlashSkills(menu, "供应商")[0]?.name).toBe("chem-supplier-match");
  });

  it("still finds skills by English name fragment", () => {
    expect(rankSlashSkills(menu, "chem-pri").map((s) => s.name)).toEqual(["chem-price-daily"]);
    expect(rankSlashSkills(menu, "pdf").map((s) => s.name)[0]).toBe("pdf");
  });

  it("prefers description substring over name-only when both match different skills", () => {
    const mixed = [
      { name: "price-tool", description: "unrelated helper" },
      price,
    ];
    expect(rankSlashSkills(mixed, "价格")[0]?.name).toBe("chem-price-daily");
  });
});
