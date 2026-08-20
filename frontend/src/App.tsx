import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  api,
  type DailyJournal,
  type PaymentCreate,
  type PaymentMethod,
  type PaymentStatus,
  type ProductVariant,
  type SaleInvoice,
  type User,
} from "./api";

const TOKEN_KEY = "store_auth_token";
const DEFAULT_JALALI_DATE = "1405/05/29";

type AuthStatus = "checking" | "guest" | "authenticated";
type AppView = "dashboard" | "sales";

type InvoiceDraftItem = {
  id: string;
  variantId: number;
  variantName: string;
  quantity: number;
  unitPriceRial: number;
  discountAmountRial: number;
};

type PaymentDraft = {
  id: string;
  method: PaymentMethod;
  amountRial: number;
  status: PaymentStatus;
  referenceNumber: string;
  dueJalaliDate: string;
  note: string;
};

const paymentLabels: Record<PaymentMethod, string> = {
  cash: "نقد",
  card: "کارتخوان",
  transfer: "کارت‌به‌کارت",
  credit: "نسیه",
  cheque: "چک",
  voucher: "کالابرگ",
};

const paymentMethods: PaymentMethod[] = ["cash", "card", "transfer", "credit", "cheque", "voucher"];

const moduleCards = [
  {
    key: "sales",
    title: "فروش",
    description: "ثبت فروش سریع، پرداخت ترکیبی و بررسی دفتر روزانه",
    icon: "ف",
    accent: "teal",
    status: "فعال",
  },
  {
    key: "products",
    title: "کالاها",
    description: "تعریف کالا، واحدها و قیمت‌های پایه",
    icon: "ک",
    accent: "blue",
    status: "آماده پایه",
  },
  {
    key: "purchase",
    title: "خرید",
    description: "ثبت خرید از تامین‌کننده و قیمت تمام‌شده",
    icon: "خ",
    accent: "amber",
    status: "به‌زودی",
  },
  {
    key: "inventory",
    title: "انبار",
    description: "موجودی، ورود و خروج و هشدار کمبود",
    icon: "ا",
    accent: "green",
    status: "به‌زودی",
  },
  {
    key: "ledger",
    title: "دفتر حساب",
    description: "حساب مشتریان، تامین‌کنندگان و تسویه‌ها",
    icon: "د",
    accent: "violet",
    status: "به‌زودی",
  },
  {
    key: "cheques",
    title: "چک‌ها",
    description: "چک‌های دریافتی، پرداختی و سررسیدها",
    icon: "چ",
    accent: "rose",
    status: "به‌زودی",
  },
  {
    key: "reports",
    title: "گزارش‌ها",
    description: "گزارش فروش، سود، بدهکاران و عملکرد روز",
    icon: "گ",
    accent: "slate",
    status: "به‌زودی",
  },
];

function formatRial(value: number) {
  return `${Math.max(0, value).toLocaleString("fa-IR")} ریال`;
}

function normalizeMoney(value: FormDataEntryValue | null) {
  const parsed = Number(String(value ?? "0").replace(/,/g, ""));
  return Number.isFinite(parsed) && parsed > 0 ? Math.round(parsed) : 0;
}

function normalizeDecimal(value: FormDataEntryValue | null) {
  const parsed = Number(String(value ?? "0").replace(",", "."));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function currentLocalTime() {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function makeDraftPayment(method: PaymentMethod, amountRial = 0): PaymentDraft {
  const pending = method === "credit" || method === "cheque" || method === "voucher";
  return {
    id: crypto.randomUUID(),
    method,
    amountRial,
    status: pending ? "pending" : "received",
    referenceNumber: "",
    dueJalaliDate: "",
    note: "",
  };
}

function App() {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [view, setView] = useState<AppView>("dashboard");
  const [user, setUser] = useState<User | null>(null);
  const [loginError, setLoginError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setStatus("guest");
      return;
    }

    api
      .me()
      .then((currentUser) => {
        setUser(currentUser);
        setStatus("authenticated");
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setStatus("guest");
      });
  }, []);

  const displayName = useMemo(() => {
    return user?.full_name || user?.username || "مدیر فروشگاه";
  }, [user]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginError("");
    setIsSubmitting(true);

    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") ?? "").trim();
    const password = String(form.get("password") ?? "");

    try {
      const result = await api.login(username, password);
      localStorage.setItem(TOKEN_KEY, result.access_token);
      setUser(result.user);
      setStatus("authenticated");
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "ورود انجام نشد.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setView("dashboard");
    setStatus("guest");
  }

  if (status === "checking") {
    return (
      <main className="shell center-shell">
        <section className="checking-panel" aria-live="polite">
          <div className="loader" />
          <p>در حال بررسی ورود...</p>
        </section>
      </main>
    );
  }

  if (status === "guest") {
    return (
      <main className="login-layout">
        <section className="login-copy" aria-labelledby="login-title">
          <div className="brand-mark">
            <span aria-hidden="true">ح</span>
          </div>
          <p className="eyebrow">اتوماسیون فروشگاه حبوبات</p>
          <h1 id="login-title">ورود به محیط مدیریت فروشگاه</h1>
          <p className="intro">
            مسیر کار از فروش روزانه شروع می‌شود: ورود مدیر، ثبت فاکتور، دریافت ترکیبی و دیدن خلاصه همان روز.
          </p>
          <div className="status-strip" aria-label="وضعیت پروژه">
            <span>فاز ۳</span>
            <strong>فروش روزانه فعال</strong>
          </div>
        </section>

        <section className="login-panel" aria-label="فرم ورود">
          <div className="panel-header">
            <h2>ورود مدیر</h2>
            <p>نام کاربری و رمز عبور حساب مدیر را وارد کنید.</p>
          </div>
          <form onSubmit={handleLogin} className="login-form">
            <label htmlFor="username">نام کاربری</label>
            <input id="username" name="username" type="text" autoComplete="username" placeholder="مثلا admin" required />

            <label htmlFor="password">رمز عبور</label>
            <input id="password" name="password" type="password" autoComplete="current-password" placeholder="رمز عبور" required />

            {loginError ? (
              <p className="error-message" role="alert">
                {loginError}
              </p>
            ) : null}

            <button type="submit" className="primary-button" disabled={isSubmitting}>
              {isSubmitting ? "در حال ورود..." : "ورود به داشبورد"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-layout">
      <header className="topbar">
        <div>
          <p className="eyebrow">داشبورد فروشگاه</p>
          <h1>سلام، {displayName}</h1>
        </div>
        <button className="ghost-button" type="button" onClick={handleLogout}>
          خروج
        </button>
      </header>

      {view === "sales" ? (
        <SalesView onBack={() => setView("dashboard")} />
      ) : (
        <DashboardView onOpenSales={() => setView("sales")} />
      )}
    </main>
  );
}

function DashboardView({ onOpenSales }: { onOpenSales: () => void }) {
  return (
    <>
      <section className="overview-band" aria-label="وضعیت امروز">
        <div>
          <span>امروز</span>
          <strong>آماده ثبت فروش</strong>
        </div>
        <div>
          <span>مرحله پروژه</span>
          <strong>فاز ۳ فعال</strong>
        </div>
        <div>
          <span>تمرکز فعلی</span>
          <strong>فروش و دفتر روزانه</strong>
        </div>
      </section>

      <section className="section-header">
        <div>
          <h2>بخش‌های اصلی سیستم</h2>
          <p>فروش روزانه فعال شده و بقیه ماژول‌ها طبق فازهای بعدی کامل می‌شوند.</p>
        </div>
        <span className="badge">نسخه عملیاتی اولیه</span>
      </section>

      <section className="module-grid" aria-label="ماژول‌های سیستم">
        {moduleCards.map((card) => {
          const isSales = card.key === "sales";
          return (
            <article className={`module-card accent-${card.accent} ${isSales ? "module-card-active" : ""}`} key={card.title}>
              <div className="module-icon">
                <span aria-hidden="true">{card.icon}</span>
              </div>
              <div>
                <h3>{card.title}</h3>
                <p>{card.description}</p>
              </div>
              {isSales ? (
                <button type="button" className="module-action" onClick={onOpenSales}>
                  شروع فروش
                </button>
              ) : (
                <span className="coming-soon">{card.status}</span>
              )}
            </article>
          );
        })}
      </section>
    </>
  );
}

function SalesView({ onBack }: { onBack: () => void }) {
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [variantsStatus, setVariantsStatus] = useState<"loading" | "ready" | "error">("loading");
  const [variantsError, setVariantsError] = useState("");
  const [items, setItems] = useState<InvoiceDraftItem[]>([]);
  const [payments, setPayments] = useState<PaymentDraft[]>([makeDraftPayment("cash")]);
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [customerName, setCustomerName] = useState("");
  const [saleDate, setSaleDate] = useState(DEFAULT_JALALI_DATE);
  const [saleTime, setSaleTime] = useState(currentLocalTime());
  const [submitStatus, setSubmitStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [submitMessage, setSubmitMessage] = useState("");
  const [lastSale, setLastSale] = useState<SaleInvoice | null>(null);
  const [journalDate, setJournalDate] = useState(DEFAULT_JALALI_DATE);
  const [journal, setJournal] = useState<DailyJournal | null>(null);
  const [journalStatus, setJournalStatus] = useState<"idle" | "loading" | "error">("idle");
  const [journalError, setJournalError] = useState("");

  useEffect(() => {
    let isMounted = true;
    setVariantsStatus("loading");
    api
      .productVariants()
      .then((result) => {
        if (!isMounted) return;
        setVariants(result);
        setVariantsStatus("ready");
      })
      .catch((error) => {
        if (!isMounted) return;
        setVariantsError(error instanceof Error ? error.message : "کالاها دریافت نشدند.");
        setVariantsStatus("error");
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const subtotal = useMemo(() => {
    return items.reduce((sum, item) => {
      return sum + Math.max(0, Math.round(item.quantity * item.unitPriceRial) - item.discountAmountRial);
    }, 0);
  }, [items]);

  const total = Math.max(0, subtotal - invoiceDiscount);
  const paymentTotal = payments.reduce((sum, payment) => sum + payment.amountRial, 0);
  const remaining = Math.max(0, total - paymentTotal);

  function handleAddItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const variantId = Number(form.get("variantId"));
    const variant = variants.find((item) => item.id === variantId);
    const quantity = normalizeDecimal(form.get("quantity"));
    const unitPriceRial = normalizeMoney(form.get("unitPriceRial"));
    const discountAmountRial = normalizeMoney(form.get("itemDiscount"));

    if (!variant || quantity <= 0 || unitPriceRial <= 0) {
      setSubmitStatus("error");
      setSubmitMessage("برای افزودن کالا، نام کالا، مقدار و قیمت واحد را کامل کنید.");
      return;
    }

    setItems((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        variantId,
        variantName: variant.name,
        quantity,
        unitPriceRial,
        discountAmountRial,
      },
    ]);
    setSubmitStatus("idle");
    setSubmitMessage("");
    event.currentTarget.reset();
  }

  function updatePayment(id: string, patch: Partial<PaymentDraft>) {
    setPayments((current) => current.map((payment) => (payment.id === id ? { ...payment, ...patch } : payment)));
  }

  async function handleSubmitSale(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitStatus("loading");
    setSubmitMessage("");

    if (!items.length) {
      setSubmitStatus("error");
      setSubmitMessage("حداقل یک کالا به فاکتور اضافه کنید.");
      return;
    }

    const validPayments = payments.filter((payment) => payment.amountRial > 0);
    if (!validPayments.length) {
      setSubmitStatus("error");
      setSubmitMessage("حداقل یک ردیف پرداخت با مبلغ معتبر وارد کنید.");
      return;
    }

    const payloadPayments: PaymentCreate[] = validPayments.map((payment) => ({
      method: payment.method,
      amount_rial: payment.amountRial,
      status: payment.status,
      reference_number: payment.referenceNumber.trim() || undefined,
      jalali_date: saleDate,
      local_time: saleTime,
      due_jalali_date: payment.dueJalaliDate.trim() || undefined,
      note: payment.note.trim() || undefined,
    }));

    try {
      const sale = await api.createSale({
        customer_name: customerName.trim() || undefined,
        jalali_date: saleDate,
        local_time: saleTime,
        discount_amount_rial: invoiceDiscount,
        items: items.map((item) => ({
          variant_id: item.variantId,
          quantity: item.quantity,
          unit_price_rial: item.unitPriceRial,
          discount_amount_rial: item.discountAmountRial,
        })),
        payments: payloadPayments,
      });

      setLastSale(sale);
      setSubmitStatus("success");
      setSubmitMessage(`فاکتور ${sale.invoice_number ?? sale.id} با موفقیت ثبت شد.`);
      setItems([]);
      setInvoiceDiscount(0);
      setPayments([makeDraftPayment("cash")]);
      setCustomerName("");
    } catch (error) {
      setSubmitStatus("error");
      setSubmitMessage(error instanceof Error ? error.message : "ثبت فروش انجام نشد.");
    }
  }

  async function handleLoadJournal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setJournalStatus("loading");
    setJournalError("");
    try {
      const result = await api.dailyJournal(journalDate);
      setJournal(result);
      setJournalStatus("idle");
    } catch (error) {
      setJournalStatus("error");
      setJournalError(error instanceof Error ? error.message : "دفتر روزانه دریافت نشد.");
    }
  }

  return (
    <section className="sales-workspace" aria-label="ثبت فروش روزانه">
      <div className="sales-header">
        <div>
          <p className="eyebrow">فروش روزانه</p>
          <h2>ثبت فاکتور و پرداخت ترکیبی</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onBack}>
          بازگشت به داشبورد
        </button>
      </div>

      <div className="sales-grid">
        <section className="sale-panel sale-panel-main">
          <form className="sale-meta-grid" onSubmit={handleSubmitSale}>
            <label>
              نام مشتری
              <input value={customerName} onChange={(event) => setCustomerName(event.target.value)} placeholder="اختیاری" />
            </label>
            <label>
              تاریخ شمسی
              <input value={saleDate} onChange={(event) => setSaleDate(event.target.value)} placeholder="1405/05/29" required />
            </label>
            <label>
              ساعت
              <input value={saleTime} onChange={(event) => setSaleTime(event.target.value)} placeholder="14:30" required />
            </label>
            <label>
              تخفیف فاکتور
              <input inputMode="numeric" value={invoiceDiscount || ""} onChange={(event) => setInvoiceDiscount(normalizeMoney(event.target.value))} placeholder="0" />
            </label>

            <div className="invoice-summary" aria-label="جمع فاکتور">
              <div>
                <span>جمع کالاها</span>
                <strong>{formatRial(subtotal)}</strong>
              </div>
              <div>
                <span>مبلغ قابل پرداخت</span>
                <strong>{formatRial(total)}</strong>
              </div>
              <div>
                <span>مانده پرداخت</span>
                <strong className={remaining > 0 ? "text-danger" : "text-ok"}>{formatRial(remaining)}</strong>
              </div>
            </div>

            <div className="payment-list">
              <div className="mini-section-header">
                <h3>پرداخت‌ها</h3>
                <button type="button" className="soft-button" onClick={() => setPayments((current) => [...current, makeDraftPayment("cash", remaining)])}>
                  افزودن پرداخت
                </button>
              </div>
              {payments.map((payment) => (
                <div className="payment-row" key={payment.id}>
                  <select value={payment.method} onChange={(event) => updatePayment(payment.id, { method: event.target.value as PaymentMethod })}>
                    {paymentMethods.map((method) => (
                      <option value={method} key={method}>
                        {paymentLabels[method]}
                      </option>
                    ))}
                  </select>
                  <input
                    inputMode="numeric"
                    value={payment.amountRial || ""}
                    onChange={(event) => updatePayment(payment.id, { amountRial: normalizeMoney(event.target.value) })}
                    placeholder="مبلغ"
                  />
                  <select value={payment.status} onChange={(event) => updatePayment(payment.id, { status: event.target.value as PaymentStatus })}>
                    <option value="received">دریافت‌شده</option>
                    <option value="pending">در انتظار</option>
                  </select>
                  <input value={payment.referenceNumber} onChange={(event) => updatePayment(payment.id, { referenceNumber: event.target.value })} placeholder="شماره پیگیری/چک" />
                  <input value={payment.dueJalaliDate} onChange={(event) => updatePayment(payment.id, { dueJalaliDate: event.target.value })} placeholder="سررسید" />
                  <button type="button" className="icon-button" aria-label="حذف پرداخت" onClick={() => setPayments((current) => current.filter((item) => item.id !== payment.id))}>
                    ×
                  </button>
                </div>
              ))}
            </div>

            {submitMessage ? (
              <p className={submitStatus === "success" ? "success-message" : "error-message"} role="status">
                {submitMessage}
              </p>
            ) : null}

            <button type="submit" className="primary-button submit-sale-button" disabled={submitStatus === "loading"}>
              {submitStatus === "loading" ? "در حال ثبت..." : "ثبت فروش"}
            </button>
          </form>
        </section>

        <aside className="sale-panel">
          <div className="mini-section-header">
            <h3>افزودن کالا</h3>
            <span>{variants.length.toLocaleString("fa-IR")} کالا</span>
          </div>

          {variantsStatus === "loading" ? <p className="state-message">در حال دریافت کالاها...</p> : null}
          {variantsStatus === "error" ? <p className="error-message">{variantsError}</p> : null}
          {variantsStatus === "ready" && variants.length === 0 ? <p className="state-message">هنوز کالایی برای فروش ثبت نشده است.</p> : null}

          {variantsStatus === "ready" && variants.length > 0 ? (
            <form className="add-item-form" onSubmit={handleAddItem}>
              <label>
                کالا
                <select name="variantId" required>
                  <option value="">انتخاب کالا</option>
                  {variants.map((variant) => (
                    <option value={variant.id} key={variant.id}>
                      {variant.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="compact-fields">
                <label>
                  مقدار
                  <input name="quantity" inputMode="decimal" placeholder="1" required />
                </label>
                <label>
                  قیمت واحد
                  <input name="unitPriceRial" inputMode="numeric" placeholder="ریال" required />
                </label>
              </div>
              <label>
                تخفیف ردیف
                <input name="itemDiscount" inputMode="numeric" placeholder="اختیاری" />
              </label>
              <button type="submit" className="soft-button">
                افزودن به فاکتور
              </button>
            </form>
          ) : null}

          <div className="invoice-items">
            <div className="mini-section-header">
              <h3>اقلام فاکتور</h3>
              <span>{items.length.toLocaleString("fa-IR")} ردیف</span>
            </div>
            {items.length === 0 ? (
              <p className="state-message">کالایی به فاکتور اضافه نشده است.</p>
            ) : (
              items.map((item) => {
                const lineTotal = Math.max(0, Math.round(item.quantity * item.unitPriceRial) - item.discountAmountRial);
                return (
                  <div className="invoice-item" key={item.id}>
                    <div>
                      <strong>{item.variantName}</strong>
                      <span>
                        {item.quantity.toLocaleString("fa-IR")} × {formatRial(item.unitPriceRial)}
                      </span>
                    </div>
                    <div>
                      <strong>{formatRial(lineTotal)}</strong>
                      <button type="button" className="link-button" onClick={() => setItems((current) => current.filter((draft) => draft.id !== item.id))}>
                        حذف
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>
      </div>

      <section className="journal-panel">
        <form className="journal-form" onSubmit={handleLoadJournal}>
          <div>
            <p className="eyebrow">دفتر روزانه</p>
            <h2>خلاصه فروش یک روز</h2>
          </div>
          <input value={journalDate} onChange={(event) => setJournalDate(event.target.value)} placeholder="1405/05/29" required />
          <button type="submit" className="ghost-button" disabled={journalStatus === "loading"}>
            {journalStatus === "loading" ? "در حال دریافت..." : "نمایش گزارش"}
          </button>
        </form>

        {journalStatus === "error" ? <p className="error-message">{journalError}</p> : null}
        {lastSale ? <p className="success-message">آخرین فاکتور ثبت‌شده: {lastSale.invoice_number ?? lastSale.id}</p> : null}
        {journal ? (
          <div className="journal-summary">
            <div>
              <span>تعداد فاکتور</span>
              <strong>{journal.invoice_count.toLocaleString("fa-IR")}</strong>
            </div>
            <div>
              <span>فروش ثبت‌شده</span>
              <strong>{formatRial(journal.sales_total_rial)}</strong>
            </div>
            <div>
              <span>دریافت واقعی</span>
              <strong>{formatRial(journal.received_total_rial)}</strong>
            </div>
            <div>
              <span>در انتظار</span>
              <strong>{formatRial(journal.pending_total_rial)}</strong>
            </div>
          </div>
        ) : null}

        {journal?.payments.length ? (
          <div className="journal-breakdown">
            {journal.payments.map((payment) => (
              <div key={payment.method}>
                <strong>{paymentLabels[payment.method]}</strong>
                <span>دریافت: {formatRial(payment.received_rial)}</span>
                <span>در انتظار: {formatRial(payment.pending_rial)}</span>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </section>
  );
}

export default App;
