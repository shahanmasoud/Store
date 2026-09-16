import { expect, test, type Locator, type Page } from "@playwright/test";

const browserErrors = new WeakMap<Page, string[]>();
const allowedConsoleErrors = new WeakMap<Page, RegExp[]>();

test.beforeEach(async ({ context, page }) => {
  const errors: string[] = [];
  browserErrors.set(page, errors);
  page.on("pageerror", (error) => errors.push(`pageerror:${error.name}`));
  page.on("console", (message) => {
    if (message.type() === "error" && !(allowedConsoleErrors.get(page) ?? []).some((pattern) => pattern.test(message.text()))) {
      errors.push(`console:${message.text()}`);
    }
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
  await scope.getByRole("combobox", { name: fieldName }).click();
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

test("داشبورد فشرده با اقدام اصلی و میانبرهای قابل لمس", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  await login(page);
  await expect(page.getByRole("button", { name: "ثبت فروش جدید", exact: true })).toBeVisible();
  await expect(page.locator(".material-module-card")).toHaveCount(8);
  await expect(page.getByText("شروع سریع برای کاربر تازه‌کار", { exact: true })).toHaveCount(0);
  const shortcuts = page.locator(".dashboard-primary-actions .MuiButton-root");
  await expect(shortcuts).toHaveCount(4);
  const minHeight = await shortcuts.evaluateAll((items) => Math.min(...items.map((item) => item.getBoundingClientRect().height)));
  expect(minHeight).toBeGreaterThanOrEqual(44);
  const completeModules = await page.locator(".material-module-card").evaluateAll((items) => items.filter((item) => item.getBoundingClientRect().bottom <= innerHeight).length);
  expect(completeModules).toBeGreaterThanOrEqual(mobile ? 0 : 8);
  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: testInfo.outputPath(`dashboard-${mobile ? "mobile" : "desktop"}.png`), animations: "disabled" });
});

test("landmark، صفحه‌کلید، بازگشت focus و reduced-motion دسترس‌پذیر هستند", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await login(page);

  await expect(page.getByRole("main")).toHaveCount(1);
  await expect(page.getByRole("heading", { name: "خانه مدیریت", level: 1 })).toBeVisible();
  const motionDuration = await page.locator(".sidebar-link").first().evaluate((element) => getComputedStyle(element).transitionDuration);
  expect(Number.parseFloat(motionDuration)).toBeLessThanOrEqual(0.01);

  if (mobile) {
    const menuTrigger = page.getByRole("button", { name: "باز کردن منوی بخش‌های مدیریت" });
    await menuTrigger.focus();
    await page.keyboard.press("Enter");
    const mobileNavigation = page.getByRole("navigation", { name: "بخش‌های پنل مدیریت" }).last();
    await expect(mobileNavigation).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(menuTrigger).toBeVisible();
    await expect(menuTrigger).toBeFocused();
    const triggerBounds = await menuTrigger.boundingBox();
    expect(triggerBounds).not.toBeNull();
    expect(triggerBounds!.width).toBeGreaterThanOrEqual(44);
    expect(triggerBounds!.height).toBeGreaterThanOrEqual(44);
  }

  const passwordTrigger = page.getByRole("button", { name: "تغییر رمز" });
  await passwordTrigger.focus();
  await page.keyboard.press("Enter");
  const passwordDialog = page.getByRole("dialog", { name: "تغییر رمز عبور" });
  await expect(passwordDialog).toBeVisible();
  await expect.poll(() => passwordDialog.evaluate((dialog) => dialog.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(passwordDialog).toBeHidden();
  await expect(passwordTrigger).toBeFocused();
});

test("حالت‌های loading، error، retry و empty کالاها روشن و قابل بازیابی هستند", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  let responseMode: "delayed-error" | "empty" = "delayed-error";
  let releaseFailure!: () => void;
  const failureGate = new Promise<void>((resolve) => { releaseFailure = resolve; });
  const catalogEndpointSuffixes = ["/units", "/categories", "/products", "/product-variants", "/prices", "/price-rules"];
  allowedConsoleErrors.set(page, [/status of 418/]);

  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/\/$/, "");
    if (!catalogEndpointSuffixes.some((suffix) => path.endsWith(suffix))) {
      await route.continue();
      return;
    }
    if (responseMode === "delayed-error") {
      await failureGate;
      await route.fulfill({ status: 418, contentType: "application/json", body: JSON.stringify({ detail: "خطای کنترل‌شده آزمون" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await login(page);
  const navigationPromise = mobile
    ? page.getByRole("button", { name: "باز کردن منوی بخش‌های مدیریت" }).click()
    : Promise.resolve();
  await navigationPromise;
  await page.getByRole("button", { name: "کالاها", exact: true }).last().click();
  await expect(page.getByRole("heading", { name: "کالاها و قیمت‌ها", exact: true, level: 1 })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "در حال دریافت دسته‌ها…" })).toBeVisible();
  releaseFailure();
  await expect(page.getByRole("alert").filter({ hasText: "خطای کنترل‌شده آزمون" })).toBeVisible();

  responseMode = "empty";
  await page.getByRole("button", { name: "تلاش دوباره", exact: true }).first().click();
  await expect(page.getByRole("status").filter({ hasText: "هنوز دسته‌ای ندارید" })).toBeVisible();
  await page.getByRole("tab", { name: "واحد و کالا", exact: true }).click();
  await expect(page.getByText("هنوز واحدی ثبت نشده است", { exact: true })).toBeVisible();
  await expect(page.getByText("هنوز کالایی ثبت نشده است", { exact: true })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("ورودی مبلغ paste فارسی و لاتین، caret میانی و Backspace را پایدار نگه می‌دارد", async ({ context, page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: "http://127.0.0.1:5193" });
  await login(page);
  await navigate(page, "چک‌ها", "مدیریت چک‌ها", mobile);
  const amount = page.getByLabel("مبلغ (تومان)").first();

  await amount.fill("1234567");
  await expect(amount).toHaveValue("۱٬۲۳۴٬۵۶۷");
  await amount.evaluate((input: HTMLInputElement) => input.setSelectionRange(3, 3));
  await amount.press("9");
  await expect(amount).toHaveValue("۱۲٬۹۳۴٬۵۶۷");
  await expect.poll(() => amount.evaluate((input: HTMLInputElement) => input.selectionStart)).toBe(4);

  await amount.press("Backspace");
  await expect(amount).toHaveValue("۱٬۲۳۴٬۵۶۷");
  await expect.poll(() => amount.evaluate((input: HTMLInputElement) => input.selectionStart)).toBe(3);

  await amount.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
  await page.evaluate(() => navigator.clipboard.writeText("۹۸76543"));
  await amount.press(process.platform === "darwin" ? "Meta+V" : "Control+V");
  await expect(amount).toHaveValue("۹٬۸۷۶٬۵۴۳");
  await expectNoHorizontalOverflow(page);
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

test("کارت‌های فروش: جستجو، مقدار فارسی، کنترل موجودی و ویرایش سبد", async ({ page }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  await loginAs(page, "e2e-sales", "e2e-role-password");
  await navigate(page, "فروش", "ثبت فروش", mobile);
  const search = page.getByRole("textbox", { name: "جستجوی کالا" });
  await search.fill("کالای غیرواقعی");
  await expect(page.getByText("کالایی پیدا نشد", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "پاک کردن فیلترها" }).click();
  await chooseOption(page, "دسته‌بندی کالا", "حبوبات");
  await search.fill("لوبیا");
  const card = page.getByRole("button", { name: "انتخاب لوبیا چیتی ممتاز", exact: true });
  await expect(card).toBeVisible();
  await expect(card).toContainText("۱۸۵٬۰۰۰");
  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: testInfo.outputPath("sale-product-cards.png"), fullPage: true });
  await card.click();
  const dialog = page.getByRole("dialog", { name: "افزودن به فروش · لوبیا چیتی ممتاز" });
  await expect(dialog).toBeVisible();
  if (mobile) await expect(dialog).toHaveClass(/MuiDialog-paperFullScreen/);
  await expect(dialog.getByRole("textbox", { name: "قیمت واحد (تومان)" })).toHaveValue("۱۸۵٬۰۰۰");
  const quantity = dialog.getByRole("textbox", { name: "مقدار", exact: true });
  await quantity.fill("۹۹۹۹");
  await dialog.getByRole("button", { name: "افزودن به فاکتور", exact: true }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await quantity.fill("۱٫۵");
  await expectNoElementOverflow(dialog);
  await page.screenshot({ path: testInfo.outputPath("sale-card-dialog.png"), fullPage: true });
  await dialog.getByRole("button", { name: "افزودن به فاکتور", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  const row = page.locator(".invoice-item").filter({ hasText: "لوبیا چیتی ممتاز" });
  await expect(row).toContainText("۲۷۷٬۵۰۰");
  await expect(card).toContainText("۱٫۵ در فاکتور");
  await row.getByRole("button", { name: "ویرایش", exact: true }).click();
  const edit = page.getByRole("dialog");
  await edit.getByRole("textbox", { name: "مقدار", exact: true }).fill("۲");
  await edit.getByRole("button", { name: "ذخیره تغییرات", exact: true }).click();
  await expect(row).toContainText("۳۷۰٬۰۰۰");
  await row.getByRole("button", { name: "حذف", exact: true }).click();
  await expect(row).toHaveCount(0);
  await expectNoHorizontalOverflow(page);
});

test("چرخه کامل کالا، تصویر، خرید، انبار و نمایش در فروشگاه", async ({ page }, testInfo) => {
  test.setTimeout(75_000);
  page.setDefaultTimeout(8_000);
  const mobile = testInfo.project.name.startsWith("mobile");
  const suffix = projectSuffix(testInfo.project.name);
  const categoryName = `دسته E2E ${suffix}`;
  const unitName = `بسته E2E ${suffix}`;
  const unitSymbol = mobile ? "pkg-e2e-m" : "pkg-e2e-d";
  const productName = `لوبیا E2E ${suffix}`;
  const variantName = `${productName} ممتاز`;
  const productDescription = `کالای ساخته‌شده از دیتابیس ایزوله ${suffix}`;

  await login(page);
  await navigate(page, "کالاها", "کالاها و قیمت‌ها", mobile);

  const categorySubmit = page.getByRole("button", { name: "ثبت دسته", exact: true });
  await expect(categorySubmit).toBeDisabled();
  await page.getByRole("textbox", { name: "نام دسته", exact: true }).fill(categoryName);
  await categorySubmit.click();
  await expect(page.getByText("دسته جدید ثبت شد.", { exact: true })).toBeVisible();
  await expect(page.locator(".category-item").filter({ hasText: categoryName })).toBeVisible();

  await page.getByRole("tab", { name: "کالاها", exact: true }).click();
  await expect(page.getByRole("heading", { name: "کالاها", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: /واحد و کالا|گونه و قیمت/ })).toHaveCount(0);
  await page.getByRole("button", { name: "مدیریت واحدها", exact: true }).click();
  const unitDialog = page.getByRole("dialog", { name: "مدیریت واحدها" });
  if (mobile) await expect(unitDialog).toHaveClass(/MuiDialog-paperFullScreen/);
  const unitSubmit = unitDialog.getByRole("button", { name: "ثبت واحد", exact: true });
  await expect(unitSubmit).toBeDisabled();
  await unitDialog.getByRole("textbox", { name: "نام واحد" }).fill(unitName);
  await unitDialog.getByRole("textbox", { name: "نماد" }).fill(unitSymbol);
  await unitSubmit.click();
  await expect(page.getByText("واحد جدید ثبت شد.", { exact: true })).toBeVisible();
  await unitDialog.getByRole("button", { name: "بستن", exact: true }).click();

  await page.getByRole("button", { name: "افزودن کالا", exact: true }).click();
  const itemForm = page.locator(".variant-form");
  await itemForm.getByRole("textbox", { name: "نام کالا" }).fill(variantName);
  await chooseOption(page, "دسته‌بندی", categoryName, itemForm);
  await chooseOption(page, "واحد", `${unitName} (${unitSymbol})`, itemForm);
  await itemForm.getByRole("textbox", { name: "توضیح کوتاه" }).fill(productDescription);
  const retailPrice = itemForm.getByRole("textbox", { name: "قیمت خرده (تومان)" });
  await retailPrice.fill("۲۵۰۰۰۰");
  await expect(retailPrice).toHaveValue("۲۵۰٬۰۰۰");
  await page.getByRole("button", { name: "ثبت کالا", exact: true }).click();
  await expect(page.getByText("کالای جدید ثبت شد.", { exact: true })).toBeVisible();

  const productCard = page.locator(".catalog-product-card").filter({ hasText: variantName });
  await expect(productCard).toContainText(categoryName);
  await productCard.getByRole("button", { name: "عملیات کالا", exact: true }).click();
  await page.getByRole("menuitem", { name: "افزودن عکس", exact: true }).click();
  const imageDialog = page.getByRole("dialog", { name: `تصویر «${variantName}»` });
  await expect(imageDialog.getByRole("button", { name: "ذخیره تصویر", exact: true })).toBeDisabled();
  await imageDialog.locator('input[type="file"]').setInputFiles({
    name: "product-e2e.png",
    mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGO8UmXOgA0wYRUdtBIANJIBlR9nS+cAAAAASUVORK5CYII=", "base64"),
  });
  await expect(imageDialog.getByAltText(`پیش‌نمایش ${variantName}`)).toBeVisible();
  await imageDialog.getByRole("button", { name: "ذخیره تصویر", exact: true }).click();
  await expect(page.getByText(`تصویر «${variantName}» ذخیره شد و در فروشگاه نمایش داده می‌شود.`, { exact: true })).toBeVisible();
  await expect(productCard.locator("img")).toBeVisible();
  await expect(productCard).toContainText("۲۵۰٬۰۰۰ تومان");

  await navigate(page, "خرید", "ثبت خرید", mobile);
  const purchaseSubmit = page.getByRole("button", { name: "ثبت فاکتور خرید", exact: true });
  await expect(page.getByRole("button", { name: "ادامه و ثبت خرید", exact: true })).toBeDisabled();
  await page.getByRole("textbox", { name: "جستجوی کالا" }).fill(variantName);
  await page.getByRole("button", { name: `انتخاب ${variantName}`, exact: true }).click();
  await expect(page.getByRole("dialog", { name: `افزودن به خرید · ${variantName}` })).toBeVisible();
  await page.getByRole("textbox", { name: "مقدار" }).fill("۳");
  const unitCost = page.getByRole("textbox", { name: "قیمت واحد (تومان)" });
  await unitCost.fill("۱۲۰۰۰۰");
  await expect(unitCost).toHaveValue("۱۲۰٬۰۰۰");
  await page.getByRole("button", { name: "افزودن به فاکتور", exact: true }).click();
  await expect(page.locator(".purchase-invoice-item").filter({ hasText: variantName })).toContainText("۳۶۰٬۰۰۰ تومان");
  await page.getByRole("button", { name: "ادامه و ثبت خرید", exact: true }).click();
  await page.getByRole("textbox", { name: "نام تأمین‌کننده" }).fill(`تأمین‌کننده E2E ${suffix}`);
  await page.getByRole("textbox", { name: "پرداخت‌شده (تومان)" }).fill("۳۶۰۰۰۰");
  await purchaseSubmit.click();
  await expect(page.getByText(/فاکتور خرید .* با موفقیت ثبت شد\./)).toBeVisible();

  await page.getByRole("button", { name: "نمایش انبار", exact: true }).click();
  await expect(page.getByRole("heading", { name: "مدیریت انبار", exact: true, level: 1 })).toBeVisible();
  const inventoryCard = page.locator(".inventory-stock-card").filter({ hasText: variantName });
  await expect(inventoryCard).toContainText("۳");
  await expect(inventoryCard).toContainText("۱۲۰٬۰۰۰ تومان");
  const transaction = page.locator(".inventory-transaction").filter({ hasText: variantName }).first();
  await expect(transaction).toContainText("ورود خرید");
  await expect(transaction).toContainText("+۳");
  await expectNoHorizontalOverflow(page);

  await page.route("**/api/v1/storefront/catalog", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 250));
    await route.continue();
  });
  if (!mobile) await page.locator(".topbar").hover();
  await page.getByRole("button", { name: "مشاهده فروشگاه", exact: true }).click();
  await expect(page.locator('[aria-label="در حال بارگذاری کالاها"]')).toBeVisible();
  const storefrontCard = page.locator(".storefront-product-card").filter({ hasText: variantName });
  await expect(storefrontCard).toBeVisible();
  await expect(storefrontCard).toContainText(productDescription);
  await expect(storefrontCard).toContainText("۲۵۰٬۰۰۰ تومان");
  await expect(storefrontCard).toContainText("۳ موجود");
  const storefrontImage = storefrontCard.getByAltText(`تصویر ${variantName}`);
  await expect(storefrontImage).toBeVisible();
  await expect(storefrontImage).toHaveAttribute("src", /\/media\/products\/[a-f0-9]+\.png$/);
  await expect(storefrontImage).toHaveJSProperty("complete", true);
  await expectNoHorizontalOverflow(page);
  await expectNoElementOverflow(storefrontCard);
});

test("کاتالوگ متراکم: تراکم، فیلتر، ویرایش و بستن فرم", async ({ page, request }, testInfo) => {
  const mobile = testInfo.project.name.startsWith("mobile");
  await login(page);
  const token = await page.evaluate(() => localStorage.getItem("store_auth_token"));
  const headers = { Authorization: `Bearer ${token}` };
  const base = "http://127.0.0.1:8013/api/v1";
  const units = await (await request.get(`${base}/units`, { headers })).json();
  const categories = await (await request.get(`${base}/categories`, { headers })).json();
  const initialItems = await (await request.get(`${base}/product-variants`, { headers })).json();
  const names = ["عدس سبز", "لوبیا چیتی", "نخود کرمانشاه", "لوبیا قرمز", "ماش", "لپه", "برنج طارم", "عدس ریز", "لوبیا سفید", "نخود درشت", "گندم", "جو پوست‌کنده", "بلغور", "دال عدس", "لوبیا کشاورزی", "نخودچی", "برنج هاشمی", "عدس کانادایی"];
  for (const [index, name] of names.entries()) {
    const response = await request.post(`${base}/catalog-items`, { headers, data: { name: `${name} ممتاز`, unit_id: units[0].id, category_id: categories[0].id, sku: `QA-${index}`, retail_price_rial: 1250000 + index * 100000, wholesale_price_rial: 1100000 + index * 100000 } });
    expect(response.ok()).toBeTruthy();
  }
  await navigate(page, "کالاها", "کالاها و قیمت‌ها", mobile);
  await page.getByRole("tab", { name: "کالاها", exact: true }).click();
  const rows = page.locator(".catalog-product-card");
  await expect(rows).toHaveCount(names.length + initialItems.length);
  await expect(page.locator(".variant-form")).toHaveCount(0);
  await expectNoElementOverflow(page.locator(".compact-catalog"));
  const visibleRows = await rows.evaluateAll((items) => items.filter((item) => { const box = item.getBoundingClientRect(); return box.top >= 0 && box.bottom <= window.innerHeight; }).length);
  expect(visibleRows).toBeGreaterThanOrEqual(mobile ? 3 : 10);
  await page.screenshot({ animations: "disabled", path: `test-results/catalog-${testInfo.project.name}.png` });
  const search = page.getByRole("textbox", { name: "جست‌وجوی کالا یا کد" });
  await search.fill("QA-17");
  await expect(rows).toHaveCount(1);
  await rows.getByRole("button", { name: "ویرایش", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "ویرایش کالا", exact: true });
  await expect(dialog.getByRole("textbox", { name: "نام کالا" })).toHaveValue("عدس کانادایی ممتاز");
  if (mobile) await expect(dialog).toHaveClass(/MuiDialog-paperFullScreen/);
  await expectNoElementOverflow(dialog);
  const labelsClear = await dialog.locator(".MuiTextField-root").evaluateAll((fields) => fields.every((field) => { const label = field.querySelector("label")?.getBoundingClientRect(); const input = field.querySelector(".MuiInputBase-root")?.getBoundingClientRect(); return !label || !input || label.bottom <= input.top; }));
  expect(labelsClear).toBeTruthy();
  await page.screenshot({ animations: "disabled", path: `test-results/catalog-editor-${testInfo.project.name}.png` });
  await dialog.getByRole("textbox", { name: "نام کالا" }).fill("عدس کانادایی ویرایش‌شده");
  await dialog.getByRole("button", { name: "ذخیره تغییرات" }).click();
  await expect(dialog).toBeHidden();
  await expect(rows).toContainText("عدس کانادایی ویرایش‌شده");
  await page.getByRole("button", { name: "افزودن کالا", exact: true }).click();
  const addDialog = page.getByRole("dialog", { name: "افزودن کالا", exact: true });
  await expect(addDialog.getByRole("textbox", { name: "نام کالا" })).toHaveValue("");
  await expect(addDialog.getByRole("button", { name: "ثبت کالا", exact: true })).toBeDisabled();
  await addDialog.getByRole("button", { name: "انصراف", exact: true }).click();
  await expect(addDialog).toBeHidden();
  await search.fill("پیدا نمی‌شود");
  await page.getByRole("button", { name: "پاک کردن فیلترها" }).click();
  await expect(rows).toHaveCount(names.length + initialItems.length);
  await expectNoHorizontalOverflow(page);
});


test("خرید و فروش مرحله‌ای: حفظ پیش‌نویس، محاسبات و ثبت موجودی", async ({ page, request }, testInfo) => {
  test.setTimeout(75_000);
  const mobile = testInfo.project.name.startsWith("mobile");
  await login(page);
  const token = await page.evaluate(() => localStorage.getItem("store_auth_token"));
  const headers = { Authorization: `Bearer ${token}` };
  const base = "http://127.0.0.1:8013/api/v1";
  const variants = await (await request.get(`${base}/product-variants`, { headers })).json();
  const variant = variants.find((item: { sku: string }) => item.sku === "DEMO-BEAN-PINTO");
  const getStock = async () => (await (await request.get(`${base}/inventory`, { headers })).json()).find((item: { variant_id: number }) => item.variant_id === variant.id).quantity_on_hand;
  const stockBefore = Number(await getStock());
  await navigate(page, "خرید", "ثبت خرید", mobile);
  await expect(page.getByRole("textbox", { name: "نام تأمین‌کننده" })).toHaveCount(0);
  await page.getByTestId(`product-card-${variant.id}`).click();
  let itemDialog = page.getByRole("dialog");
  await itemDialog.getByRole("textbox", { name: "مقدار", exact: true }).fill("۲٫۵");
  await itemDialog.getByRole("textbox", { name: "قیمت واحد (تومان)" }).fill("۱۰۰۰۰۰");
  await itemDialog.getByRole("textbox", { name: "هزینه جانبی ردیف (تومان)" }).fill("۵۰۰۰");
  await itemDialog.getByRole("button", { name: "افزودن به فاکتور", exact: true }).click();
  await expect(page.locator(".invoice-cart")).toContainText("۲۵۵٬۰۰۰ تومان");
  await page.getByRole("button", { name: "ادامه و ثبت خرید", exact: true }).click();
  let checkout = page.getByRole("dialog", { name: "تکمیل خرید", exact: true });
  if (mobile) await expect(checkout).toHaveClass(/MuiDialog-paperFullScreen/);
  await checkout.getByRole("textbox", { name: "نام تأمین‌کننده" }).fill("تأمین‌کننده تست مرحله‌ای");
  await checkout.getByRole("textbox", { name: "تخفیف فاکتور (تومان)" }).fill("۱۰۰۰۰");
  await checkout.getByRole("textbox", { name: "هزینه جانبی فاکتور (تومان)" }).fill("۲۰۰۰۰");
  await checkout.getByRole("textbox", { name: "پرداخت‌شده (تومان)" }).fill("۶۵۰۰۰");
  await expect(checkout.locator(".purchase-summary")).toContainText("۲۶۵٬۰۰۰ تومان");
  await expect(checkout.locator(".purchase-summary")).toContainText("۲۰۰٬۰۰۰ تومان");
  await checkout.getByRole("button", { name: "بازگشت به اقلام" }).click();
  await expect(page.locator(".invoice-cart-footer")).toContainText("۲۶۵٬۰۰۰ تومان");
  await page.getByRole("button", { name: "ادامه و ثبت خرید", exact: true }).click();
  await expect(checkout.getByRole("textbox", { name: "نام تأمین‌کننده" })).toHaveValue("تأمین‌کننده تست مرحله‌ای");
  await expectNoElementOverflow(checkout);
  const purchaseResponse = page.waitForResponse(r => r.url().endsWith("/purchase-invoices") && r.request().method() === "POST");
  await checkout.getByRole("button", { name: "ثبت فاکتور خرید", exact: true }).click();
  const purchase = await (await purchaseResponse).json();
  expect(purchase.total_rial).toBe(2650000);
  await expect(checkout).toBeHidden();
  expect(Number(await getStock())).toBe(stockBefore + 2.5);

  await navigate(page, "فروش", "ثبت فروش", mobile);
  await page.getByTestId(`product-card-${variant.id}`).click();
  itemDialog = page.getByRole("dialog");
  await itemDialog.getByRole("textbox", { name: "مقدار", exact: true }).fill("۱٫۵");
  await itemDialog.getByRole("textbox", { name: "تخفیف ردیف (تومان)" }).fill("۷۵۰۰");
  await itemDialog.getByRole("button", { name: "افزودن به فاکتور", exact: true }).click();
  await expect(page.locator(".invoice-cart")).toContainText("۲۷۰٬۰۰۰ تومان");
  await page.getByRole("button", { name: "ادامه و پرداخت", exact: true }).click();
  checkout = page.getByRole("dialog", { name: "تکمیل فروش", exact: true });
  await checkout.getByRole("textbox", { name: "تخفیف فاکتور (تومان)" }).fill("۱۰۰۰۰");
  await checkout.getByRole("textbox", { name: "مبلغ (تومان)", exact: true }).fill("۱۰۰۰۰۰");
  await checkout.getByRole("button", { name: "ثبت نهایی فروش", exact: true }).click();
  await expect(checkout.getByText("برای فروش نسیه یا دارای مانده، انتخاب مشتری الزامی است.")).toBeVisible();
  await checkout.getByRole("textbox", { name: "مبلغ (تومان)", exact: true }).fill("۲۶۰۰۰۰");
  await checkout.getByRole("button", { name: "بازگشت به اقلام" }).click();
  await expect(page.locator(".invoice-cart-footer")).toContainText("۲۶۰٬۰۰۰ تومان");
  await page.getByRole("button", { name: "ادامه و پرداخت", exact: true }).click();
  await expect(checkout.getByRole("textbox", { name: "مبلغ (تومان)", exact: true })).toHaveValue("۲۶۰٬۰۰۰");
  await expectNoElementOverflow(checkout);
  const labelsClear = await checkout.locator(".MuiTextField-root").evaluateAll(fields => fields.every(field => { const label = field.querySelector("label")?.getBoundingClientRect(); const input = field.querySelector(".MuiInputBase-root")?.getBoundingClientRect(); return !label || !input || label.bottom <= input.top; }));
  expect(labelsClear).toBeTruthy();
  const saleResponse = page.waitForResponse(r => r.url().endsWith("/sales") && r.request().method() === "POST");
  await checkout.getByRole("button", { name: "ثبت نهایی فروش", exact: true }).click();
  const sale = await (await saleResponse).json();
  expect(sale.total_rial).toBe(2600000);
  expect(sale.payments[0].amount_rial).toBe(2600000);
  await expect(checkout).toBeHidden();
  await expect(page.locator(".invoice-cart .invoice-item")).toHaveCount(0);
  expect(Number(await getStock())).toBe(stockBefore + 1);
  await expectNoHorizontalOverflow(page);
});
