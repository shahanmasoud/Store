import { expect, test, type Page } from "@playwright/test";

const browserErrors = new WeakMap<Page, string[]>();

test.beforeEach(async ({ context, page }) => {
  const errors: string[] = [];
  browserErrors.set(page, errors);
  page.on("pageerror", (error) => errors.push(`pageerror:${error.name}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console:${message.text()}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 500) errors.push(`http:${response.status()}:${new URL(response.url()).pathname}`);
  });
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname !== "127.0.0.1" || !["5193", "8013"].includes(url.port)) {
      throw new Error(`E2E network isolation rejected external request: ${url.origin}`);
    }
    await route.continue();
  });
});

test.afterEach(async ({ page }) => {
  expect(browserErrors.get(page) ?? [], "مرورگر نباید خطای JavaScript، console یا HTTP 5xx داشته باشد").toEqual([]);
});

async function expectNoHorizontalOverflow(page: Page) {
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
}

async function login(page: Page) {
  await page.goto("/admin");
  await page.getByLabel("نام کاربری").fill("e2e-admin");
  await page.getByLabel("رمز عبور", { exact: true }).fill("e2e-password-123");
  await page.getByRole("button", { name: "ورود به داشبورد" }).click();
  await expect(page.getByRole("heading", { name: "خانه مدیریت", exact: true })).toBeVisible();
}

async function navigate(page: Page, name: string, heading: string, mobile: boolean) {
  if (mobile) {
    await page.getByRole("button", { name: "باز کردن منوی بخش‌های مدیریت" }).click();
    await expect(page.getByRole("navigation", { name: "بخش‌های پنل مدیریت" }).last()).toBeVisible();
  }
  await page.getByRole("button", { name, exact: true }).last().click();
  await expect(page.getByRole("heading", { name: heading, exact: true, level: 1 })).toBeVisible();
  await expectNoHorizontalOverflow(page);
}

test("ورود مدیر و ناوبری صفحات کلیدی بدون overflow افقی", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  await login(page);
  await expectNoHorizontalOverflow(page);

  await navigate(page, "کالاها", "کالاها و قیمت‌ها", mobile);
  await navigate(page, "انبار", "مدیریت انبار", mobile);
  await navigate(page, "چک‌ها", "مدیریت چک‌ها", mobile);
});

test("dialog ویرایش کاربر در موبایل تمام‌صفحه و قابل لمس است", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith("mobile"), "این سناریو مخصوص viewport موبایل است.");
  await login(page);
  await page.getByRole("button", { name: "باز کردن منوی بخش‌های مدیریت" }).click();
  await page.getByRole("button", { name: "کاربران و دسترسی‌ها", exact: true }).last().click();
  await expect(page.getByRole("heading", { name: "کاربران و دسترسی‌ها", exact: true, level: 1 })).toBeVisible();
  const operatorCard = page.locator(".admin-user-card").filter({ hasText: "@e2e-operator" });
  await operatorCard.getByRole("button", { name: "ویرایش", exact: true }).click();

  const dialog = page.getByRole("dialog", { name: "ویرایش e2e-operator" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveClass(/MuiDialog-paperFullScreen/);
  await expect(dialog.getByLabel("نام و نام خانوادگی")).toBeVisible();
  const submit = dialog.getByRole("button", { name: "ذخیره", exact: true });
  await expect(submit).toBeVisible();
  await expectNoHorizontalOverflow(page);

  const bounds = await dialog.boundingBox();
  const submitBounds = await submit.boundingBox();
  expect(bounds).not.toBeNull();
  expect(submitBounds).not.toBeNull();
  expect(bounds!.x).toBe(0);
  expect(bounds!.y).toBe(0);
  expect(bounds!.width).toBe(390);
  expect(bounds!.height).toBe(844);
  expect(submitBounds!.height).toBeGreaterThanOrEqual(44);
});
