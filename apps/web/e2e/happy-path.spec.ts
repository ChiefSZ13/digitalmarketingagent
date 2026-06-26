import { expect, type Page, test } from "@playwright/test";

const tinyPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=",
  "base64",
);

async function submitFixtureAnalysis(page: Page) {
  await page.getByLabel("Product images").setInputFiles({
    name: "lamp.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  await page
    .getByLabel("Product description")
    .fill("Portable rechargeable desk lamp");
  await page.getByRole("button", { name: "Analyze" }).click();
  await expect(
    page.getByText("Portable Rechargeable Desk Lamp").first(),
  ).toBeVisible();
}

async function expectPageToFitViewport(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
}

test("fixture-backed analysis flow", async ({ page }) => {
  await page.goto("/");
  await submitFixtureAnalysis(page);
  await expectPageToFitViewport(page);
  await expect(
    page.getByRole("heading", { name: "Marketplace Snapshot" }),
  ).toBeVisible();
  await expect(page.getByText("Amazon").first()).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Official matches" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Official alternate variants" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Licensed third-party alternatives" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Other compatible alternatives" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Needs review" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rejected" })).toBeVisible();
  await expect(
    page.getByText("Replacement charger for Portable Rechargeable Desk Lamp", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator("table").first()).not.toContainText(
    "Replacement charger",
  );
  await page.getByRole("button", { name: /accept as official match/i }).click();
  await expect(
    page.getByText(/Local review override: Official Match/i),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: /^Category$/ })
    .selectOption("negative");
  await expect(
    page.getByRole("cell", { name: "cheap Portable Rechargeable Desk Lamp" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /inspect/i }).click();
  await expect(
    page.getByText(
      "Negative keyword candidate to avoid low-intent bargain traffic.",
      { exact: true },
    ),
  ).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /download/i }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain("run_fixture_portable_lamp");
});

test("fixture-backed results fit a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await submitFixtureAnalysis(page);
  await expectPageToFitViewport(page);
  await page
    .getByRole("button", { name: /inspect/i })
    .first()
    .click();
  await expectPageToFitViewport(page);
  await expect(page.getByText("Keyword").first()).toBeVisible();
});
