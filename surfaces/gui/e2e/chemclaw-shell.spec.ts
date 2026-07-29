import { expect, test } from "./fixtures";

test("ChemClaw boots in Chinese and keeps a selected English shell after reload", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText(/^ChemClaw/).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "新建对话" })).toBeVisible();
  await expect(page.getByText("最近对话", { exact: true })).toBeVisible();
  await expect(page.getByPlaceholder("向 ChemClaw 提问…（可拖放或粘贴文件）")).toBeVisible();
  await expect(page.getByRole("button", { name: "添加附件" })).toBeVisible();
  await expect(page.getByRole("button", { name: "模式" })).toBeVisible();
  await expect(page.getByRole("button", { name: "发送" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("OpenWorker");

  await page.getByTestId("account-row").click();
  await expect(page.getByTestId("account-menu")).not.toContainText("OpenWorker");
  await page.getByTestId("account-menu").getByRole("button", { name: "设置" }).click();
  await page.getByRole("button", { name: "通用" }).click();
  await expect(page.locator("main")).not.toContainText("OpenWorker");
  await page.getByRole("button", { name: "重新运行设置" }).click();
  await expect(page.getByTestId("onboarding")).toBeVisible();
  await expect(page.getByTestId("onboarding")).not.toContainText("OpenWorker");
  await page.getByRole("button", { name: "Skip setup" }).click();
  await page.getByRole("button", { name: "skip anyway" }).click();

  await page.getByTestId("account-row").click();
  await page.getByTestId("account-menu").getByRole("button", { name: "设置" }).click();
  await page.getByRole("button", { name: "通用" }).click();
  await page.getByLabel("语言").selectOption("en-US");

  await expect(page.getByRole("button", { name: "New conversation" })).toBeVisible();
  await expect(page.getByText("Recent", { exact: true })).toBeVisible();

  await page.reload();

  await expect(page.getByRole("button", { name: "New conversation" })).toBeVisible();
  await expect(page.getByText("Recent", { exact: true })).toBeVisible();
});
