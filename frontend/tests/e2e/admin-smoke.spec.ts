import { expect, test, type Locator, type Page } from "@playwright/test";

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

async function expectNoElementOverflow(locator: Locator) {
  await expect.poll(() => locator.evaluate((element) => element.scrollWidth - element.clientWidth)).toBeLessThanOrEqual(1);
}

async function login(page: Page) {
  await loginAs(page, "e2e-admin", "e2e-password-123");
}

async function loginAs(page: Page, username: string, password: string) {
  await page.goto("/admin");
  await page.getByLabel("نام کاربری").fill(username);
  await page.getByLabel("رمز عبور", { exact: true }).fill(password);
  await page.getByRole("button", { name: "ورود به داشبورد" }).click();
  await expect(page.getByRole("heading", { name: "خانه مدیریت", exact: true })).toBeVisible();
}

async function openRoleNavigation(page: Page, mobile: boolean) {
  if (mobile) {
    await page.getByRole("button", { name: "باز کردن منوی بخش‌های مدیریت" }).click();
  }
  const navigation = page.getByRole("navigation", { name: "بخش‌های پنل مدیریت" }).last();
  await expect(navigation).toBeVisible();
  return navigation;
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

async function chooseOption(page: Page, fieldName: string, optionName: string, scope: Locator = page.locator("body")) {
  await scope.getByLabel(fieldName, { exact: true }).click();
  await page.getByRole("option", { name: optionName, exact: true }).click();
}

function projectSuffix(projectName: string) {
  return projectName.startsWith("mobile") ? "موبایل" : "دسکتاپ";
}

const roleNavigationItems = [
  ["خانه مدیریت", "خانه مدیریت"],
  ["یادآوری‌های سررسید", "یادآوری‌های سررسید"],
  ["فروش", "ثبت فروش"],
  ["کالاها", "کالاها و قیمت‌ها"],
  ["خرید", "ثبت خرید"],
  ["انبار", "مدیریت انبار"],
  ["دفتر حساب", "دفتر حساب"],
  ["چک‌ها", "مدیریت چک‌ها"],
  ["گزارش‌ها", "گزارش‌ها"],
  ["اتصال آنلاین", "سفارش‌های آنلاین"],
  ["کاربران و دسترسی‌ها", "کاربران و دسترسی‌ها"],
] as const;

const roleMatrix = [
  { username: "e2e-sales", allowed: ["خانه مدیریت", "یادآوری‌های سررسید", "فروش"], visit: "فروش" },
  { username: "e2e-catalog", allowed: ["خانه مدیریت", "کالاها", "خرید", "انبار"], visit: "کالاها" },
  { username: "e2e-ledger", allowed: ["خانه مدیریت", "یادآوری‌های سررسید", "دفتر حساب"], visit: "دفتر حساب" },
  { username: "e2e-reports", allowed: ["خانه مدیریت", "یادآوری‌های سررسید", "چک‌ها", "گزارش‌ها"], visit: "گزارش‌ها" },
  { username: "e2e-admin", allowed: roleNavigationItems.map(([name]) => name), visit: "کاربران و دسترسی‌ها" },
] satisfies Array<{ username: string; allowed: readonly string[]; visit: string }>;

test("ماتریس پنج نقش فقط منوهای مجاز را در پنل نشان می‌دهد", async ({ page }, testInfo) => {
  test.setTimeout(60_000);
  const mobile = testInfo.project.name.startsWith("mobile");

  for (const role of roleMatrix) {
    const password = role.username === "e2e-admin" ? "e2e-password-123" : "e2e-role-password";
    await loginAs(page, role.username, password);
    const navigation = await openRoleNavigation(page, mobile);

    for (const [name] of roleNavigationItems) {
      const item = navigation.getByRole("button", { name, exact: true });
      if (role.allowed.includes(name)) {
        await expect(item, `${role.username} باید منوی ${name} را ببیند`).toBeVisible();
      } else {
        await expect(item, `${role.username} نباید منوی ${name} را داشته باشد`).toHaveCount(0);
      }
    }

    const [, heading] = roleNavigationItems.find(([name]) => name === role.visit)!;
    await navigation.getByRole("button", { name: role.visit, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading, exact: true, level: 1 })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.getByRole("button", { name: "خروج", exact: true }).click();
    await expect(page.getByRole("heading", { name: "ورود مدیر", exact: true })).toBeVisible();
  }
});

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

test("ایجاد مشتری، اعتبارسنجی مشخصات و مشاهده popup مانده حساب", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  const suffix = projectSuffix(testInfo.project.name);
  const customerName = `مشتری E2E ${suffix}`;
  const customerNote = `توضیح تست تجربه کاربری ${suffix}`;

  await login(page);
  await navigate(page, "دفتر حساب", "دفتر حساب", mobile);
  await page.getByRole("button", { name: "شخص جدید", exact: true }).click();

  const dialog = page.getByRole("dialog").filter({ has: page.getByRole("heading", { name: "ثبت شخص جدید" }) });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "ثبت شخص", exact: true })).toBeDisabled();
  await dialog.getByLabel("نام شخص").fill(customerName);
  await dialog.getByLabel("شماره تماس (اختیاری)", { exact: true }).fill("۰۹۱۲۱۲۳۴۵۶۷");
  await chooseOption(page, "وضعیت خوش‌حسابی", "نیازمند توجه", dialog);
  await dialog.getByLabel("توضیحات (اختیاری)", { exact: true }).fill(customerNote);
  await dialog.getByRole("button", { name: "ثبت شخص", exact: true }).click();
  await expect(page.getByText("شخص جدید ثبت شد.", { exact: true })).toBeVisible();

  const customer = page.locator(".ledger-person-item").filter({ hasText: customerName });
  await expect(customer).toContainText("۰۹۱۲۱۲۳۴۵۶۷");
  await expect(customer).toContainText("نیازمند توجه");
  await customer.click();

  const summary = page.getByRole("dialog").filter({ has: page.getByRole("heading", { name: `خلاصه حساب ${customerName}` }) });
  await expect(summary).toBeVisible();
  await expect(summary.getByText("حساب تسویه است", { exact: true })).toBeVisible();
  await expect(summary).toContainText(customerNote);
  await expect(summary).toContainText("۰۹۱۲۱۲۳۴۵۶۷");
  await expectNoHorizontalOverflow(page);
  await expectNoElementOverflow(summary);
  if (mobile) {
    const bounds = await summary.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.width).toBe(390);
    expect(bounds!.height).toBe(844);
  }
});

test("ثبت چک با عدد فارسی و ویرایش امن سررسید با سابقه", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  const suffix = projectSuffix(testInfo.project.name);
  const chequeNumber = mobile ? "۹۸۷۶۵۴۳۲۱" : "۱۲۳۴۵۶۷۸۹";

  await login(page);
  await navigate(page, "چک‌ها", "مدیریت چک‌ها", mobile);
  await page.getByLabel("نام بانک").fill(`بانک E2E ${suffix}`);
  await page.getByLabel("شماره چک").fill(chequeNumber);
  const amount = page.getByLabel("مبلغ (تومان)").first();
  await amount.fill("۱۲۳۴۵۶۷");
  await expect(amount).toHaveValue("۱٬۲۳۴٬۵۶۷");
  await page.getByLabel("یادداشت (اختیاری)", { exact: true }).first().fill(`ثبت خودکار ${suffix}`);
  await page.getByRole("button", { name: "ثبت چک", exact: true }).click();
  await expect(page.getByText("چک با موفقیت ثبت شد.", { exact: true })).toBeVisible();

  const card = page.locator(".cheque-card").filter({ hasText: chequeNumber });
  await expect(card).toContainText("۱٬۲۳۴٬۵۶۷ تومان");
  await expect(card).toContainText("در انتظار");
  await card.getByRole("button", { name: "ویرایش", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: new RegExp(`ویرایش چک ${chequeNumber}`) });
  await expect(dialog).toBeVisible();
  const save = dialog.getByRole("button", { name: "ذخیره ویرایش", exact: true });
  await expect(save).toBeDisabled();
  await dialog.getByLabel("دلیل ویرایش").fill(`کنترل سررسید ${suffix}`);
  await dialog.getByLabel("یادداشت (اختیاری)", { exact: true }).fill(`سررسید بازبینی شد ${suffix}`);
  await save.click();
  await expect(page.getByText("اطلاعات چک ویرایش و در تاریخچه ثبت شد.", { exact: true })).toBeVisible();

  await card.getByRole("button", { name: "ویرایش", exact: true }).click();
  const reopened = page.getByRole("dialog", { name: new RegExp(`ویرایش چک ${chequeNumber}`) });
  await expect(reopened.getByText(`کنترل سررسید ${suffix}`, { exact: true })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expectNoElementOverflow(reopened);
  if (mobile) await expect(reopened).toHaveClass(/MuiDialog-paperFullScreen/);
});

test("ویرایش سررسید پرداخت pending فروش و ثبت audit", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  const suffix = projectSuffix(testInfo.project.name);

  await login(page);
  await navigate(page, "فروش", "ثبت فروش", mobile);
  const demoInvoice = page.locator(".recent-sale-card").filter({ hasText: "مشتری نمونه فروشگاه" });
  await expect(demoInvoice).toBeVisible();
  await demoInvoice.locator(".recent-sale-summary").click();
  const pendingPayment = demoInvoice.locator(".recent-payment-card").filter({ hasText: "در انتظار" });
  await pendingPayment.getByRole("button", { name: "ویرایش سررسید", exact: true }).click();

  const dialog = page.getByRole("dialog", { name: "ویرایش سررسید پرداخت" });
  await expect(dialog).toBeVisible();
  const toggle = dialog.getByRole("button", { name: "حذف سررسید", exact: true });
  await toggle.click();
  await expect(dialog.getByText("این پرداخت بدون سررسید ذخیره می‌شود.", { exact: true })).toBeVisible();
  await dialog.getByLabel("دلیل تغییر").fill(`آزمون حذف سررسید ${suffix}`);
  await dialog.getByRole("button", { name: "ذخیره سررسید", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(pendingPayment).toContainText("بدون سررسید");

  await pendingPayment.getByRole("button", { name: "ویرایش سررسید", exact: true }).click();
  const reopened = page.getByRole("dialog", { name: "ویرایش سررسید پرداخت" });
  await expect(reopened.getByText(`آزمون حذف سررسید ${suffix}`, { exact: true })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expectNoElementOverflow(reopened);
  if (mobile) await expect(reopened).toHaveClass(/MuiDialog-paperFullScreen/);
});
