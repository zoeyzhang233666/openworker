// Start-screen template tasks for ChemClaw (cowork): three chemical knowledge-work rows
// (research memo / price brief / local folder). No HubSpot / GitHub+Slack connector gates (D-080).
import { expect } from "@playwright/test";
import { test } from "./fixtures";

test("three ChemClaw starter rows; memo and price prefill the composer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("chat-with-agent")).toBeVisible();
  await expect(page.getByTestId("chat-with-agent")).toContainText(/Chatting with/i);

  await expect(page.getByTestId("intro-tasks-cowork")).toBeVisible();
  await expect(page.locator(".task-card")).toHaveCount(3);
  await expect(page.getByText("Set me up (optional)")).toHaveCount(0);
  await expect(page.getByTestId("intro-task-hubspot")).toHaveCount(0);
  await expect(page.getByTestId("intro-task-github-slack")).toHaveCount(0);

  const memo = page.getByTestId("intro-task-memo");
  await expect(memo).toContainText("Draft a chemical-topic research memo");
  await expect(memo).toContainText("Start →");
  await memo.click();
  await expect(page.getByPlaceholder(/Ask the coworker/)).toHaveValue(/research memo/i);

  const price = page.getByTestId("intro-task-price");
  await expect(price).toContainText("Look up recent prices");
  await price.click();
  await expect(page.getByPlaceholder(/Ask the coworker/)).toHaveValue(/recent prices/i);
});

test("folder task opens the inline add-folder form; adding a folder prefills the composer", async ({
  page,
}) => {
  await page.goto("/");

  // No shared folder yet (the fixture root is the primary scratch) → the row expands the form.
  await page.getByTestId("intro-task-folder").click();
  const path = page.getByPlaceholder("Choose or paste a folder path…");
  await expect(path).toBeVisible();
  await path.fill("/Users/me/Reports");
  await page.getByRole("button", { name: "Add", exact: true }).click();

  await expect(page.getByPlaceholder(/Ask the coworker/)).toHaveValue(
    /read the materials in this folder/i,
  );
});
