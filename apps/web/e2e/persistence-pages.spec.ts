import { expect, test } from "@playwright/test";

test("fixture-backed persisted analysis pages render", async ({ page }) => {
  await page.goto("/analyses");
  await expect(
    page.getByRole("heading", { name: "Analysis history" }),
  ).toBeVisible();
  await expect(page.getByText("Portable Rechargeable Desk Lamp")).toBeVisible();

  await page.getByRole("link", { name: "Open" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Portable Rechargeable Desk Lamp",
      level: 1,
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Providers" }).click();
  await expect(
    page.getByRole("columnheader", { name: "Provider" }),
  ).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: "Operation" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Json" }).click();
  await expect(
    page.getByRole("heading", { name: "JSON export" }),
  ).toBeVisible();
});

test("fixture-backed admin inspector shows disabled state safely", async ({
  page,
}) => {
  await page.goto("/admin/db");
  await expect(
    page.getByRole("heading", { name: "Database inspector" }),
  ).toBeVisible();
  await expect(page.getByText(/Development database inspector/i)).toBeVisible();
});
