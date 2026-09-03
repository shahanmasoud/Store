import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { Alert, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Drawer, IconButton, InputAdornment, LinearProgress, MenuItem, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";
import AccountBalanceWalletRounded from "@mui/icons-material/AccountBalanceWalletRounded";
import AdminPanelSettingsRounded from "@mui/icons-material/AdminPanelSettingsRounded";
import AnalyticsRounded from "@mui/icons-material/AnalyticsRounded";
import ArrowBackRounded from "@mui/icons-material/ArrowBackRounded";
import DashboardRounded from "@mui/icons-material/DashboardRounded";
import FactCheckRounded from "@mui/icons-material/FactCheckRounded";
import HelpOutlineRounded from "@mui/icons-material/HelpOutlineRounded";
import Inventory2Rounded from "@mui/icons-material/Inventory2Rounded";
import PaymentsRounded from "@mui/icons-material/PaymentsRounded";
import PointOfSaleRounded from "@mui/icons-material/PointOfSaleRounded";
import ReceiptLongRounded from "@mui/icons-material/ReceiptLongRounded";
import ShoppingCartCheckoutRounded from "@mui/icons-material/ShoppingCartCheckoutRounded";
import StorefrontRounded from "@mui/icons-material/StorefrontRounded";
import SyncRounded from "@mui/icons-material/SyncRounded";
import AddRounded from "@mui/icons-material/AddRounded";
import CloseRounded from "@mui/icons-material/CloseRounded";
import DeleteOutlineRounded from "@mui/icons-material/DeleteOutlineRounded";
import EditRounded from "@mui/icons-material/EditRounded";
import FolderOutlined from "@mui/icons-material/FolderOutlined";
import RefreshRounded from "@mui/icons-material/RefreshRounded";
import CategoryRounded from "@mui/icons-material/CategoryRounded";
import SearchRounded from "@mui/icons-material/SearchRounded";
import StraightenRounded from "@mui/icons-material/StraightenRounded";
import HistoryRounded from "@mui/icons-material/HistoryRounded";
import LocalOfferRounded from "@mui/icons-material/LocalOfferRounded";
import MenuRounded from "@mui/icons-material/MenuRounded";
import {
  api,
  type DailyJournal,
  type Dues,
  type CashflowReport,
  type Category,
  type Cheque,
  type CustomerDebtsReport,
  type InventoryItem,
  type InventoryTransaction,
  type InventoryReport,
  type LedgerEntry,
  type OnlineChannel,
  type OnlineOrder,
  type OnlinePriceRule,
  type StockReservation,
  type PaymentCreate,
  type PaymentMethod,
  type PaymentStatus,
  type PriceList,
  type PriceRule,
  type PriceType,
  type Person,
  type Product,
  type ProductVariant,
  type ProfitLossReport,
  type PurchaseInvoice,
  type SaleInvoice,
  type SalesSummaryReport,
  type Unit,
  type User,
} from "./api";

const TOKEN_KEY = "store_auth_token";
const PRICE_TYPE_LABELS: Record<PriceType, string> = { retail: "خرده‌فروشی", wholesale: "عمده‌فروشی", online: "آنلاین" };

type AuthStatus = "checking" | "guest" | "authenticated";
type AppView = "dashboard" | "sales" | "purchase" | "inventory" | "products" | "ledger" | "cheques" | "reports" | "online";

const viewMeta: Record<AppView, { title: string; eyebrow: string; help: string }> = {
  dashboard: { title: "خانه مدیریت", eyebrow: "نمای کلی فروشگاه", help: "از کارهای سریع شروع کن یا وضعیت امروز را مرور کن." },
  sales: { title: "ثبت فروش", eyebrow: "فروش روزانه", help: "ابتدا کالاها را اضافه کن، سپس روش پرداخت را مشخص و فاکتور را ثبت کن." },
  purchase: { title: "ثبت خرید", eyebrow: "خرید و تامین", help: "تامین‌کننده و کالاها را وارد کن؛ موجودی بعد از ثبت به‌روز می‌شود." },
  inventory: { title: "مدیریت انبار", eyebrow: "موجودی و ارزش کالا", help: "کالاهای کم‌موجود را بررسی کن و برای خرید بعدی تصمیم بگیر." },
  products: { title: "کالاها و قیمت‌ها", eyebrow: "اطلاعات پایه", help: "تعریف کالا، واحد و تنوع محصول، پیش‌نیاز ثبت خرید و فروش است." },
  ledger: { title: "دفتر حساب", eyebrow: "حساب اشخاص", help: "مشتری یا تامین‌کننده را انتخاب کن و مانده و تراکنش‌هایش را ببین." },
  cheques: { title: "مدیریت چک‌ها", eyebrow: "سررسید و پیگیری", help: "چک‌های نزدیک به سررسید را اول بررسی و وضعیتشان را به‌روز کن." },
  reports: { title: "گزارش‌ها", eyebrow: "تحلیل عملکرد", help: "بازه زمانی را انتخاب کن تا فروش، سود و جریان نقدی را مقایسه کنی." },
  online: { title: "سفارش‌های آنلاین", eyebrow: "اتصال فروشگاه", help: "کانال فروش را متصل کن و سفارش‌های جدید را قبل از تایید بررسی کن." },
};

type InvoiceDraftItem = {
  id: string;
  variantId: number;
  variantName: string;
  quantity: number;
  unitPriceRial: number;
  discountAmountRial: number;
  estimatedCostRial: number;
};

type PurchaseDraftItem = {
  id: string;
  variantId: number;
  variantName: string;
  quantity: number;
  unitCostRial: number;
  extraCostRial: number;
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
    action: "شروع فروش",
  },
  {
    key: "products",
    title: "کالاها",
    description: "تعریف کالا، واحدها و قیمت‌های پایه",
    icon: "ک",
    accent: "blue",
    status: "فعال",
    action: "مدیریت کالا",
  },
  {
    key: "purchase",
    title: "خرید",
    description: "ثبت خرید از تأمین‌کننده و قیمت تمام‌شده",
    icon: "خ",
    accent: "amber",
    status: "فعال",
    action: "ثبت خرید",
  },
  {
    key: "inventory",
    title: "انبار",
    description: "موجودی، میانگین موزون و نقطه سفارش",
    icon: "ا",
    accent: "green",
    status: "فعال",
    action: "نمایش انبار",
  },
  {
    key: "ledger",
    title: "دفتر حساب",
    description: "حساب مشتریان، تأمین‌کنندگان و تسویه‌ها",
    icon: "د",
    accent: "violet",
    status: "فعال",
    action: "دفتر حساب",
  },
  {
    key: "cheques",
    title: "چک‌ها",
    description: "چک‌های دریافتی، پرداختی و سررسیدها",
    icon: "چ",
    accent: "rose",
    status: "فعال",
    action: "مدیریت چک",
  },
  {
    key: "reports",
    title: "گزارش‌ها",
    description: "گزارش فروش، سود، بدهکاران و عملکرد روز",
    icon: "گ",
    accent: "slate",
    status: "فعال",
    action: "گزارش‌ها",
  },
];

moduleCards.push({
  key: "online",
  title: "اتصال آنلاین",
  description: "کانال‌ها، سفارش‌های سایت و همگام‌سازی اولیه",
  icon: "آ",
  accent: "teal",
  status: "فعال",
  action: "مدیریت آنلاین",
});

const latinDigits = "0123456789";
const persianDigits = "۰۱۲۳۴۵۶۷۸۹";
const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
const jalaliMonths = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];

function toEnglishDigits(value: string) {
  return value.replace(/[۰-۹٠-٩]/g, (digit) => {
    const persianIndex = persianDigits.indexOf(digit);
    if (persianIndex >= 0) return latinDigits[persianIndex];
    const arabicIndex = arabicDigits.indexOf(digit);
    return arabicIndex >= 0 ? latinDigits[arabicIndex] : digit;
  });
}

function toPersianDigits(value: string | number) {
  return String(value).replace(/\d/g, (digit) => persianDigits[Number(digit)]);
}

function parseLocalizedNumber(value: FormDataEntryValue | string | null) {
  const normalized = toEnglishDigits(String(value ?? ""))
    .replace(/[,\s٬،]/g, "")
    .replace("/", ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function rialToToman(value: number) {
  return Math.round(Math.max(0, value) / 10);
}

function tomanToRial(value: number) {
  return Math.round(Math.max(0, value) * 10);
}

function moneyInputValue(valueRial: number) {
  return valueRial > 0 ? toPersianDigits(rialToToman(valueRial).toLocaleString("fa-IR")) : "";
}

function formatRial(value: number) {
  return `${rialToToman(value).toLocaleString("fa-IR")} تومان`;
}

function formatDecimal(value: number | string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString("fa-IR") : String(value);
}

function normalizeMoney(value: FormDataEntryValue | string | null) {
  return tomanToRial(parseLocalizedNumber(value));
}

function normalizeDecimal(value: FormDataEntryValue | null) {
  const parsed = Number(toEnglishDigits(String(value ?? "0")).replace(",", "."));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function currentJalaliDate() {
  const parts = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    timeZone: "Asia/Tehran",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    toEnglishDigits(parts.find((item) => item.type === type)?.value ?? "");
  return `${part("year")}/${part("month").padStart(2, "0")}/${part("day").padStart(2, "0")}`;
}

function splitJalaliDate(value: string) {
  const [fallbackYear, fallbackMonth, fallbackDay] = currentJalaliDate().split("/");
  const [year = fallbackYear, month = fallbackMonth, day = fallbackDay] = toEnglishDigits(value).split("/");
  return {
    year: Number(year) || Number(fallbackYear),
    month: Math.min(12, Math.max(1, Number(month) || Number(fallbackMonth))),
    day: Math.min(31, Math.max(1, Number(day) || Number(fallbackDay))),
  };
}

function buildJalaliDate(year: number, month: number, day: number) {
  return `${year}/${String(month).padStart(2, "0")}/${String(day).padStart(2, "0")}`;
}

function currentLocalTime() {
  const parts = new Intl.DateTimeFormat("fa-IR", {
    timeZone: "Asia/Tehran",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date());
  const part = (type: "hour" | "minute") =>
    toEnglishDigits(parts.find((item) => item.type === type)?.value ?? "00").padStart(2, "0");
  return `${part("hour")}:${part("minute")}`;
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

function JalaliDateField({
  label,
  value,
  onChange,
  required = false,
}: {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const selected = splitJalaliDate(value);
  const days = Array.from({ length: selected.month <= 6 ? 31 : 30 }, (_, index) => index + 1);
  const currentYear = splitJalaliDate(currentJalaliDate()).year;
  const years = Array.from({ length: 5 }, (_, index) => currentYear - 2 + index);

  function updateDate(patch: Partial<{ year: number; month: number; day: number }>) {
    const next = { ...selected, ...patch };
    const maxDay = next.month <= 6 ? 31 : 30;
    onChange(buildJalaliDate(next.year, next.month, Math.min(next.day, maxDay)));
  }

  return (
    <label className="date-field">
      {label}
      <button type="button" className="date-trigger" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span>{toPersianDigits(value)}</span>
        <small>انتخاب تاریخ</small>
      </button>
      {required ? <input className="sr-only" value={value} onChange={(event) => onChange(event.target.value)} required tabIndex={-1} /> : null}
      {open ? (
        <div className="date-popover" role="dialog" aria-label="انتخاب تاریخ شمسی">
          <div className="date-controls">
            <select value={selected.year} onChange={(event) => updateDate({ year: Number(event.target.value) })}>
              {years.map((year) => (
                <option value={year} key={year}>
                  {toPersianDigits(year)}
                </option>
              ))}
            </select>
            <select value={selected.month} onChange={(event) => updateDate({ month: Number(event.target.value) })}>
              {jalaliMonths.map((month, index) => (
                <option value={index + 1} key={month}>
                  {month}
                </option>
              ))}
            </select>
          </div>
          <div className="date-days">
            {days.map((day) => (
              <button
                type="button"
                className={day === selected.day ? "active" : ""}
                key={day}
                onClick={() => {
                  updateDate({ day });
                  setOpen(false);
                }}
              >
                {toPersianDigits(day)}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </label>
  );
}

function AdminApp({ onOpenStore }: { onOpenStore: () => void }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [view, setView] = useState<AppView>("dashboard");
  const [user, setUser] = useState<User | null>(null);
  const [loginError, setLoginError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const sectionHeadingRef = useRef<HTMLHeadingElement>(null);

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

  useEffect(() => {
    if (status !== "authenticated") return;
    window.scrollTo({ top: 0, behavior: "auto" });
    const frame = window.requestAnimationFrame(() => sectionHeadingRef.current?.focus({ preventScroll: true }));
    return () => window.cancelAnimationFrame(frame);
  }, [status, view]);

  function navigateView(target: AppView) {
    setMobileNavOpen(false);
    setView(target);
  }

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

  function renderNavigation() {
    return (
      <nav className="sidebar-nav" aria-label="بخش‌های پنل مدیریت">
        <span className="sidebar-section-label">مدیریت روزانه</span>
        <button type="button" className={`sidebar-link ${view === "dashboard" ? "active" : ""}`} aria-current={view === "dashboard" ? "page" : undefined} onClick={() => navigateView("dashboard")}>
          <DashboardRounded aria-hidden="true" />
          خانه مدیریت
        </button>
        {moduleCards.map((card) => {
          const target = card.key as AppView;
          const Icon = card.key === "sales" ? PointOfSaleRounded :
            card.key === "products" ? Inventory2Rounded :
            card.key === "purchase" ? ShoppingCartCheckoutRounded :
            card.key === "inventory" ? FactCheckRounded :
            card.key === "ledger" ? AccountBalanceWalletRounded :
            card.key === "cheques" ? PaymentsRounded :
            card.key === "reports" ? AnalyticsRounded : SyncRounded;
          return (
            <button
              type="button"
              className={`sidebar-link accent-${card.accent} ${view === target ? "active" : ""}`}
              aria-current={view === target ? "page" : undefined}
              onClick={() => navigateView(target)}
              key={card.key}
            >
              <Icon aria-hidden="true" />
              {card.title}
            </button>
          );
        })}
      </nav>
    );
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
          <h1 id="login-title">مدیریت فروشگاه، ساده و سریع</h1>
          <p className="intro">
            برای ورود به داشبورد و مدیریت فروش، خرید و موجودی حساب مدیر را وارد کنید.
          </p>
        </section>

        <section className="login-panel" aria-label="فرم ورود">
          <Button className="back-to-store" variant="text" startIcon={<StorefrontRounded />} onClick={onOpenStore}>
            بازگشت به فروشگاه
          </Button>
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
      <aside className="app-sidebar" aria-label="ناوبری اصلی">
        <div className="sidebar-brand">
          <span className="sidebar-logo" aria-hidden="true">ح</span>
          <div><strong>حبوباتین</strong><small>پنل مدیریت</small></div>
        </div>
        {renderNavigation()}
      </aside>
      <Drawer
        anchor="right"
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        className="mobile-admin-drawer"
        ModalProps={{ keepMounted: true }}
        slotProps={{ paper: { component: "aside", "aria-label": "منوی بخش‌های مدیریت" } }}
      >
        <div className="mobile-drawer-header">
          <div className="sidebar-brand"><span className="sidebar-logo" aria-hidden="true">ح</span><div><strong>حبوباتین</strong><small>پنل مدیریت</small></div></div>
          <IconButton aria-label="بستن منوی مدیریت" onClick={() => setMobileNavOpen(false)}><CloseRounded /></IconButton>
        </div>
        {renderNavigation()}
      </Drawer>
      <div className="app-main">
      <header className="topbar">
        <div>
          <p className="eyebrow">{viewMeta[view].eyebrow}</p>
          <h1 ref={sectionHeadingRef} tabIndex={-1}>{viewMeta[view].title}</h1>
          <span className="topbar-user">سلام {displayName}</span>
        </div>
        <div className="topbar-actions">
          <IconButton className="mobile-nav-trigger" aria-label="باز کردن منوی بخش‌های مدیریت" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen(true)}><MenuRounded /></IconButton>
          <Button variant="outlined" startIcon={<StorefrontRounded />} onClick={onOpenStore}>مشاهده فروشگاه</Button>
          <button className="ghost-button" type="button" onClick={handleLogout}>خروج</button>
        </div>
      </header>

      {view !== "dashboard" ? (
        <aside className="admin-guide" aria-label="راهنمای این بخش">
          <HelpOutlineRounded />
          <div><strong>از کجا شروع کنم؟</strong><span>{viewMeta[view].help}</span></div>
        </aside>
      ) : null}

      {view === "sales" ? <SalesView onBack={() => navigateView("dashboard")} /> : null}
      {view === "purchase" ? <PurchaseView onBack={() => navigateView("dashboard")} onOpenInventory={() => navigateView("inventory")} /> : null}
      {view === "inventory" ? <InventoryView onBack={() => navigateView("dashboard")} /> : null}
      {view === "products" ? <ProductsView onBack={() => navigateView("dashboard")} /> : null}
      {view === "ledger" ? <LedgerView onBack={() => navigateView("dashboard")} /> : null}
      {view === "cheques" ? <ChequesView onBack={() => navigateView("dashboard")} /> : null}
      {view === "reports" ? <ReportsView onBack={() => navigateView("dashboard")} /> : null}
      {view === "online" ? <OnlineView onBack={() => navigateView("dashboard")} /> : null}
      {view === "dashboard" ? (
        <DashboardView
          onOpenSales={() => navigateView("sales")}
          onOpenPurchase={() => navigateView("purchase")}
          onOpenInventory={() => navigateView("inventory")}
          onOpenProducts={() => navigateView("products")}
          onOpenLedger={() => navigateView("ledger")}
          onOpenCheques={() => navigateView("cheques")}
          onOpenReports={() => navigateView("reports")}
          onOpenOnline={() => navigateView("online")}
        />
      ) : null}
      </div>
    </main>
  );
}

function DashboardView({
  onOpenSales,
  onOpenPurchase,
  onOpenInventory,
  onOpenProducts,
  onOpenLedger,
  onOpenCheques,
  onOpenReports,
  onOpenOnline,
}: {
  onOpenSales: () => void;
  onOpenPurchase: () => void;
  onOpenInventory: () => void;
  onOpenProducts: () => void;
  onOpenLedger: () => void;
  onOpenCheques: () => void;
  onOpenReports: () => void;
  onOpenOnline: () => void;
}) {
  const [snapshot, setSnapshot] = useState<{ journal: DailyJournal; inventory: InventoryReport; dues: Dues } | null>(null);
  const [snapshotStatus, setSnapshotStatus] = useState<"loading" | "ready" | "error">("loading");
  const [snapshotError, setSnapshotError] = useState("");

  async function loadSnapshot() {
    setSnapshotStatus("loading");
    setSnapshotError("");
    const today = currentJalaliDate();
    try {
      const [journal, inventory, dues] = await Promise.all([
        api.dailyJournal(today),
        api.inventoryReport(),
        api.dues(today),
      ]);
      setSnapshot({ journal, inventory, dues });
      setSnapshotStatus("ready");
    } catch (error) {
      setSnapshotError(error instanceof Error ? error.message : "خلاصه وضعیت فروشگاه دریافت نشد.");
      setSnapshotStatus("error");
    }
  }

  useEffect(() => {
    void loadSnapshot();
  }, []);

  const actions: Array<{ key: AppView; title: string; description: string; icon: ReactNode; color: string; action: () => void }> = [
    { key: "sales", title: "ثبت فروش", description: "فاکتور و پرداخت مشتری", icon: <PointOfSaleRounded />, color: "#087f5b", action: onOpenSales },
    { key: "purchase", title: "ثبت خرید", description: "خرید از تامین‌کننده", icon: <ShoppingCartCheckoutRounded />, color: "#ef8b24", action: onOpenPurchase },
    { key: "inventory", title: "کنترل انبار", description: "موجودی و نقطه سفارش", icon: <FactCheckRounded />, color: "#3f8f4f", action: onOpenInventory },
    { key: "products", title: "کالاها", description: "تعریف محصول و قیمت", icon: <Inventory2Rounded />, color: "#2f80ed", action: onOpenProducts },
    { key: "ledger", title: "دفتر حساب", description: "مانده حساب اشخاص", icon: <AccountBalanceWalletRounded />, color: "#7e57c2", action: onOpenLedger },
    { key: "cheques", title: "چک‌ها", description: "سررسید و وضعیت چک", icon: <PaymentsRounded />, color: "#e35d6a", action: onOpenCheques },
    { key: "reports", title: "گزارش‌ها", description: "فروش، سود و نقدینگی", icon: <AnalyticsRounded />, color: "#40637a", action: onOpenReports },
    { key: "online", title: "سفارش آنلاین", description: "بررسی سفارش‌های سایت", icon: <SyncRounded />, color: "#00a2a5", action: onOpenOnline },
  ];

  return (
    <Box className="material-dashboard">
      <Box component="section" className="dashboard-welcome">
        <Box>
          <Chip icon={<AdminPanelSettingsRounded />} label="همه بخش‌ها آماده‌اند" color="primary" variant="outlined" />
          <Typography variant="h4" component="h2">امروز چه کاری انجام می‌دهی؟</Typography>
          <Typography color="text.secondary">کارهای پرتکرار را مستقیم شروع کن؛ وضعیت فروشگاه هم در همین صفحه خلاصه شده است.</Typography>
        </Box>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
          <Button variant="contained" size="large" startIcon={<PointOfSaleRounded />} onClick={onOpenSales}>فروش جدید</Button>
          <Button variant="outlined" size="large" startIcon={<ShoppingCartCheckoutRounded />} onClick={onOpenPurchase}>خرید جدید</Button>
        </Stack>
      </Box>

      <Box component="section" className="quick-start" aria-label="شروع سریع">
        <Box className="quick-start-title"><HelpOutlineRounded /><Box><Typography sx={{ fontWeight: 900 }}>شروع سریع برای کاربر تازه‌کار</Typography><Typography variant="body2" color="text.secondary">برای یک چرخه کامل روزانه، این سه مرحله را به‌ترتیب انجام بده.</Typography></Box></Box>
        <Box className="quick-start-steps">
          <button type="button" onClick={onOpenProducts}><span>۱</span><div><strong>کالا را تعریف کن</strong><small>نام، واحد و قیمت پایه</small></div><ArrowBackRounded /></button>
          <button type="button" onClick={onOpenPurchase}><span>۲</span><div><strong>موجودی وارد کن</strong><small>ثبت خرید از تامین‌کننده</small></div><ArrowBackRounded /></button>
          <button type="button" onClick={onOpenSales}><span>۳</span><div><strong>فروش را ثبت کن</strong><small>فاکتور و روش پرداخت</small></div><ArrowBackRounded /></button>
        </Box>
      </Box>

      <Box component="section" aria-labelledby="dashboard-status-title" aria-busy={snapshotStatus === "loading"}>
        <Box className="dashboard-section-heading">
          <Box><Typography id="dashboard-status-title" variant="h5">وضعیت امروز</Typography><Typography color="text.secondary">آخرین داده ثبت‌شده تا {toPersianDigits(currentJalaliDate())}</Typography></Box>
          {snapshotStatus === "ready" ? <Button size="small" startIcon={<RefreshRounded />} onClick={() => void loadSnapshot()}>به‌روزرسانی</Button> : null}
        </Box>
        {snapshotStatus === "loading" ? (
          <Box className="dashboard-snapshot-state" role="status"><CircularProgress size={28} /><Typography>در حال دریافت وضعیت واقعی فروشگاه...</Typography></Box>
        ) : null}
        {snapshotStatus === "error" ? (
          <Alert severity="error" className="dashboard-snapshot-state" action={<Button color="inherit" onClick={() => void loadSnapshot()}>تلاش دوباره</Button>}>
            {snapshotError}
          </Alert>
        ) : null}
        {snapshotStatus === "ready" && snapshot ? (
          <Box className="dashboard-kpis">
            <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">فروش امروز</Typography><PointOfSaleRounded color="primary" /></Stack><Typography variant="h5">{formatRial(snapshot.journal.sales_total_rial)}</Typography><Chip size="small" label={`${toPersianDigits(snapshot.journal.invoice_count.toLocaleString("fa-IR"))} فاکتور`} color="primary" variant="outlined" /></CardContent></Card>
            <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">دریافت واقعی</Typography><ReceiptLongRounded color="info" /></Stack><Typography variant="h5">{formatRial(snapshot.journal.received_total_rial)}</Typography><LinearProgress aria-label="نسبت مبلغ دریافت‌شده به فروش امروز" variant="determinate" value={snapshot.journal.sales_total_rial > 0 ? Math.min(100, snapshot.journal.received_total_rial / snapshot.journal.sales_total_rial * 100) : 0} sx={{ mt: 1.5 }} /></CardContent></Card>
            <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">هشدار موجودی</Typography><Inventory2Rounded color="warning" /></Stack><Typography variant="h5">{toPersianDigits(snapshot.inventory.low_stock_count.toLocaleString("fa-IR"))} کالا</Typography><Button size="small" onClick={onOpenInventory}>{snapshot.inventory.low_stock_count ? "بررسی موجودی" : "انبار بدون هشدار"}</Button></CardContent></Card>
            <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">چک‌های سررسیدشده</Typography><PaymentsRounded color="secondary" /></Stack><Typography variant="h5">{toPersianDigits(snapshot.dues.pending_cheques.length.toLocaleString("fa-IR"))} چک</Typography><Button size="small" onClick={onOpenCheques}>{snapshot.dues.pending_cheques.length ? "پیگیری چک‌ها" : "بدون سررسید معوق"}</Button></CardContent></Card>
          </Box>
        ) : null}
      </Box>

      <Box component="section" className="dashboard-modules">
        <Box className="dashboard-section-heading"><Box><Typography variant="h5">بخش‌های مدیریت</Typography><Typography color="text.secondary">هر کارت تو را مستقیم به کار موردنظر می‌برد.</Typography></Box><Chip label="۸ بخش فعال" /></Box>
        <Box className="material-module-grid">
          {actions.map((item) => (
            <Card key={item.key} className="material-module-card" style={{ "--module-color": item.color } as CSSProperties}>
              <CardActionArea onClick={item.action}>
                <CardContent>
                  <Box className="material-module-icon">{item.icon}</Box>
                  <Typography variant="h6">{item.title}</Typography>
                  <Typography variant="body2" color="text.secondary">{item.description}</Typography>
                  <Box className="material-module-link">ورود به بخش <ArrowBackRounded /></Box>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Box>
      </Box>
    </Box>
  );
}

function PurchaseView({ onBack, onOpenInventory }: { onBack: () => void; onOpenInventory: () => void }) {
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [variantsStatus, setVariantsStatus] = useState<"loading" | "ready" | "error">("loading");
  const [variantsError, setVariantsError] = useState("");
  const [items, setItems] = useState<PurchaseDraftItem[]>([]);
  const [supplierName, setSupplierName] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(currentJalaliDate);
  const [purchaseTime, setPurchaseTime] = useState(currentLocalTime());
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [extraCost, setExtraCost] = useState(0);
  const [paidAmount, setPaidAmount] = useState(0);
  const [note, setNote] = useState("");
  const [submitStatus, setSubmitStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [submitMessage, setSubmitMessage] = useState("");
  const [lastPurchase, setLastPurchase] = useState<PurchaseInvoice | null>(null);
  const [itemVariantId, setItemVariantId] = useState("");
  const [itemQuantity, setItemQuantity] = useState("");
  const [itemUnitCost, setItemUnitCost] = useState("");
  const [itemExtraCost, setItemExtraCost] = useState("");
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [itemNotice, setItemNotice] = useState("");

  const loadVariants = () => {
    setVariantsStatus("loading");
    setVariantsError("");
    return api
      .productVariants()
      .then((result) => {
        setVariants(result);
        setVariantsStatus("ready");
      })
      .catch((error) => {
        setVariantsError(error instanceof Error ? error.message : "کالاها دریافت نشدند.");
        setVariantsStatus("error");
      });
  };

  useEffect(() => {
    void loadVariants();
  }, []);

  const subtotal = useMemo(() => {
    return items.reduce((sum, item) => sum + Math.round(item.quantity * item.unitCostRial) + item.extraCostRial, 0);
  }, [items]);
  const total = Math.max(0, subtotal + extraCost - invoiceDiscount);
  const dueTotal = Math.max(0, total - paidAmount);

  function handleAddPurchaseItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const variantId = Number(itemVariantId);
    const variant = variants.find((item) => item.id === variantId);
    const quantity = normalizeDecimal(itemQuantity);
    const unitCostRial = normalizeMoney(itemUnitCost);
    const extraCostRial = normalizeMoney(itemExtraCost);

    if (!variant || quantity <= 0 || unitCostRial <= 0) {
      setItemNotice("کالا، مقدار مثبت و قیمت خرید واحد را کامل و درست وارد کنید.");
      return;
    }

    const nextItem = { id: editingItemId ?? crypto.randomUUID(), variantId, variantName: variant.name, quantity, unitCostRial, extraCostRial };
    setItems((current) => editingItemId === null ? [...current, nextItem] : current.map((item) => item.id === editingItemId ? nextItem : item));
    setEditingItemId(null);
    setItemVariantId("");
    setItemQuantity("");
    setItemUnitCost("");
    setItemExtraCost("");
    setItemNotice("");
    setSubmitStatus("idle");
    setSubmitMessage("");
  }

  function editPurchaseItem(item: PurchaseDraftItem) {
    setEditingItemId(item.id);
    setItemVariantId(String(item.variantId));
    setItemQuantity(String(item.quantity));
    setItemUnitCost(moneyInputValue(item.unitCostRial));
    setItemExtraCost(moneyInputValue(item.extraCostRial));
    setItemNotice("");
  }

  function resetPurchaseItemForm() {
    setEditingItemId(null);
    setItemVariantId("");
    setItemQuantity("");
    setItemUnitCost("");
    setItemExtraCost("");
    setItemNotice("");
  }

  async function handleSubmitPurchase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitStatus("loading");
    setSubmitMessage("");

    if (!supplierName.trim()) {
      setSubmitStatus("error");
      setSubmitMessage("نام تأمین‌کننده را وارد کنید.");
      return;
    }

    if (!items.length) {
      setSubmitStatus("error");
      setSubmitMessage("حداقل یک کالا به فاکتور خرید اضافه کنید.");
      return;
    }

    if (invoiceDiscount > subtotal + extraCost) {
      setSubmitStatus("error");
      setSubmitMessage("تخفیف فاکتور نمی‌تواند از جمع خرید و هزینه‌های جانبی بیشتر باشد.");
      return;
    }

    if (paidAmount > total) {
      setSubmitStatus("error");
      setSubmitMessage("مبلغ پرداخت‌شده نمی‌تواند از مبلغ نهایی فاکتور بیشتر باشد.");
      return;
    }

    try {
      const purchase = await api.createPurchaseInvoice({
        supplier_name: supplierName.trim(),
        jalali_date: purchaseDate,
        local_time: purchaseTime,
        discount_amount_rial: invoiceDiscount,
        extra_cost_rial: extraCost,
        paid_total_rial: paidAmount,
        note: note.trim() || undefined,
        items: items.map((item) => ({
          variant_id: item.variantId,
          quantity: item.quantity,
          unit_cost_rial: item.unitCostRial,
          extra_cost_rial: item.extraCostRial,
        })),
      });

      setLastPurchase(purchase);
      setSubmitStatus("success");
      setSubmitMessage(`فاکتور خرید ${purchase.invoice_number ?? purchase.id} با موفقیت ثبت شد.`);
      setItems([]);
      setInvoiceDiscount(0);
      setExtraCost(0);
      setPaidAmount(0);
      setNote("");
      setSupplierName("");
      resetPurchaseItemForm();
    } catch (error) {
      setSubmitStatus("error");
      setSubmitMessage(error instanceof Error ? error.message : "ثبت خرید انجام نشد.");
    }
  }

  return (
    <section className="sales-workspace purchase-workspace" aria-label="ثبت خرید">
      <div className="sales-header purchase-header">
        <div>
          <p className="eyebrow">خرید و تأمین کالا</p>
          <h2>ثبت فاکتور خرید و به‌روزرسانی موجودی</h2>
          <p className="purchase-guide">ابتدا اقلام را اضافه کنید، سپس اطلاعات فاکتور و مبلغ پرداختی را بررسی و ثبت کنید.</p>
        </div>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} className="purchase-header-actions">
          <Button variant="outlined" startIcon={<Inventory2Rounded />} onClick={onOpenInventory}>نمایش انبار</Button>
          <Button variant="text" startIcon={<ArrowBackRounded />} onClick={onBack}>بازگشت به داشبورد</Button>
        </Stack>
      </div>

      <div className="purchase-layout">
        <section className="sale-panel purchase-invoice-panel">
          <div className="purchase-section-heading"><div><ReceiptLongRounded /><div><h3>اطلاعات فاکتور</h3><p>مبالغ را به تومان وارد کنید.</p></div></div><Chip label={`${items.length.toLocaleString("fa-IR")} ردیف`} color="primary" variant="outlined" /></div>
          <form className="purchase-invoice-form" onSubmit={handleSubmitPurchase} noValidate>
            <TextField label="نام تأمین‌کننده" value={supplierName} onChange={(event) => setSupplierName(event.target.value)} placeholder="مثلاً عمده‌فروش بازار" required disabled={submitStatus === "loading"} />
            <JalaliDateField label="تاریخ شمسی" value={purchaseDate} onChange={setPurchaseDate} required />
            <TextField label="ساعت" value={purchaseTime} onChange={(event) => setPurchaseTime(event.target.value)} placeholder="14:30" required disabled={submitStatus === "loading"} slotProps={{ htmlInput: { dir: "ltr" } }} />
            <TextField label="پرداخت‌شده (تومان)" value={moneyInputValue(paidAmount)} onChange={(event) => setPaidAmount(normalizeMoney(event.target.value))} inputMode="numeric" disabled={submitStatus === "loading"} />
            <TextField label="تخفیف فاکتور (تومان)" value={moneyInputValue(invoiceDiscount)} onChange={(event) => setInvoiceDiscount(normalizeMoney(event.target.value))} inputMode="numeric" disabled={submitStatus === "loading"} />
            <TextField label="هزینه جانبی فاکتور (تومان)" value={moneyInputValue(extraCost)} onChange={(event) => setExtraCost(normalizeMoney(event.target.value))} inputMode="numeric" disabled={submitStatus === "loading"} />
            <TextField className="purchase-note" label="یادداشت (اختیاری)" value={note} onChange={(event) => setNote(event.target.value)} disabled={submitStatus === "loading"} multiline minRows={2} />

            <div className="invoice-summary purchase-summary" aria-label="جمع فاکتور خرید">
              <div>
                <span>جمع ردیف‌ها</span>
                <strong>{formatRial(subtotal)}</strong>
              </div>
              <div>
                <span>مبلغ نهایی</span>
                <strong>{formatRial(total)}</strong>
              </div>
              <div>
                <span>مانده تأمین‌کننده</span>
                <strong className={dueTotal > 0 ? "text-danger" : "text-ok"}>{formatRial(dueTotal)}</strong>
              </div>
            </div>

            {submitMessage ? <Alert className="purchase-message" severity={submitStatus === "success" ? "success" : "error"}>{submitMessage}</Alert> : null}

            <Button type="submit" className="purchase-submit" variant="contained" size="large" disabled={submitStatus === "loading" || items.length === 0} startIcon={submitStatus === "loading" ? <CircularProgress size={18} color="inherit" /> : <ReceiptLongRounded />}>{submitStatus === "loading" ? "در حال ثبت…" : "ثبت فاکتور خرید"}</Button>
          </form>
        </section>

        <aside className="sale-panel purchase-items-panel">
          <div className="mini-section-header">
            <div><h3>{editingItemId === null ? "افزودن کالا" : "ویرایش ردیف"}</h3><span>مقدار و بهای خرید این ردیف</span></div>
            <Chip size="small" label={`${variants.length.toLocaleString("fa-IR")} گونه`} />
          </div>

          {variantsStatus === "loading" ? <div className="record-state"><CircularProgress size={26} /><span>در حال دریافت کالاها…</span></div> : null}
          {variantsStatus === "error" ? <Alert severity="error" action={<Button color="inherit" onClick={() => void loadVariants()}>تلاش دوباره</Button>}>{variantsError}</Alert> : null}
          {variantsStatus === "ready" && variants.length === 0 ? <div className="record-state"><Inventory2Rounded /><strong>هنوز گونه کالایی ثبت نشده است</strong><span>ابتدا از بخش کالاها یک گونه بسازید.</span></div> : null}

          {variantsStatus === "ready" && variants.length > 0 ? (
            <form className="purchase-item-form" onSubmit={handleAddPurchaseItem} noValidate>
              {itemNotice ? <Alert severity="error" onClose={() => setItemNotice("")}>{itemNotice}</Alert> : null}
              <TextField select label="گونه کالا" value={itemVariantId} onChange={(event) => setItemVariantId(event.target.value)} required><MenuItem value="">انتخاب گونه</MenuItem>{variants.map((variant) => <MenuItem value={String(variant.id)} key={variant.id}>{variant.name}</MenuItem>)}</TextField>
              <div className="purchase-item-fields">
                <TextField label="مقدار" value={itemQuantity} onChange={(event) => setItemQuantity(event.target.value)} inputMode="decimal" required />
                <TextField label="قیمت واحد (تومان)" value={itemUnitCost} onChange={(event) => setItemUnitCost(event.target.value)} inputMode="numeric" required />
              </div>
              <TextField label="هزینه جانبی ردیف (تومان)" value={itemExtraCost} onChange={(event) => setItemExtraCost(event.target.value)} inputMode="numeric" helperText="اختیاری؛ مثل حمل یا بسته‌بندی" />
              <div className="purchase-item-actions"><Button type="submit" variant="contained" size="large" startIcon={editingItemId === null ? <AddRounded /> : <EditRounded />} disabled={!itemVariantId || !itemQuantity.trim() || !itemUnitCost.trim()}>{editingItemId === null ? "افزودن به فاکتور" : "ذخیره ردیف"}</Button>{editingItemId !== null ? <Button type="button" size="large" onClick={resetPurchaseItemForm} startIcon={<CloseRounded />}>انصراف</Button> : null}</div>
            </form>
          ) : null}

          <div className="invoice-items">
            <div className="mini-section-header">
              <h3>اقلام خرید</h3>
              <span>{items.length.toLocaleString("fa-IR")} ردیف</span>
            </div>
            {items.length === 0 ? (
              <div className="record-state purchase-empty"><ShoppingCartCheckoutRounded /><strong>هنوز ردیفی اضافه نشده است</strong><span>از فرم بالا، نخستین کالای خرید را اضافه کنید.</span></div>
            ) : (
              items.map((item) => {
                const lineTotal = Math.round(item.quantity * item.unitCostRial) + item.extraCostRial;
                return (
                  <article className="invoice-item purchase-invoice-item" key={item.id}>
                    <div>
                      <strong>{item.variantName}</strong>
                      <span>{item.quantity.toLocaleString("fa-IR")} × {formatRial(item.unitCostRial)}{item.extraCostRial ? ` + ${formatRial(item.extraCostRial)} هزینه` : ""}</span>
                    </div>
                    <div className="purchase-invoice-item-end">
                      <strong>{formatRial(lineTotal)}</strong>
                      <div><Button size="small" startIcon={<EditRounded />} onClick={() => editPurchaseItem(item)}>ویرایش</Button><Button size="small" color="error" startIcon={<DeleteOutlineRounded />} onClick={() => { setItems((current) => current.filter((draft) => draft.id !== item.id)); if (editingItemId === item.id) resetPurchaseItemForm(); }}>حذف</Button></div>
                    </div>
                  </article>
                );
              })
            )}
          </div>
          {lastPurchase ? <Alert severity="success">آخرین خرید ثبت‌شده: {lastPurchase.invoice_number ?? lastPurchase.id}</Alert> : null}
        </aside>
      </div>
    </section>
  );
}

function InventoryView({ onBack }: { onBack: () => void }) {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [transactionVariantId, setTransactionVariantId] = useState("");
  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);
  const [reorderLevel, setReorderLevel] = useState("");
  const [reorderError, setReorderError] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");

  const load = async () => {
    setStatus("loading");
    setError("");
    try {
      const [nextItems, nextTransactions] = await Promise.all([api.inventory(), api.inventoryTransactions({ limit: 100 })]);
      setItems(nextItems);
      setTransactions(nextTransactions);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "اطلاعات انبار دریافت نشد.");
      setStatus("error");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const totalValue = items.reduce((sum, item) => sum + Number(item.quantity_on_hand) * item.weighted_average_cost_rial, 0);
  const lowStockCount = items.filter((item) => item.reorder_level != null && Number(item.quantity_on_hand) <= Number(item.reorder_level)).length;
  const filteredItems = items.filter((item) => {
    const matchesSearch = item.variant_name.toLocaleLowerCase("fa").includes(search.trim().toLocaleLowerCase("fa"));
    const isLow = item.reorder_level != null && Number(item.quantity_on_hand) <= Number(item.reorder_level);
    return matchesSearch && (!lowStockOnly || isLow);
  });
  const filteredTransactions = transactions.filter((transaction) => !transactionVariantId || transaction.variant_id === Number(transactionVariantId));

  function openReorderDialog(item: InventoryItem) {
    setEditingItem(item);
    setReorderLevel(item.reorder_level == null ? "" : String(item.reorder_level));
    setReorderError("");
    setNotice("");
  }

  async function saveReorderLevel() {
    if (!editingItem) return;
    const normalized = toEnglishDigits(reorderLevel).replace(/[٬،,\s]/g, "").replace("/", ".");
    const value = normalized === "" ? null : Number(normalized);
    if (value !== null && (!Number.isFinite(value) || value < 0)) {
      setReorderError("یک عدد صفر یا بزرگ‌تر وارد کنید؛ برای حذف نقطه سفارش، کادر را خالی بگذارید.");
      return;
    }
    setSaving(true);
    setReorderError("");
    try {
      const updated = await api.updateInventory(editingItem.id, { reorder_level: value });
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setEditingItem(null);
      setNotice("نقطه سفارش ذخیره شد.");
    } catch (err) {
      setReorderError(err instanceof Error ? err.message : "ذخیره نقطه سفارش انجام نشد.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="sales-workspace inventory-workspace" aria-label="انبار">
      <div className="sales-header">
        <div>
          <p className="eyebrow">کنترل انبار</p>
          <h2>موجودی و گردش کالاها</h2>
          <p className="inventory-guide">موجودی از ثبت و لغو خرید محاسبه می‌شود؛ فقط نقطه سفارش را برای هشدار کمبود تنظیم کنید.</p>
        </div>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} className="inventory-header-actions">
          <Button variant="outlined" startIcon={<RefreshRounded />} onClick={() => void load()} disabled={status === "loading"}>به‌روزرسانی</Button>
          <Button variant="text" startIcon={<ArrowBackRounded />} onClick={onBack}>بازگشت به داشبورد</Button>
        </Stack>
      </div>

      <section className="inventory-summary">
        <div><span>گونه‌های انبار</span><strong>{items.length.toLocaleString("fa-IR")}</strong></div>
        <div><span>ارزش تقریبی موجودی</span><strong>{formatRial(totalValue)}</strong></div>
        <div className={lowStockCount ? "inventory-kpi-alert" : ""}><span>نیازمند سفارش</span><strong>{lowStockCount.toLocaleString("fa-IR")}</strong></div>
      </section>

      {notice ? <Alert severity="success" onClose={() => setNotice("")}>{notice}</Alert> : null}
      {status === "loading" ? (
        <section className="sale-panel inventory-state" aria-live="polite"><CircularProgress size={28} /><div><strong>در حال آماده‌سازی انبار</strong><span>موجودی و آخرین گردش‌ها دریافت می‌شوند.</span></div></section>
      ) : null}
      {status === "error" ? <Alert severity="error" action={<Button color="inherit" onClick={() => void load()}>تلاش دوباره</Button>}>{error}</Alert> : null}

      {status === "ready" ? (
        <div className="inventory-sections">
          <section className="sale-panel inventory-panel" aria-labelledby="inventory-list-heading">
            <div className="inventory-section-heading">
              <div><h3 id="inventory-list-heading">وضعیت کالاها</h3><p>نقطه سفارش، مرز هشدار برای خرید بعدی است.</p></div>
              <Chip label={`کم‌موجود (${lowStockCount.toLocaleString("fa-IR")})`} color={lowStockOnly ? "warning" : "default"} variant={lowStockOnly ? "filled" : "outlined"} onClick={() => setLowStockOnly((value) => !value)} />
            </div>
            <TextField fullWidth label="جست‌وجوی کالا" value={search} onChange={(event) => setSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} />
            {items.length === 0 ? <div className="inventory-empty"><Inventory2Rounded /><strong>هنوز موجودی ثبت نشده است.</strong><span>با ثبت نخستین خرید، موجودی اینجا نمایش داده می‌شود.</span></div> : null}
            {items.length > 0 && filteredItems.length === 0 ? <div className="inventory-empty"><SearchRounded /><strong>نتیجه‌ای پیدا نشد.</strong><span>عبارت جست‌وجو یا فیلتر کم‌موجود را تغییر دهید.</span></div> : null}
            <div className="inventory-card-grid">
              {filteredItems.map((item) => {
                const isLow = item.reorder_level != null && Number(item.quantity_on_hand) <= Number(item.reorder_level);
                return (
                  <article className={`inventory-stock-card${isLow ? " is-low" : ""}`} key={item.id}>
                    <div className="inventory-stock-title"><div><strong>{item.variant_name}</strong><span>{isLow ? "نیازمند سفارش" : "وضعیت عادی"}</span></div><Chip size="small" color={isLow ? "warning" : "success"} label={isLow ? "کم‌موجود" : "موجود"} /></div>
                    <div className="inventory-stock-metrics">
                      <div><span>موجودی</span><strong>{formatDecimal(item.quantity_on_hand)}</strong></div>
                      <div><span>میانگین بها</span><strong>{formatRial(item.weighted_average_cost_rial)}</strong></div>
                      <div><span>نقطه سفارش</span><strong>{item.reorder_level == null ? "تنظیم نشده" : formatDecimal(item.reorder_level)}</strong></div>
                    </div>
                    <Button fullWidth variant="outlined" startIcon={<EditRounded />} onClick={() => openReorderDialog(item)}>تنظیم نقطه سفارش</Button>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="sale-panel inventory-panel" aria-labelledby="inventory-transactions-heading">
            <div className="inventory-section-heading"><div><h3 id="inventory-transactions-heading">آخرین گردش‌ها</h3><p>ورود و برگشت کالا به ترتیب جدیدترین رخداد.</p></div><HistoryRounded /></div>
            <TextField select fullWidth label="فیلتر بر اساس گونه" value={transactionVariantId} onChange={(event) => setTransactionVariantId(event.target.value)}>
              <MenuItem value="">همه گونه‌ها</MenuItem>
              {items.map((item) => <MenuItem value={String(item.variant_id)} key={item.variant_id}>{item.variant_name}</MenuItem>)}
            </TextField>
            {filteredTransactions.length === 0 ? <div className="inventory-empty"><HistoryRounded /><strong>گردشی برای نمایش وجود ندارد.</strong><span>پس از ثبت یا لغو خرید، رخدادها اینجا می‌آیند.</span></div> : null}
            <div className="inventory-transaction-list">
              {filteredTransactions.map((transaction) => {
                const isIncoming = Number(transaction.quantity_delta) > 0;
                return (
                  <article className="inventory-transaction" key={transaction.id}>
                    <div className={`inventory-transaction-sign ${isIncoming ? "is-in" : "is-out"}`}>{isIncoming ? "+" : "−"}</div>
                    <div className="inventory-transaction-main"><strong>{transaction.variant_name}</strong><span>{transaction.transaction_type === "purchase_in" ? "ورود خرید" : transaction.transaction_type === "cancel_purchase" ? "لغو خرید" : transaction.transaction_type === "sale_out" ? "خروج فروش" : transaction.transaction_type === "cancel_sale" ? "لغو فروش" : transaction.transaction_type}</span><small>{transaction.note ?? (transaction.purchase_invoice_id ? `فاکتور خرید ${transaction.purchase_invoice_id}` : "گردش انبار")}</small></div>
                    <div className="inventory-transaction-numbers"><strong className={isIncoming ? "is-in" : "is-out"}>{isIncoming ? "+" : ""}{formatDecimal(transaction.quantity_delta)}</strong><span>مانده: {formatDecimal(transaction.balance_after)}</span><small>{toPersianDigits(transaction.jalali_date)} · {toPersianDigits(transaction.local_time)}</small></div>
                  </article>
                );
              })}
            </div>
          </section>
        </div>
      ) : null}

      <Dialog open={Boolean(editingItem)} onClose={() => !saving && setEditingItem(null)} fullWidth maxWidth="xs">
        <DialogTitle>تنظیم نقطه سفارش</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ pt: 1 }}><Typography color="text.secondary">{editingItem?.variant_name}</Typography><TextField autoFocus label="نقطه سفارش" value={reorderLevel} onChange={(event) => setReorderLevel(event.target.value)} error={Boolean(reorderError)} helperText={reorderError || "عدد صفر یا بیشتر؛ برای حذف هشدار، خالی بگذارید."} slotProps={{ htmlInput: { inputMode: "decimal" } }} /></Stack></DialogContent>
        <DialogActions><Button onClick={() => setEditingItem(null)} disabled={saving}>انصراف</Button><Button variant="contained" onClick={() => void saveReorderLevel()} disabled={saving}>{saving ? "در حال ذخیره..." : "ذخیره"}</Button></DialogActions>
      </Dialog>
    </section>
  );
}

function ProductsView({ onBack }: { onBack: () => void }) {
  const [catalogTab, setCatalogTab] = useState(0);
  const [units, setUnits] = useState<Unit[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [prices, setPrices] = useState<PriceList[]>([]);
  const [catalogLoadError, setCatalogLoadError] = useState("");
  const [categoryStatus, setCategoryStatus] = useState<"loading" | "ready" | "error">("loading");
  const [categoryNotice, setCategoryNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [categoryName, setCategoryName] = useState("");
  const [categoryParentId, setCategoryParentId] = useState("");
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null);
  const [categorySaving, setCategorySaving] = useState(false);
  const [deactivatingCategoryId, setDeactivatingCategoryId] = useState<number | null>(null);
  const [pendingDeactivateCategory, setPendingDeactivateCategory] = useState<Category | null>(null);
  const [unitProductStatus, setUnitProductStatus] = useState<"loading" | "ready" | "error">("loading");
  const [unitNotice, setUnitNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [productNotice, setProductNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [unitName, setUnitName] = useState("");
  const [unitSymbol, setUnitSymbol] = useState("");
  const [editingUnitId, setEditingUnitId] = useState<number | null>(null);
  const [unitSaving, setUnitSaving] = useState(false);
  const [pendingDeactivateUnit, setPendingDeactivateUnit] = useState<Unit | null>(null);
  const [unitSearch, setUnitSearch] = useState("");
  const [productName, setProductName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [productCategoryId, setProductCategoryId] = useState("");
  const [editingProductId, setEditingProductId] = useState<number | null>(null);
  const [productSaving, setProductSaving] = useState(false);
  const [pendingDeactivateProduct, setPendingDeactivateProduct] = useState<Product | null>(null);
  const [productSearch, setProductSearch] = useState("");
  const [deactivatingRecord, setDeactivatingRecord] = useState(false);
  const [variantStatus, setVariantStatus] = useState<"loading" | "ready" | "error">("loading");
  const [variantNotice, setVariantNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [variantProductId, setVariantProductId] = useState("");
  const [variantUnitId, setVariantUnitId] = useState("");
  const [variantName, setVariantName] = useState("");
  const [variantSku, setVariantSku] = useState("");
  const [variantRetail, setVariantRetail] = useState("");
  const [variantWholesale, setVariantWholesale] = useState("");
  const [variantMinWholesale, setVariantMinWholesale] = useState("");
  const [editingVariantId, setEditingVariantId] = useState<number | null>(null);
  const [variantSaving, setVariantSaving] = useState(false);
  const [variantSearch, setVariantSearch] = useState("");
  const [pendingDeactivateVariant, setPendingDeactivateVariant] = useState<ProductVariant | null>(null);
  const [priceNotice, setPriceNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [priceVariantId, setPriceVariantId] = useState("");
  const [priceType, setPriceType] = useState<PriceType>("retail");
  const [priceAmount, setPriceAmount] = useState("");
  const [priceDate, setPriceDate] = useState(currentJalaliDate);
  const [priceSaving, setPriceSaving] = useState(false);
  const [historyVariantId, setHistoryVariantId] = useState("");
  const [historyPriceType, setHistoryPriceType] = useState<"" | PriceType>("");
  const [priceRules, setPriceRules] = useState<PriceRule[]>([]);
  const [ruleNotice, setRuleNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [ruleVariantId, setRuleVariantId] = useState("");
  const [ruleMinQuantity, setRuleMinQuantity] = useState("");
  const [ruleDiscountType, setRuleDiscountType] = useState<"amount" | "percent">("percent");
  const [ruleDiscountValue, setRuleDiscountValue] = useState("");
  const [ruleStartDate, setRuleStartDate] = useState("");
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [ruleSaving, setRuleSaving] = useState(false);
  const [ruleVariantFilter, setRuleVariantFilter] = useState("");
  const [pendingDeactivateRule, setPendingDeactivateRule] = useState<PriceRule | null>(null);

  const load = () => {
    setCategoryStatus("loading");
    setUnitProductStatus("loading");
    setVariantStatus("loading");
    setCatalogLoadError("");
    setCategoryNotice(null);
    return Promise.all([api.units(), api.categories(), api.products(), api.productVariants(), api.prices(), api.priceRules()])
      .then(([nextUnits, nextCategories, nextProducts, nextVariants, nextPrices, nextPriceRules]) => {
        setUnits(nextUnits);
        setCategories(nextCategories);
        setProducts(nextProducts);
        setVariants(nextVariants);
        setPrices(nextPrices);
        setPriceRules(nextPriceRules);
        setCategoryStatus("ready");
        setUnitProductStatus("ready");
        setVariantStatus("ready");
      })
      .catch((error) => {
        const text = error instanceof Error ? error.message : "دریافت اطلاعات کالا انجام نشد.";
        setCatalogLoadError(text);
        setCategoryStatus("error");
        setUnitProductStatus("error");
        setVariantStatus("error");
      });
  };

  useEffect(() => {
    void load();
  }, []);

  function resetUnitForm() {
    setEditingUnitId(null);
    setUnitName("");
    setUnitSymbol("");
  }

  function startUnitEdit(unit: Unit) {
    setEditingUnitId(unit.id);
    setUnitName(unit.name);
    setUnitSymbol(unit.symbol);
    setUnitNotice(null);
  }

  async function submitUnit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedName = unitName.trim();
    const normalizedSymbol = unitSymbol.trim();
    if (!normalizedName || !normalizedSymbol) {
      setUnitNotice({ type: "error", text: "نام و نماد واحد را کامل وارد کنید." });
      return;
    }
    setUnitSaving(true);
    setUnitNotice(null);
    const wasEditing = editingUnitId !== null;
    try {
      if (editingUnitId === null) await api.createUnit({ name: normalizedName, symbol: normalizedSymbol });
      else await api.updateUnit(editingUnitId, { name: normalizedName, symbol: normalizedSymbol });
      resetUnitForm();
      await load();
      setUnitNotice({ type: "success", text: wasEditing ? "تغییرات واحد ذخیره شد." : "واحد جدید ثبت شد." });
    } catch (error) {
      setUnitNotice({ type: "error", text: error instanceof Error ? error.message : "ذخیره واحد انجام نشد." });
    } finally {
      setUnitSaving(false);
    }
  }

  const orderedCategories = useMemo(() => {
    const children = new Map<number | null, Category[]>();
    categories.forEach((category) => {
      const key = category.parent_id ?? null;
      children.set(key, [...(children.get(key) ?? []), category]);
    });
    children.forEach((items) => items.sort((a, b) => a.name.localeCompare(b.name, "fa")));
    const result: Array<Category & { depth: number }> = [];
    const seen = new Set<number>();
    const visit = (parentId: number | null, depth: number) => {
      (children.get(parentId) ?? []).forEach((category) => {
        if (seen.has(category.id)) return;
        seen.add(category.id);
        result.push({ ...category, depth });
        visit(category.id, depth + 1);
      });
    };
    visit(null, 0);
    categories.forEach((category) => {
      if (!seen.has(category.id)) result.push({ ...category, depth: 0 });
    });
    return result;
  }, [categories]);

  const unavailableParentIds = useMemo(() => {
    if (editingCategoryId === null) return new Set<number>();
    const ids = new Set<number>([editingCategoryId]);
    let changed = true;
    while (changed) {
      changed = false;
      categories.forEach((category) => {
        if (category.parent_id != null && ids.has(category.parent_id) && !ids.has(category.id)) {
          ids.add(category.id);
          changed = true;
        }
      });
    }
    return ids;
  }, [categories, editingCategoryId]);

  function resetCategoryForm() {
    setEditingCategoryId(null);
    setCategoryName("");
    setCategoryParentId("");
  }

  function startCategoryEdit(category: Category) {
    setEditingCategoryId(category.id);
    setCategoryName(category.name);
    setCategoryParentId(category.parent_id == null ? "" : String(category.parent_id));
    setCategoryNotice(null);
  }

  async function submitCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedName = categoryName.trim();
    if (!normalizedName) {
      setCategoryNotice({ type: "error", text: "نام دسته را وارد کنید." });
      return;
    }
    setCategorySaving(true);
    setCategoryNotice(null);
    try {
      const payload = { name: normalizedName, parent_id: categoryParentId ? Number(categoryParentId) : null };
      if (editingCategoryId === null) {
        await api.createCategory(payload);
      } else {
        await api.updateCategory(editingCategoryId, payload);
      }
      resetCategoryForm();
      await load();
      setCategoryNotice({ type: "success", text: editingCategoryId === null ? "دسته جدید ثبت شد." : "تغییرات دسته ذخیره شد." });
    } catch (error) {
      setCategoryNotice({ type: "error", text: error instanceof Error ? error.message : "ذخیره دسته انجام نشد." });
    } finally {
      setCategorySaving(false);
    }
  }

  async function deactivateCategory() {
    const category = pendingDeactivateCategory;
    if (category === null) return;
    setDeactivatingCategoryId(category.id);
    setCategoryNotice(null);
    try {
      await api.deactivateCategory(category.id);
      setPendingDeactivateCategory(null);
      if (editingCategoryId === category.id) resetCategoryForm();
      await load();
      setCategoryNotice({ type: "success", text: "دسته با موفقیت غیرفعال شد." });
    } catch (error) {
      setPendingDeactivateCategory(null);
      setCategoryNotice({ type: "error", text: error instanceof Error ? error.message : "غیرفعال‌سازی دسته انجام نشد." });
    } finally {
      setDeactivatingCategoryId(null);
    }
  }

  const filteredUnits = useMemo(() => {
    const query = unitSearch.trim().toLocaleLowerCase("fa");
    return query ? units.filter((unit) => `${unit.name} ${unit.symbol}`.toLocaleLowerCase("fa").includes(query)) : units;
  }, [unitSearch, units]);

  const filteredProducts = useMemo(() => {
    const query = productSearch.trim().toLocaleLowerCase("fa");
    return query ? products.filter((product) => {
      const categoryName = categories.find((category) => category.id === product.category_id)?.name ?? "بدون دسته";
      return `${product.name} ${product.description ?? ""} ${categoryName}`.toLocaleLowerCase("fa").includes(query);
    }) : products;
  }, [categories, productSearch, products]);

  function resetProductForm() {
    setEditingProductId(null);
    setProductName("");
    setProductDescription("");
    setProductCategoryId("");
  }

  function startProductEdit(product: Product) {
    setEditingProductId(product.id);
    setProductName(product.name);
    setProductDescription(product.description ?? "");
    setProductCategoryId(product.category_id == null ? "" : String(product.category_id));
    setProductNotice(null);
  }

  async function submitProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedName = productName.trim();
    if (!normalizedName) {
      setProductNotice({ type: "error", text: "نام کالا را وارد کنید." });
      return;
    }
    setProductSaving(true);
    setProductNotice(null);
    const wasEditing = editingProductId !== null;
    const payload = {
      name: normalizedName,
      description: productDescription.trim() || null,
      category_id: productCategoryId ? Number(productCategoryId) : null,
    };
    try {
      if (editingProductId === null) await api.createProduct(payload);
      else await api.updateProduct(editingProductId, payload);
      resetProductForm();
      await load();
      setProductNotice({ type: "success", text: wasEditing ? "تغییرات کالا ذخیره شد." : "کالای جدید ثبت شد." });
    } catch (error) {
      setProductNotice({ type: "error", text: error instanceof Error ? error.message : "ذخیره کالا انجام نشد." });
    } finally {
      setProductSaving(false);
    }
  }

  async function deactivateUnit() {
    if (pendingDeactivateUnit === null) return;
    setDeactivatingRecord(true);
    setUnitNotice(null);
    try {
      await api.deactivateUnit(pendingDeactivateUnit.id);
      if (editingUnitId === pendingDeactivateUnit.id) resetUnitForm();
      setPendingDeactivateUnit(null);
      await load();
      setUnitNotice({ type: "success", text: "واحد با موفقیت غیرفعال شد." });
    } catch (error) {
      setPendingDeactivateUnit(null);
      setUnitNotice({ type: "error", text: error instanceof Error ? error.message : "غیرفعال‌سازی واحد انجام نشد." });
    } finally {
      setDeactivatingRecord(false);
    }
  }

  async function deactivateProduct() {
    if (pendingDeactivateProduct === null) return;
    setDeactivatingRecord(true);
    setProductNotice(null);
    try {
      await api.deactivateProduct(pendingDeactivateProduct.id);
      if (editingProductId === pendingDeactivateProduct.id) resetProductForm();
      setPendingDeactivateProduct(null);
      await load();
      setProductNotice({ type: "success", text: "کالا با موفقیت غیرفعال شد." });
    } catch (error) {
      setPendingDeactivateProduct(null);
      setProductNotice({ type: "error", text: error instanceof Error ? error.message : "غیرفعال‌سازی کالا انجام نشد." });
    } finally {
      setDeactivatingRecord(false);
    }
  }

  const filteredVariants = useMemo(() => {
    const query = variantSearch.trim().toLocaleLowerCase("fa");
    if (!query) return variants;
    return variants.filter((variant) => {
      const productName = products.find((product) => product.id === variant.product_id)?.name ?? "";
      const unitName = units.find((unit) => unit.id === variant.unit_id)?.name ?? "";
      return `${variant.name} ${variant.sku ?? ""} ${productName} ${unitName}`.toLocaleLowerCase("fa").includes(query);
    });
  }, [products, units, variantSearch, variants]);

  const filteredPrices = useMemo(() => prices.filter((price) => {
    if (historyVariantId && price.variant_id !== Number(historyVariantId)) return false;
    return !historyPriceType || price.price_type === historyPriceType;
  }), [historyPriceType, historyVariantId, prices]);

  const filteredPriceRules = useMemo(() => priceRules.filter((rule) => (
    !ruleVariantFilter || rule.variant_id === Number(ruleVariantFilter)
  )), [priceRules, ruleVariantFilter]);

  function resetVariantForm() {
    setEditingVariantId(null);
    setVariantProductId("");
    setVariantUnitId("");
    setVariantName("");
    setVariantSku("");
    setVariantRetail("");
    setVariantWholesale("");
    setVariantMinWholesale("");
  }

  function startVariantEdit(variant: ProductVariant) {
    setEditingVariantId(variant.id);
    setVariantProductId(String(variant.product_id));
    setVariantUnitId(String(variant.unit_id));
    setVariantName(variant.name);
    setVariantSku(variant.sku ?? "");
    setVariantRetail(moneyInputValue(variant.retail_price_rial));
    setVariantWholesale(variant.wholesale_price_rial == null ? "" : moneyInputValue(variant.wholesale_price_rial));
    setVariantMinWholesale(variant.min_wholesale_quantity == null ? "" : String(variant.min_wholesale_quantity));
    setVariantNotice(null);
  }

  async function submitVariant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!variantProductId || !variantUnitId || !variantName.trim()) {
      setVariantNotice({ type: "error", text: "کالای پایه، واحد و نام گونه را کامل وارد کنید." });
      return;
    }
    setVariantSaving(true);
    setVariantNotice(null);
    const wasEditing = editingVariantId !== null;
    const payload = {
      product_id: Number(variantProductId),
      unit_id: Number(variantUnitId),
      name: variantName.trim(),
      sku: variantSku.trim() || null,
      retail_price_rial: normalizeMoney(variantRetail),
      wholesale_price_rial: variantWholesale.trim() ? normalizeMoney(variantWholesale) : null,
      min_wholesale_quantity: normalizeDecimal(variantMinWholesale) || null,
    };
    try {
      if (editingVariantId === null) await api.createProductVariant(payload);
      else await api.updateProductVariant(editingVariantId, payload);
      resetVariantForm();
      await load();
      setVariantNotice({ type: "success", text: wasEditing ? "تغییرات گونه ذخیره شد." : "گونه جدید ثبت شد." });
    } catch (error) {
      setVariantNotice({ type: "error", text: error instanceof Error ? error.message : "ذخیره گونه انجام نشد." });
    } finally {
      setVariantSaving(false);
    }
  }

  async function submitPrice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!priceVariantId || !priceAmount.trim() || !priceDate.trim()) {
      setPriceNotice({ type: "error", text: "گونه، مبلغ و تاریخ قیمت را کامل وارد کنید." });
      return;
    }
    setPriceSaving(true);
    setPriceNotice(null);
    try {
      await api.createPrice({
        variant_id: Number(priceVariantId),
        price_type: priceType,
        amount_rial: normalizeMoney(priceAmount),
        jalali_date: priceDate.trim(),
        local_time: currentLocalTime(),
      });
      setPriceAmount("");
      await load();
      setPriceNotice({ type: "success", text: priceType === "online" ? "قیمت آنلاین در تاریخچه ثبت شد." : "قیمت ثبت شد و قیمت جاری گونه به‌روز شد." });
    } catch (error) {
      setPriceNotice({ type: "error", text: error instanceof Error ? error.message : "ثبت قیمت انجام نشد." });
    } finally {
      setPriceSaving(false);
    }
  }

  function resetRuleForm() {
    setEditingRuleId(null);
    setRuleVariantId("");
    setRuleMinQuantity("");
    setRuleDiscountType("percent");
    setRuleDiscountValue("");
    setRuleStartDate("");
  }

  function startRuleEdit(rule: PriceRule) {
    const usesAmount = rule.discount_amount_rial != null && rule.discount_amount_rial > 0;
    setEditingRuleId(rule.id);
    setRuleVariantId(String(rule.variant_id));
    setRuleMinQuantity(String(rule.min_quantity));
    setRuleDiscountType(usesAmount ? "amount" : "percent");
    setRuleDiscountValue(usesAmount ? moneyInputValue(rule.discount_amount_rial ?? 0) : String(rule.discount_percent ?? ""));
    setRuleStartDate(rule.starts_jalali_date ?? "");
    setRuleNotice(null);
  }

  async function submitPriceRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parseRuleDecimal = (value: string) => Number(
      toEnglishDigits(value).replace(/[٫/]/g, ".").replace(/[٬،\s]/g, "").replace(",", "."),
    );
    const minQuantity = parseRuleDecimal(ruleMinQuantity);
    const discountValue = ruleDiscountType === "amount" ? parseLocalizedNumber(ruleDiscountValue) : parseRuleDecimal(ruleDiscountValue);
    if (!ruleVariantId || !Number.isFinite(minQuantity) || minQuantity < 0 || !Number.isFinite(discountValue) || discountValue <= 0) {
      setRuleNotice({ type: "error", text: "گونه، حداقل تعداد و مقدار مثبت تخفیف را درست وارد کنید." });
      return;
    }
    if (ruleDiscountType === "percent" && discountValue > 100) {
      setRuleNotice({ type: "error", text: "درصد تخفیف نمی‌تواند بیشتر از ۱۰۰ باشد." });
      return;
    }
    setRuleSaving(true);
    setRuleNotice(null);
    const wasEditing = editingRuleId !== null;
    const payload = {
      variant_id: Number(ruleVariantId),
      min_quantity: minQuantity,
      discount_amount_rial: ruleDiscountType === "amount" ? normalizeMoney(ruleDiscountValue) : null,
      discount_percent: ruleDiscountType === "percent" ? discountValue : null,
      starts_jalali_date: ruleStartDate.trim() || null,
    };
    try {
      if (editingRuleId === null) await api.createPriceRule(payload);
      else await api.updatePriceRule(editingRuleId, payload);
      resetRuleForm();
      await load();
      setRuleNotice({ type: "success", text: wasEditing ? "قاعده تخفیف به‌روز شد." : "قاعده تخفیف جدید ثبت شد." });
    } catch (error) {
      setRuleNotice({ type: "error", text: error instanceof Error ? error.message : "ذخیره قاعده تخفیف انجام نشد." });
    } finally {
      setRuleSaving(false);
    }
  }

  async function deactivatePriceRule() {
    if (pendingDeactivateRule === null) return;
    setDeactivatingRecord(true);
    setRuleNotice(null);
    try {
      await api.deactivatePriceRule(pendingDeactivateRule.id);
      if (editingRuleId === pendingDeactivateRule.id) resetRuleForm();
      setPendingDeactivateRule(null);
      await load();
      setRuleNotice({ type: "success", text: "قاعده تخفیف غیرفعال شد." });
    } catch (error) {
      setPendingDeactivateRule(null);
      setRuleNotice({ type: "error", text: error instanceof Error ? error.message : "غیرفعال‌سازی قاعده انجام نشد." });
    } finally {
      setDeactivatingRecord(false);
    }
  }

  async function deactivateVariant() {
    if (pendingDeactivateVariant === null) return;
    setDeactivatingRecord(true);
    setVariantNotice(null);
    try {
      await api.deactivateProductVariant(pendingDeactivateVariant.id);
      if (editingVariantId === pendingDeactivateVariant.id) resetVariantForm();
      setPendingDeactivateVariant(null);
      await load();
      setVariantNotice({ type: "success", text: "گونه با موفقیت غیرفعال شد." });
    } catch (error) {
      setPendingDeactivateVariant(null);
      setVariantNotice({ type: "error", text: error instanceof Error ? error.message : "غیرفعال‌سازی گونه انجام نشد." });
    } finally {
      setDeactivatingRecord(false);
    }
  }

  return (
    <CrudWorkspace title="کالاها و قیمت‌ها" eyebrow="مدیریت کاتالوگ" onBack={onBack}>
      <nav className="catalog-tabs" aria-label="بخش‌های مدیریت کالا">
        <Tabs value={catalogTab} onChange={(_, value: number) => setCatalogTab(value)} variant="scrollable" scrollButtons="auto">
          <Tab icon={<CategoryRounded />} iconPosition="start" label="دسته‌ها" />
          <Tab icon={<StraightenRounded />} iconPosition="start" label="واحد و کالا" />
          <Tab icon={<Inventory2Rounded />} iconPosition="start" label="گونه و قیمت" />
        </Tabs>
      </nav>
      {catalogTab === 0 ? (
      <section className="category-manager" aria-labelledby="category-manager-title">
        <div className="category-manager-heading">
          <div>
            <p className="eyebrow">ساختار فروشگاه</p>
            <h3 id="category-manager-title">مدیریت دسته‌بندی‌ها</h3>
            <p>دسته‌های اصلی و زیرمجموعه‌ها را بسازید، ویرایش کنید یا با حفظ سوابق غیرفعال کنید.</p>
          </div>
          <Chip label={`${categories.length.toLocaleString("fa-IR")} دسته فعال`} color="primary" variant="outlined" />
        </div>

        {categoryNotice ? <Alert severity={categoryNotice.type} onClose={() => setCategoryNotice(null)}>{categoryNotice.text}</Alert> : null}

        <div className="category-manager-grid">
          <form className="category-form" onSubmit={submitCategory} noValidate>
            <div className="category-form-title">
              <span className="category-icon"><FolderOutlined /></span>
              <div>
                <strong>{editingCategoryId === null ? "دسته جدید" : "ویرایش دسته"}</strong>
                <small>{editingCategoryId === null ? "نام و جایگاه دسته را مشخص کنید." : "نام یا والد دسته را تغییر دهید."}</small>
              </div>
            </div>
            <TextField
              label="نام دسته"
              value={categoryName}
              onChange={(event) => setCategoryName(event.target.value)}
              slotProps={{ htmlInput: { maxLength: 120 } }}
              required
              fullWidth
              disabled={categorySaving}
              error={categoryName.length > 0 && !categoryName.trim()}
              helperText={categoryName.length > 0 && !categoryName.trim() ? "نام فقط نمی‌تواند فاصله باشد." : "مثلاً برنج ایرانی"}
            />
            <TextField
              select
              label="دسته والد"
              value={categoryParentId}
              onChange={(event) => setCategoryParentId(event.target.value)}
              fullWidth
              disabled={categorySaving || categoryStatus !== "ready"}
              helperText="برای دسته اصلی، گزینه بدون والد را نگه دارید."
            >
              <MenuItem value="">بدون والد (دسته اصلی)</MenuItem>
              {orderedCategories.filter((category) => !unavailableParentIds.has(category.id)).map((category) => (
                <MenuItem key={category.id} value={String(category.id)}>{`${"— ".repeat(category.depth)}${category.name}`}</MenuItem>
              ))}
            </TextField>
            <div className="category-form-actions">
              <Button type="submit" variant="contained" size="large" startIcon={categorySaving ? <CircularProgress size={18} color="inherit" /> : editingCategoryId === null ? <AddRounded /> : <EditRounded />} disabled={categorySaving || !categoryName.trim()}>
                {categorySaving ? "در حال ذخیره…" : editingCategoryId === null ? "ثبت دسته" : "ذخیره تغییرات"}
              </Button>
              {editingCategoryId !== null ? <Button type="button" variant="text" size="large" startIcon={<CloseRounded />} onClick={resetCategoryForm} disabled={categorySaving}>انصراف</Button> : null}
            </div>
          </form>

          <div className="category-list-panel" aria-live="polite">
            <div className="category-list-heading">
              <div><strong>دسته‌های فعال</strong><small>ساختار فعلی فروشگاه</small></div>
              <Button type="button" startIcon={<RefreshRounded />} onClick={() => load()} disabled={categoryStatus === "loading"}>تازه‌سازی</Button>
            </div>
            {categoryStatus === "loading" ? <div className="category-state"><CircularProgress size={28} /><span>در حال دریافت دسته‌ها…</span></div> : null}
            {categoryStatus === "error" ? <div className="category-state category-state-error"><span>{catalogLoadError || "دریافت دسته‌ها انجام نشد."}</span><Button variant="outlined" onClick={() => load()}>تلاش دوباره</Button></div> : null}
            {categoryStatus === "ready" && orderedCategories.length === 0 ? <div className="category-state"><FolderOutlined /><strong>هنوز دسته‌ای ندارید</strong><span>اولین دسته را از فرم روبه‌رو بسازید.</span></div> : null}
            {categoryStatus === "ready" && orderedCategories.length > 0 ? (
              <div className="category-list">
                {orderedCategories.map((category) => (
                  <article className="category-item" key={category.id} style={{ "--category-depth": Math.min(category.depth, 4) } as CSSProperties}>
                    <div className="category-item-name"><FolderOutlined /><div><strong>{category.name}</strong><small>{category.parent_id == null ? "دسته اصلی" : "زیرمجموعه"}</small></div></div>
                    <div className="category-item-actions">
                      <Button type="button" variant="text" startIcon={<EditRounded />} onClick={() => startCategoryEdit(category)} disabled={deactivatingCategoryId !== null}>ویرایش</Button>
                      <Button type="button" color="error" variant="text" startIcon={deactivatingCategoryId === category.id ? <CircularProgress size={17} color="inherit" /> : <DeleteOutlineRounded />} onClick={() => setPendingDeactivateCategory(category)} disabled={deactivatingCategoryId !== null}>غیرفعال</Button>
                    </div>
                  </article>
                ))}
              </div>
            ) : null}
          </div>
        </div>
        <Dialog
          open={pendingDeactivateCategory !== null}
          onClose={() => {
            if (deactivatingCategoryId === null) setPendingDeactivateCategory(null);
          }}
          fullWidth
          maxWidth="xs"
          aria-labelledby="deactivate-category-title"
          aria-describedby="deactivate-category-description"
          slotProps={{ paper: { className: "category-confirm-dialog" } }}
        >
          <DialogTitle id="deactivate-category-title">غیرفعال‌کردن دسته</DialogTitle>
          <DialogContent>
            <p id="deactivate-category-description">
              دسته «{pendingDeactivateCategory?.name}» از فهرست انتخاب‌ها پنهان می‌شود، اما سوابق آن حذف نخواهد شد.
            </p>
            <Alert severity="warning">اگر این دسته فرزند یا کالای فعال داشته باشد، سیستم برای محافظت از اطلاعات اجازه غیرفعال‌سازی نمی‌دهد.</Alert>
          </DialogContent>
          <DialogActions>
            <Button size="large" onClick={() => setPendingDeactivateCategory(null)} disabled={deactivatingCategoryId !== null}>انصراف</Button>
            <Button size="large" color="error" variant="contained" onClick={deactivateCategory} disabled={deactivatingCategoryId !== null} startIcon={deactivatingCategoryId !== null ? <CircularProgress size={18} color="inherit" /> : <DeleteOutlineRounded />}>
              {deactivatingCategoryId !== null ? "در حال غیرفعال‌سازی…" : "غیرفعال شود"}
            </Button>
          </DialogActions>
        </Dialog>
      </section>
      ) : null}
      {catalogTab === 1 ? (
        <section className="unit-product-workspace" aria-label="مدیریت واحدها و کالاهای پایه">
          <section className="record-manager" aria-labelledby="unit-manager-title">
            <header className="record-manager-heading">
              <div><span className="record-manager-icon"><StraightenRounded /></span><div><h3 id="unit-manager-title">واحدهای اندازه‌گیری</h3><p>واحدهایی مثل کیلوگرم، بسته یا عدد را مدیریت کنید.</p></div></div>
              <Chip label={`${units.length.toLocaleString("fa-IR")} واحد فعال`} variant="outlined" color="primary" />
            </header>
            {unitNotice ? <Alert severity={unitNotice.type} onClose={() => setUnitNotice(null)}>{unitNotice.text}</Alert> : null}
            <form className="record-form record-form-unit" onSubmit={submitUnit} noValidate>
              <TextField label="نام واحد" value={unitName} onChange={(event) => setUnitName(event.target.value)} required disabled={unitSaving} helperText="مثلاً کیلوگرم" slotProps={{ htmlInput: { maxLength: 60 } }} />
              <TextField label="نماد" value={unitSymbol} onChange={(event) => setUnitSymbol(event.target.value)} required disabled={unitSaving} helperText="مثلاً kg" slotProps={{ htmlInput: { maxLength: 20, dir: "ltr" } }} />
              <div className="record-form-actions">
                <Button type="submit" variant="contained" size="large" disabled={unitSaving || !unitName.trim() || !unitSymbol.trim()} startIcon={unitSaving ? <CircularProgress size={18} color="inherit" /> : editingUnitId === null ? <AddRounded /> : <EditRounded />}>
                  {unitSaving ? "در حال ذخیره…" : editingUnitId === null ? "ثبت واحد" : "ذخیره تغییرات"}
                </Button>
                {editingUnitId !== null ? <Button type="button" size="large" onClick={resetUnitForm} disabled={unitSaving} startIcon={<CloseRounded />}>انصراف</Button> : null}
              </div>
            </form>
            <TextField className="record-search" size="small" label="جست‌وجوی واحد" value={unitSearch} onChange={(event) => setUnitSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} />
            {unitProductStatus === "loading" ? <div className="record-state"><CircularProgress size={28} /><span>در حال دریافت واحدها…</span></div> : null}
            {unitProductStatus === "error" ? <div className="record-state record-state-error"><span>{catalogLoadError || "دریافت واحدها انجام نشد."}</span><Button variant="outlined" onClick={() => load()}>تلاش دوباره</Button></div> : null}
            {unitProductStatus === "ready" && units.length === 0 ? <div className="record-state"><StraightenRounded /><strong>هنوز واحدی ثبت نشده است</strong></div> : null}
            {unitProductStatus === "ready" && units.length > 0 && filteredUnits.length === 0 ? <div className="record-state"><SearchRounded /><strong>واحدی با این عبارت پیدا نشد</strong></div> : null}
            {unitProductStatus === "ready" && filteredUnits.length > 0 ? <div className="record-list">{filteredUnits.map((unit) => (
              <article className="record-item" key={unit.id}>
                <div><strong>{unit.name}</strong><Chip label={unit.symbol} size="small" /></div>
                <div className="record-item-actions"><Button startIcon={<EditRounded />} onClick={() => startUnitEdit(unit)}>ویرایش</Button><Button color="error" startIcon={<DeleteOutlineRounded />} onClick={() => setPendingDeactivateUnit(unit)}>غیرفعال</Button></div>
              </article>
            ))}</div> : null}
          </section>

          <section className="record-manager" aria-labelledby="product-manager-title">
            <header className="record-manager-heading">
              <div><span className="record-manager-icon record-manager-icon-product"><Inventory2Rounded /></span><div><h3 id="product-manager-title">کالاهای پایه</h3><p>نام، توضیح و دسته هر کالا را مدیریت کنید.</p></div></div>
              <Chip label={`${products.length.toLocaleString("fa-IR")} کالای فعال`} variant="outlined" color="secondary" />
            </header>
            {productNotice ? <Alert severity={productNotice.type} onClose={() => setProductNotice(null)}>{productNotice.text}</Alert> : null}
            <form className="record-form" onSubmit={submitProduct} noValidate>
              <TextField label="نام کالا" value={productName} onChange={(event) => setProductName(event.target.value)} required disabled={productSaving} helperText="مثلاً عدس سبز" slotProps={{ htmlInput: { maxLength: 160 } }} />
              <TextField select label="دسته کالا" value={productCategoryId} onChange={(event) => setProductCategoryId(event.target.value)} disabled={productSaving || unitProductStatus !== "ready"} helperText="انتخاب دسته اختیاری است."><MenuItem value="">بدون دسته</MenuItem>{orderedCategories.map((category) => <MenuItem key={category.id} value={String(category.id)}>{`${"— ".repeat(category.depth)}${category.name}`}</MenuItem>)}</TextField>
              <TextField className="record-form-wide" label="توضیح کوتاه" value={productDescription} onChange={(event) => setProductDescription(event.target.value)} disabled={productSaving} multiline minRows={2} />
              <div className="record-form-actions record-form-wide">
                <Button type="submit" variant="contained" size="large" disabled={productSaving || !productName.trim()} startIcon={productSaving ? <CircularProgress size={18} color="inherit" /> : editingProductId === null ? <AddRounded /> : <EditRounded />}>
                  {productSaving ? "در حال ذخیره…" : editingProductId === null ? "ثبت کالا" : "ذخیره تغییرات"}
                </Button>
                {editingProductId !== null ? <Button type="button" size="large" onClick={resetProductForm} disabled={productSaving} startIcon={<CloseRounded />}>انصراف</Button> : null}
              </div>
            </form>
            <TextField className="record-search" size="small" label="جست‌وجوی کالا یا دسته" value={productSearch} onChange={(event) => setProductSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} />
            {unitProductStatus === "loading" ? <div className="record-state"><CircularProgress size={28} /><span>در حال دریافت کالاها…</span></div> : null}
            {unitProductStatus === "error" ? <div className="record-state record-state-error"><span>{catalogLoadError || "دریافت کالاها انجام نشد."}</span><Button variant="outlined" onClick={() => load()}>تلاش دوباره</Button></div> : null}
            {unitProductStatus === "ready" && products.length === 0 ? <div className="record-state"><Inventory2Rounded /><strong>هنوز کالایی ثبت نشده است</strong></div> : null}
            {unitProductStatus === "ready" && products.length > 0 && filteredProducts.length === 0 ? <div className="record-state"><SearchRounded /><strong>کالایی با این عبارت پیدا نشد</strong></div> : null}
            {unitProductStatus === "ready" && filteredProducts.length > 0 ? <div className="record-list">{filteredProducts.map((product) => {
              const categoryName = categories.find((category) => category.id === product.category_id)?.name ?? "بدون دسته";
              return <article className="record-item record-item-product" key={product.id}><div><strong>{product.name}</strong><small>{categoryName}{product.description ? ` • ${product.description}` : ""}</small></div><div className="record-item-actions"><Button startIcon={<EditRounded />} onClick={() => startProductEdit(product)}>ویرایش</Button><Button color="error" startIcon={<DeleteOutlineRounded />} onClick={() => setPendingDeactivateProduct(product)}>غیرفعال</Button></div></article>;
            })}</div> : null}
          </section>

          <Dialog open={pendingDeactivateUnit !== null} onClose={() => { if (!deactivatingRecord) setPendingDeactivateUnit(null); }} fullWidth maxWidth="xs" slotProps={{ paper: { className: "category-confirm-dialog" } }}>
            <DialogTitle>غیرفعال‌کردن واحد</DialogTitle><DialogContent><p>واحد «{pendingDeactivateUnit?.name}» از انتخاب‌های جدید پنهان می‌شود و سوابق آن باقی می‌ماند.</p><Alert severity="warning">اگر گونه فعال از این واحد استفاده کند، عملیات انجام نمی‌شود.</Alert></DialogContent><DialogActions><Button size="large" onClick={() => setPendingDeactivateUnit(null)} disabled={deactivatingRecord}>انصراف</Button><Button size="large" color="error" variant="contained" onClick={deactivateUnit} disabled={deactivatingRecord} startIcon={deactivatingRecord ? <CircularProgress size={18} color="inherit" /> : <DeleteOutlineRounded />}>غیرفعال شود</Button></DialogActions>
          </Dialog>
          <Dialog open={pendingDeactivateProduct !== null} onClose={() => { if (!deactivatingRecord) setPendingDeactivateProduct(null); }} fullWidth maxWidth="xs" slotProps={{ paper: { className: "category-confirm-dialog" } }}>
            <DialogTitle>غیرفعال‌کردن کالا</DialogTitle><DialogContent><p>کالای «{pendingDeactivateProduct?.name}» از انتخاب‌های جدید پنهان می‌شود و سوابق آن باقی می‌ماند.</p><Alert severity="warning">اگر این کالا گونه فعال داشته باشد، عملیات انجام نمی‌شود.</Alert></DialogContent><DialogActions><Button size="large" onClick={() => setPendingDeactivateProduct(null)} disabled={deactivatingRecord}>انصراف</Button><Button size="large" color="error" variant="contained" onClick={deactivateProduct} disabled={deactivatingRecord} startIcon={deactivatingRecord ? <CircularProgress size={18} color="inherit" /> : <DeleteOutlineRounded />}>غیرفعال شود</Button></DialogActions>
          </Dialog>
        </section>
      ) : null}
      {catalogTab === 2 ? (
        <section className="variant-price-workspace" aria-label="مدیریت گونه‌ها و تاریخچه قیمت">
          <section className="variant-manager" aria-labelledby="variant-manager-title">
            <header className="record-manager-heading">
              <div><span className="record-manager-icon"><Inventory2Rounded /></span><div><h3 id="variant-manager-title">گونه‌های کالا</h3><p>بسته‌بندی، واحد فروش، کد و قیمت جاری هر گونه را مدیریت کنید.</p></div></div>
              <Chip label={`${variants.length.toLocaleString("fa-IR")} گونه فعال`} color="primary" variant="outlined" />
            </header>
            {variantNotice ? <Alert severity={variantNotice.type} onClose={() => setVariantNotice(null)}>{variantNotice.text}</Alert> : null}
            <div className="variant-manager-grid">
              <form className="variant-form" onSubmit={submitVariant} noValidate>
                <TextField select label="کالای پایه" value={variantProductId} onChange={(event) => setVariantProductId(event.target.value)} required disabled={variantSaving || variantStatus !== "ready"}><MenuItem value="">انتخاب کالا</MenuItem>{products.map((product) => <MenuItem value={String(product.id)} key={product.id}>{product.name}</MenuItem>)}</TextField>
                <TextField select label="واحد" value={variantUnitId} onChange={(event) => setVariantUnitId(event.target.value)} required disabled={variantSaving || variantStatus !== "ready"}><MenuItem value="">انتخاب واحد</MenuItem>{units.map((unit) => <MenuItem value={String(unit.id)} key={unit.id}>{unit.name} ({unit.symbol})</MenuItem>)}</TextField>
                <TextField label="نام گونه" value={variantName} onChange={(event) => setVariantName(event.target.value)} required disabled={variantSaving} helperText="مثلاً عدس درجه یک کیلویی" slotProps={{ htmlInput: { maxLength: 180 } }} />
                <TextField label="کد کالا (SKU)" value={variantSku} onChange={(event) => setVariantSku(event.target.value)} disabled={variantSaving} helperText="اختیاری و یکتا" slotProps={{ htmlInput: { maxLength: 80, dir: "ltr" } }} />
                <TextField label="قیمت خرده (تومان)" value={variantRetail} onChange={(event) => setVariantRetail(event.target.value)} inputMode="numeric" disabled={variantSaving} required />
                <TextField label="قیمت عمده (تومان)" value={variantWholesale} onChange={(event) => setVariantWholesale(event.target.value)} inputMode="numeric" disabled={variantSaving} />
                <TextField label="حداقل تعداد عمده" value={variantMinWholesale} onChange={(event) => setVariantMinWholesale(event.target.value)} inputMode="decimal" disabled={variantSaving} />
                <div className="record-form-actions variant-form-actions"><Button type="submit" variant="contained" size="large" disabled={variantSaving || !variantProductId || !variantUnitId || !variantName.trim()} startIcon={variantSaving ? <CircularProgress size={18} color="inherit" /> : editingVariantId === null ? <AddRounded /> : <EditRounded />}>{variantSaving ? "در حال ذخیره…" : editingVariantId === null ? "ثبت گونه" : "ذخیره تغییرات"}</Button>{editingVariantId !== null ? <Button type="button" size="large" onClick={resetVariantForm} disabled={variantSaving} startIcon={<CloseRounded />}>انصراف</Button> : null}</div>
              </form>

              <div className="variant-list-panel">
                <div className="variant-list-toolbar"><TextField className="record-search" size="small" label="جست‌وجوی گونه، SKU یا کالا" value={variantSearch} onChange={(event) => setVariantSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} /><Button startIcon={<RefreshRounded />} onClick={() => load()} disabled={variantStatus === "loading"}>تازه‌سازی</Button></div>
                {variantStatus === "loading" ? <div className="record-state"><CircularProgress size={28} /><span>در حال دریافت گونه‌ها…</span></div> : null}
                {variantStatus === "error" ? <div className="record-state record-state-error"><span>{catalogLoadError || "دریافت گونه‌ها انجام نشد."}</span><Button variant="outlined" onClick={() => load()}>تلاش دوباره</Button></div> : null}
                {variantStatus === "ready" && variants.length === 0 ? <div className="record-state"><Inventory2Rounded /><strong>هنوز گونه‌ای ثبت نشده است</strong><span>ابتدا کالا و واحد پایه را در تب قبلی بسازید.</span></div> : null}
                {variantStatus === "ready" && variants.length > 0 && filteredVariants.length === 0 ? <div className="record-state"><SearchRounded /><strong>گونه‌ای با این عبارت پیدا نشد</strong></div> : null}
                {variantStatus === "ready" && filteredVariants.length > 0 ? <div className="variant-card-list">{filteredVariants.map((variant) => {
                  const product = products.find((item) => item.id === variant.product_id);
                  const unit = units.find((item) => item.id === variant.unit_id);
                  return <article className="variant-card" key={variant.id}><div className="variant-card-main"><div><strong>{variant.name}</strong><small>{product?.name ?? "کالای نامشخص"} • {unit?.name ?? "واحد نامشخص"}{variant.sku ? ` • ${variant.sku}` : ""}</small></div><div className="variant-prices"><span><small>خرده</small><strong>{formatRial(variant.retail_price_rial)}</strong></span><span><small>عمده</small><strong>{variant.wholesale_price_rial == null ? "ثبت نشده" : formatRial(variant.wholesale_price_rial)}</strong></span></div></div><div className="record-item-actions"><Button startIcon={<EditRounded />} onClick={() => startVariantEdit(variant)}>ویرایش</Button><Button color="error" startIcon={<DeleteOutlineRounded />} onClick={() => setPendingDeactivateVariant(variant)}>غیرفعال</Button></div></article>;
                })}</div> : null}
              </div>
            </div>
          </section>

          <section className="price-manager" aria-labelledby="price-manager-title">
            <header className="record-manager-heading"><div><span className="record-manager-icon record-manager-icon-price"><LocalOfferRounded /></span><div><h3 id="price-manager-title">ثبت و تاریخچه قیمت</h3><p>هر تغییر قیمت ثبت می‌شود؛ قیمت خرده و عمده هم‌زمان روی گونه به‌روز می‌شوند.</p></div></div></header>
            <div className="price-manager-grid">
              <form className="price-form" onSubmit={submitPrice} noValidate>
                <h4>قیمت جدید</h4>
                {priceNotice ? <Alert severity={priceNotice.type} onClose={() => setPriceNotice(null)}>{priceNotice.text}</Alert> : null}
                <TextField select label="گونه" value={priceVariantId} onChange={(event) => setPriceVariantId(event.target.value)} required disabled={priceSaving || variantStatus !== "ready"}><MenuItem value="">انتخاب گونه</MenuItem>{variants.map((variant) => <MenuItem key={variant.id} value={String(variant.id)}>{variant.name}</MenuItem>)}</TextField>
                <TextField select label="نوع قیمت" value={priceType} onChange={(event) => setPriceType(event.target.value as PriceType)} disabled={priceSaving}>{Object.entries(PRICE_TYPE_LABELS).map(([value, label]) => <MenuItem value={value} key={value}>{label}</MenuItem>)}</TextField>
                <TextField label="مبلغ (تومان)" value={priceAmount} onChange={(event) => setPriceAmount(event.target.value)} inputMode="numeric" required disabled={priceSaving} />
                <TextField label="تاریخ شمسی" value={priceDate} onChange={(event) => setPriceDate(event.target.value)} required disabled={priceSaving} helperText="مثلاً 1405/06/02" slotProps={{ htmlInput: { dir: "ltr" } }} />
                <Button type="submit" variant="contained" size="large" disabled={priceSaving || !priceVariantId || !priceAmount.trim() || !priceDate.trim()} startIcon={priceSaving ? <CircularProgress size={18} color="inherit" /> : <LocalOfferRounded />}>{priceSaving ? "در حال ثبت…" : "ثبت قیمت"}</Button>
              </form>
              <div className="price-history">
                <div className="price-history-heading"><div><HistoryRounded /><div><strong>تاریخچه قیمت</strong><small>{filteredPrices.length.toLocaleString("fa-IR")} تغییر ثبت‌شده</small></div></div></div>
                <div className="price-history-filters"><TextField select size="small" label="گونه" value={historyVariantId} onChange={(event) => setHistoryVariantId(event.target.value)}><MenuItem value="">همه گونه‌ها</MenuItem>{variants.map((variant) => <MenuItem value={String(variant.id)} key={variant.id}>{variant.name}</MenuItem>)}</TextField><TextField select size="small" label="نوع قیمت" value={historyPriceType} onChange={(event) => setHistoryPriceType(event.target.value as "" | PriceType)}><MenuItem value="">همه نوع‌ها</MenuItem>{Object.entries(PRICE_TYPE_LABELS).map(([value, label]) => <MenuItem value={value} key={value}>{label}</MenuItem>)}</TextField></div>
                {variantStatus === "loading" ? <div className="record-state"><CircularProgress size={26} /><span>در حال دریافت تاریخچه…</span></div> : null}
                {variantStatus === "ready" && filteredPrices.length === 0 ? <div className="record-state"><HistoryRounded /><strong>هنوز تغییری ثبت نشده است</strong></div> : null}
                {variantStatus === "ready" && filteredPrices.length > 0 ? <div className="price-history-list">{filteredPrices.map((price) => { const variant = variants.find((item) => item.id === price.variant_id); return <article className="price-history-item" key={price.id}><div><strong>{variant?.name ?? `گونه ${price.variant_id.toLocaleString("fa-IR")}`}</strong><small>{PRICE_TYPE_LABELS[price.price_type]} • {price.jalali_date} ساعت {price.local_time}</small></div><strong>{formatRial(price.amount_rial)}</strong></article>; })}</div> : null}
              </div>
            </div>
          </section>

          <section className="discount-rule-manager" aria-labelledby="discount-rule-manager-title">
            <header className="record-manager-heading">
              <div><span className="record-manager-icon record-manager-icon-discount"><LocalOfferRounded /></span><div><h3 id="discount-rule-manager-title">قواعد تخفیف تعدادی</h3><p>برای خرید از یک تعداد مشخص، فقط یک تخفیف مبلغی یا درصدی تعریف کنید.</p></div></div>
              <Chip label={`${priceRules.length.toLocaleString("fa-IR")} قاعده فعال`} color="secondary" variant="outlined" />
            </header>
            {ruleNotice ? <Alert severity={ruleNotice.type} onClose={() => setRuleNotice(null)}>{ruleNotice.text}</Alert> : null}
            <div className="discount-rule-grid">
              <form className="discount-rule-form" onSubmit={submitPriceRule} noValidate>
                <div className="discount-rule-form-heading"><strong>{editingRuleId === null ? "قاعده جدید" : "ویرایش قاعده"}</strong><small>محدوده اجرا و نوع تخفیف را مشخص کنید.</small></div>
                <TextField select label="گونه کالا" value={ruleVariantId} onChange={(event) => setRuleVariantId(event.target.value)} required disabled={ruleSaving || variantStatus !== "ready"}><MenuItem value="">انتخاب گونه</MenuItem>{variants.map((variant) => <MenuItem value={String(variant.id)} key={variant.id}>{variant.name}</MenuItem>)}</TextField>
                <TextField label="حداقل تعداد" value={ruleMinQuantity} onChange={(event) => setRuleMinQuantity(event.target.value)} inputMode="decimal" required disabled={ruleSaving} helperText="از صفر به بالا؛ مثلاً ۵" />
                <TextField select label="نوع تخفیف" value={ruleDiscountType} onChange={(event) => { setRuleDiscountType(event.target.value as "amount" | "percent"); setRuleDiscountValue(""); }} disabled={ruleSaving}><MenuItem value="percent">درصدی</MenuItem><MenuItem value="amount">مبلغ ثابت</MenuItem></TextField>
                <TextField label={ruleDiscountType === "amount" ? "مبلغ تخفیف (تومان)" : "درصد تخفیف"} value={ruleDiscountValue} onChange={(event) => setRuleDiscountValue(event.target.value)} inputMode={ruleDiscountType === "amount" ? "numeric" : "decimal"} required disabled={ruleSaving} helperText={ruleDiscountType === "amount" ? "مبلغ مثبت را به تومان وارد کنید." : "مقداری بیشتر از صفر و حداکثر ۱۰۰"} />
                <TextField label="تاریخ شروع (اختیاری)" value={ruleStartDate} onChange={(event) => setRuleStartDate(event.target.value)} disabled={ruleSaving} helperText="مثلاً 1405/06/02؛ خالی یعنی بدون محدودیت" slotProps={{ htmlInput: { dir: "ltr" } }} />
                <div className="record-form-actions discount-rule-form-actions"><Button type="submit" variant="contained" size="large" disabled={ruleSaving || !ruleVariantId || !ruleMinQuantity.trim() || !ruleDiscountValue.trim()} startIcon={ruleSaving ? <CircularProgress size={18} color="inherit" /> : editingRuleId === null ? <AddRounded /> : <EditRounded />}>{ruleSaving ? "در حال ذخیره…" : editingRuleId === null ? "ثبت قاعده" : "ذخیره تغییرات"}</Button>{editingRuleId !== null ? <Button type="button" size="large" onClick={resetRuleForm} disabled={ruleSaving} startIcon={<CloseRounded />}>انصراف</Button> : null}</div>
              </form>

              <div className="discount-rule-list-panel">
                <div className="discount-rule-toolbar"><div><strong>قواعد فعال</strong><small>قاعده مناسب هر گونه را سریع پیدا و اصلاح کنید.</small></div><TextField select size="small" label="فیلتر گونه" value={ruleVariantFilter} onChange={(event) => setRuleVariantFilter(event.target.value)}><MenuItem value="">همه گونه‌ها</MenuItem>{variants.map((variant) => <MenuItem value={String(variant.id)} key={variant.id}>{variant.name}</MenuItem>)}</TextField></div>
                {variantStatus === "loading" ? <div className="record-state"><CircularProgress size={26} /><span>در حال دریافت قواعد…</span></div> : null}
                {variantStatus === "error" ? <div className="record-state record-state-error"><span>{catalogLoadError || "دریافت قواعد تخفیف انجام نشد."}</span><Button variant="outlined" onClick={() => load()}>تلاش دوباره</Button></div> : null}
                {variantStatus === "ready" && priceRules.length === 0 ? <div className="record-state"><LocalOfferRounded /><strong>هنوز قاعده‌ای ثبت نشده است</strong><span>فرم روبه‌رو را برای اولین تخفیف تکمیل کنید.</span></div> : null}
                {variantStatus === "ready" && priceRules.length > 0 && filteredPriceRules.length === 0 ? <div className="record-state"><SearchRounded /><strong>برای این گونه قاعده‌ای پیدا نشد</strong></div> : null}
                {variantStatus === "ready" && filteredPriceRules.length > 0 ? <div className="discount-rule-list">{filteredPriceRules.map((rule) => {
                  const variant = variants.find((item) => item.id === rule.variant_id);
                  const amountDiscount = rule.discount_amount_rial != null && rule.discount_amount_rial > 0;
                  return <article className="discount-rule-card" key={rule.id}><div className="discount-rule-card-main"><div><strong>{variant?.name ?? `گونه ${rule.variant_id.toLocaleString("fa-IR")}`}</strong><small>شروع: {rule.starts_jalali_date || "بدون محدودیت تاریخ"}</small></div><div className="discount-rule-summary"><span><small>از تعداد</small><strong>{formatDecimal(rule.min_quantity)}</strong></span><span className="discount-rule-value"><small>تخفیف</small><strong>{amountDiscount ? formatRial(rule.discount_amount_rial ?? 0) : `${formatDecimal(rule.discount_percent ?? 0)}٪`}</strong></span></div></div><div className="record-item-actions"><Button startIcon={<EditRounded />} onClick={() => startRuleEdit(rule)}>ویرایش</Button><Button color="error" startIcon={<DeleteOutlineRounded />} onClick={() => setPendingDeactivateRule(rule)}>غیرفعال</Button></div></article>;
                })}</div> : null}
              </div>
            </div>
          </section>

          <Dialog open={pendingDeactivateVariant !== null} onClose={() => { if (!deactivatingRecord) setPendingDeactivateVariant(null); }} fullWidth maxWidth="xs" slotProps={{ paper: { className: "category-confirm-dialog" } }}><DialogTitle>غیرفعال‌کردن گونه</DialogTitle><DialogContent><p>گونه «{pendingDeactivateVariant?.name}» از انتخاب‌های جدید پنهان می‌شود و سوابق خرید، فروش و قیمت آن باقی می‌ماند.</p><Alert severity="warning">اگر موجودی این گونه غیرصفر باشد، عملیات انجام نمی‌شود.</Alert></DialogContent><DialogActions><Button size="large" onClick={() => setPendingDeactivateVariant(null)} disabled={deactivatingRecord}>انصراف</Button><Button size="large" color="error" variant="contained" onClick={deactivateVariant} disabled={deactivatingRecord} startIcon={deactivatingRecord ? <CircularProgress size={18} color="inherit" /> : <DeleteOutlineRounded />}>غیرفعال شود</Button></DialogActions></Dialog>
          <Dialog open={pendingDeactivateRule !== null} onClose={() => { if (!deactivatingRecord) setPendingDeactivateRule(null); }} fullWidth maxWidth="xs" slotProps={{ paper: { className: "category-confirm-dialog" } }}><DialogTitle>غیرفعال‌کردن قاعده تخفیف</DialogTitle><DialogContent><p>این قاعده برای «{variants.find((variant) => variant.id === pendingDeactivateRule?.variant_id)?.name ?? "گونه انتخاب‌شده"}» دیگر در محاسبات جدید استفاده نمی‌شود.</p><Alert severity="info">سابقه قاعده در سیستم باقی می‌ماند.</Alert></DialogContent><DialogActions><Button size="large" onClick={() => setPendingDeactivateRule(null)} disabled={deactivatingRecord}>انصراف</Button><Button size="large" color="error" variant="contained" onClick={deactivatePriceRule} disabled={deactivatingRecord} startIcon={deactivatingRecord ? <CircularProgress size={18} color="inherit" /> : <DeleteOutlineRounded />}>غیرفعال شود</Button></DialogActions></Dialog>
        </section>
      ) : null}
    </CrudWorkspace>
  );
}

function LedgerView({ onBack }: { onBack: () => void }) {
  const [people, setPeople] = useState<Person[]>([]);
  const [selectedId, setSelectedId] = useState(0);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [peopleStatus, setPeopleStatus] = useState<"loading" | "ready" | "error">("loading");
  const [ledgerStatus, setLedgerStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [personDialog, setPersonDialog] = useState(false);
  const [personDialogError, setPersonDialogError] = useState("");
  const [personName, setPersonName] = useState("");
  const [personPhone, setPersonPhone] = useState("");
  const [personType, setPersonType] = useState<Person["person_type"]>("customer");
  const [personSaving, setPersonSaving] = useState(false);
  const [entryType, setEntryType] = useState<"debit" | "credit">("debit");
  const [entryAmount, setEntryAmount] = useState("");
  const [entryDate, setEntryDate] = useState(currentJalaliDate);
  const [entryDescription, setEntryDescription] = useState("");
  const [entrySaving, setEntrySaving] = useState(false);
  const [settlementType, setSettlementType] = useState<"debit" | "credit">("debit");
  const [settlementAmount, setSettlementAmount] = useState("");
  const [settlementDate, setSettlementDate] = useState(currentJalaliDate);
  const [settlementNote, setSettlementNote] = useState("");
  const [settlementSaving, setSettlementSaving] = useState(false);
  const selected = people.find((person) => person.id === selectedId);
  const debitOpen = entries.filter((entry) => entry.status === "open" && entry.entry_type === "debit").reduce((sum, entry) => sum + entry.remaining_rial, 0);
  const creditOpen = entries.filter((entry) => entry.status === "open" && entry.entry_type === "credit").reduce((sum, entry) => sum + entry.remaining_rial, 0);
  const balance = debitOpen - creditOpen;
  const selectedSideBalance = settlementType === "debit" ? debitOpen : creditOpen;
  const filteredPeople = people.filter((person) => `${person.name} ${person.phone ?? ""}`.toLowerCase().includes(search.trim().toLowerCase()));
  const sortedEntries = [...entries].sort((a, b) => `${b.jalali_date}${b.local_time}${b.id}`.localeCompare(`${a.jalali_date}${a.local_time}${a.id}`));

  async function loadPeople() {
    setPeopleStatus("loading");
    try { setPeople(await api.persons()); setPeopleStatus("ready"); }
    catch (error) { setPeopleStatus("error"); setNotice({ type: "error", text: error instanceof Error ? error.message : "اشخاص دریافت نشدند." }); }
  }
  async function loadLedger(personId: number) {
    setLedgerStatus("loading");
    try { setEntries(await api.personLedger(personId)); setLedgerStatus("ready"); }
    catch (error) { setLedgerStatus("error"); setNotice({ type: "error", text: error instanceof Error ? error.message : "دفتر حساب دریافت نشد." }); }
  }
  useEffect(() => { loadPeople(); }, []);
  useEffect(() => { if (selectedId) loadLedger(selectedId); else { setEntries([]); setLedgerStatus("idle"); } }, [selectedId]);

  async function submitPerson(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!personName.trim()) { setPersonDialogError("نام شخص را وارد کنید."); return; }
    setPersonSaving(true); setNotice(null); setPersonDialogError("");
    try {
      const created = await api.createPerson({ name: personName.trim(), phone: personPhone.trim() || undefined, person_type: personType });
      setPersonName(""); setPersonPhone(""); setPersonDialog(false); setNotice({ type: "success", text: "شخص جدید ثبت شد." });
      await loadPeople(); setSelectedId(created.id);
    } catch (error) { setPersonDialogError(error instanceof Error ? error.message : "ثبت شخص انجام نشد."); }
    finally { setPersonSaving(false); }
  }

  async function submitEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = normalizeMoney(entryAmount);
    if (!selectedId || amount <= 0) { setNotice({ type: "error", text: "شخص و مبلغ مثبت را مشخص کنید." }); return; }
    setEntrySaving(true); setNotice(null);
    try {
      await api.createManualEntry({ person_id: selectedId, entry_type: entryType, amount_rial: amount, jalali_date: entryDate, local_time: currentLocalTime(), description: entryDescription.trim() || undefined });
      setEntryAmount(""); setEntryDescription(""); setNotice({ type: "success", text: "سند دستی ثبت شد." }); await loadLedger(selectedId);
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "ثبت سند انجام نشد." }); }
    finally { setEntrySaving(false); }
  }

  async function submitSettlement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = normalizeMoney(settlementAmount);
    if (!selectedId || amount <= 0) { setNotice({ type: "error", text: "مبلغ تسویه باید بیشتر از صفر باشد." }); return; }
    if (amount > selectedSideBalance) { setNotice({ type: "error", text: `مبلغ تسویه از مانده ${settlementType === "debit" ? "بدهکار" : "بستانکار"} بیشتر است.` }); return; }
    setSettlementSaving(true); setNotice(null);
    try {
      await api.createSettlement({ person_id: selectedId, entry_type: settlementType, amount_rial: amount, jalali_date: settlementDate, local_time: currentLocalTime(), note: settlementNote.trim() || undefined });
      setSettlementAmount(""); setSettlementNote(""); setNotice({ type: "success", text: "تسویه با موفقیت ثبت شد." }); await loadLedger(selectedId);
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "ثبت تسویه انجام نشد." }); }
    finally { setSettlementSaving(false); }
  }

  return (
    <CrudWorkspace title="دفتر حساب اشخاص" eyebrow="مشتری و تامین‌کننده" onBack={onBack}>
      {notice ? <Alert severity={notice.type} onClose={() => setNotice(null)}>{notice.text}</Alert> : null}
      <div className="ledger-shell">
        <aside className="ledger-people-panel sale-panel">
          <div className="ledger-section-heading"><div><strong>اشخاص</strong><small>حساب موردنظر را انتخاب کنید</small></div><Button variant="contained" startIcon={<AddRounded />} onClick={() => { setPersonDialogError(""); setPersonDialog(true); }}>شخص جدید</Button></div>
          <TextField size="small" label="جست‌وجوی نام یا تلفن" value={search} onChange={(event) => setSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} />
          {peopleStatus === "loading" ? <div className="record-state"><CircularProgress size={26} /><span>در حال دریافت اشخاص…</span></div> : null}
          {peopleStatus === "error" ? <div className="record-state record-state-error"><span>فهرست اشخاص دریافت نشد.</span><Button variant="outlined" startIcon={<RefreshRounded />} onClick={loadPeople}>تلاش دوباره</Button></div> : null}
          {peopleStatus === "ready" && people.length === 0 ? <div className="record-state"><AccountBalanceWalletRounded /><strong>هنوز شخصی ثبت نشده است</strong><span>برای شروع، یک مشتری یا تأمین‌کننده بسازید.</span></div> : null}
          {peopleStatus === "ready" && people.length > 0 && filteredPeople.length === 0 ? <div className="record-state"><SearchRounded /><strong>شخصی با این جست‌وجو پیدا نشد</strong></div> : null}
          <div className="ledger-person-list">{filteredPeople.map((person) => <button type="button" className={`ledger-person-item ${selectedId === person.id ? "active" : ""}`} key={person.id} onClick={() => setSelectedId(person.id)}><span><strong>{person.name}</strong><small>{person.phone || "بدون شماره تماس"}</small></span><Chip size="small" label={person.person_type === "customer" ? "مشتری" : person.person_type === "supplier" ? "تأمین‌کننده" : "هر دو"} /></button>)}</div>
        </aside>
        <main className="ledger-main">
          {!selected ? <div className="record-state ledger-welcome sale-panel"><AccountBalanceWalletRounded /><strong>یک حساب را انتخاب کنید</strong><span>مانده و گردش حساب شخص در این بخش نمایش داده می‌شود.</span></div> : <>
            <section className={`ledger-balance-card ${balance > 0 ? "debtor" : balance < 0 ? "creditor" : "settled"}`}>
              <div><small>مانده خالص {selected.name}</small><strong>{formatRial(Math.abs(balance))}</strong><span>{balance > 0 ? "این شخص به فروشگاه بدهکار است" : balance < 0 ? "فروشگاه به این شخص بدهکار است" : "حساب تسویه است"}</span></div>
              <div className="ledger-side-balances"><span><small>مانده بدهکار</small><strong>{formatRial(debitOpen)}</strong></span><span><small>مانده بستانکار</small><strong>{formatRial(creditOpen)}</strong></span></div>
            </section>
            <div className="ledger-actions-grid">
              <form className="sale-panel ledger-form" onSubmit={submitEntry} noValidate><div className="ledger-section-heading"><div><strong>سند دستی</strong><small>افزایش مانده بدهکار یا بستانکار</small></div></div><TextField select label="نوع سند" value={entryType} onChange={(event) => setEntryType(event.target.value as "debit" | "credit")} disabled={entrySaving}><MenuItem value="debit">بدهکار — شخص باید پرداخت کند</MenuItem><MenuItem value="credit">بستانکار — فروشگاه باید پرداخت کند</MenuItem></TextField><TextField label="مبلغ (تومان)" value={entryAmount} onChange={(event) => setEntryAmount(event.target.value)} inputMode="numeric" required disabled={entrySaving} /><JalaliDateField label="تاریخ سند" value={entryDate} onChange={setEntryDate} required /><TextField label="شرح (اختیاری)" value={entryDescription} onChange={(event) => setEntryDescription(event.target.value)} disabled={entrySaving} /><Button type="submit" size="large" variant="contained" disabled={entrySaving || normalizeMoney(entryAmount) <= 0} startIcon={entrySaving ? <CircularProgress size={18} color="inherit" /> : <AddRounded />}>{entrySaving ? "در حال ثبت…" : "ثبت سند"}</Button></form>
              <form className="sale-panel ledger-form" onSubmit={submitSettlement} noValidate><div className="ledger-section-heading"><div><strong>ثبت تسویه</strong><small>فقط اسناد باز همان سمت، از قدیمی‌ترین تسویه می‌شوند</small></div></div><TextField select label="سمت حساب برای تسویه" value={settlementType} onChange={(event) => setSettlementType(event.target.value as "debit" | "credit")} disabled={settlementSaving}><MenuItem value="debit">مانده بدهکار ({formatRial(debitOpen)})</MenuItem><MenuItem value="credit">مانده بستانکار ({formatRial(creditOpen)})</MenuItem></TextField><TextField label="مبلغ تسویه (تومان)" value={settlementAmount} onChange={(event) => setSettlementAmount(event.target.value)} inputMode="numeric" required disabled={settlementSaving} error={normalizeMoney(settlementAmount) > selectedSideBalance} helperText={`حداکثر قابل تسویه: ${formatRial(selectedSideBalance)}`} /><JalaliDateField label="تاریخ تسویه" value={settlementDate} onChange={setSettlementDate} required /><TextField label="یادداشت (اختیاری)" value={settlementNote} onChange={(event) => setSettlementNote(event.target.value)} disabled={settlementSaving} /><Button type="submit" size="large" variant="contained" disabled={settlementSaving || normalizeMoney(settlementAmount) <= 0 || normalizeMoney(settlementAmount) > selectedSideBalance} startIcon={settlementSaving ? <CircularProgress size={18} color="inherit" /> : <PaymentsRounded />}>{settlementSaving ? "در حال ثبت…" : "ثبت تسویه"}</Button></form>
            </div>
            <section className="sale-panel ledger-timeline-panel"><div className="ledger-section-heading"><div><strong>گردش حساب</strong><small>جدیدترین تراکنش‌ها در ابتدای فهرست</small></div><Chip label={`${entries.length.toLocaleString("fa-IR")} سند`} variant="outlined" /></div>{ledgerStatus === "loading" ? <div className="record-state"><CircularProgress size={26} /><span>در حال دریافت گردش حساب…</span></div> : null}{ledgerStatus === "error" ? <div className="record-state record-state-error"><span>گردش حساب دریافت نشد.</span><Button variant="outlined" onClick={() => loadLedger(selectedId)}>تلاش دوباره</Button></div> : null}{ledgerStatus === "ready" && entries.length === 0 ? <div className="record-state"><HistoryRounded /><strong>هنوز سندی ثبت نشده است</strong></div> : null}<div className="ledger-timeline">{sortedEntries.map((entry) => <article className="ledger-entry-card" key={entry.id}><span className={`ledger-entry-mark ${entry.entry_type}`} /><div><div className="ledger-entry-title"><strong>{entry.entry_type === "debit" ? "بدهکار" : "بستانکار"}</strong><Chip size="small" color={entry.status === "settled" ? "success" : "default"} label={entry.status === "settled" ? "تسویه‌شده" : entry.status === "canceled" ? "لغوشده" : "باز"} /></div><small>{entry.jalali_date}، ساعت {entry.local_time} • {({ sale: "فروش", purchase: "خرید", settlement: "تسویه", cheque: "چک", manual: "سند دستی" } as Record<string, string>)[entry.source_type] ?? entry.source_type}</small><p>{entry.description || "بدون شرح"}</p></div><div className="ledger-entry-amount"><strong>{formatRial(entry.amount_rial)}</strong><small>مانده {formatRial(entry.remaining_rial)}</small></div></article>)}</div></section>
          </>}
        </main>
      </div>
      <Dialog open={personDialog} onClose={() => { if (!personSaving) setPersonDialog(false); }} fullWidth maxWidth="xs"><form onSubmit={submitPerson} noValidate><DialogTitle>ثبت شخص جدید</DialogTitle><DialogContent className="dialog-form">{personDialogError ? <Alert severity="error">{personDialogError}</Alert> : null}<TextField autoFocus label="نام شخص" value={personName} onChange={(event) => { setPersonName(event.target.value); setPersonDialogError(""); }} required disabled={personSaving} error={personName.length > 0 && !personName.trim()} helperText={personName.length > 0 && !personName.trim() ? "نام نمی‌تواند فقط فاصله باشد." : ""} /><TextField label="شماره تماس (اختیاری)" value={personPhone} onChange={(event) => setPersonPhone(event.target.value)} inputMode="tel" disabled={personSaving} /><TextField select label="نوع شخص" value={personType} onChange={(event) => setPersonType(event.target.value as Person["person_type"])} disabled={personSaving}><MenuItem value="customer">مشتری</MenuItem><MenuItem value="supplier">تأمین‌کننده</MenuItem><MenuItem value="both">مشتری و تأمین‌کننده</MenuItem></TextField></DialogContent><DialogActions><Button size="large" onClick={() => setPersonDialog(false)} disabled={personSaving}>انصراف</Button><Button size="large" type="submit" variant="contained" disabled={personSaving || !personName.trim()} startIcon={personSaving ? <CircularProgress size={18} color="inherit" /> : <AddRounded />}>ثبت شخص</Button></DialogActions></form></Dialog>
    </CrudWorkspace>
  );
}

function ChequesView({ onBack }: { onBack: () => void }) {
  const [people, setPeople] = useState<Person[]>([]);
  const [cheques, setCheques] = useState<Cheque[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"" | "received" | "paid">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dueFilter, setDueFilter] = useState<"all" | "due">("all");
  const [chequeType, setChequeType] = useState<"received" | "paid">("received");
  const [personId, setPersonId] = useState("");
  const [bank, setBank] = useState("");
  const [number, setNumber] = useState("");
  const [amount, setAmount] = useState("");
  const [issueDate, setIssueDate] = useState(currentJalaliDate);
  const [dueDate, setDueDate] = useState(currentJalaliDate);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [eventCheque, setEventCheque] = useState<Cheque | null>(null);
  const [eventType, setEventType] = useState<"cleared" | "bounced" | "canceled">("cleared");
  const [eventDate, setEventDate] = useState(currentJalaliDate);
  const [eventNote, setEventNote] = useState("");
  const [eventSaving, setEventSaving] = useState(false);
  const [eventDialogError, setEventDialogError] = useState("");
  const [historyId, setHistoryId] = useState<number | null>(null);
  const [duesDate, setDuesDate] = useState(currentJalaliDate);
  const [dues, setDues] = useState<Dues | null>(null);
  const [duesStatus, setDuesStatus] = useState<"loading" | "ready" | "error">("loading");

  async function load() {
    setStatus("loading");
    try { const [nextPeople, nextCheques] = await Promise.all([api.persons(), api.cheques()]); setPeople(nextPeople); setCheques(nextCheques); setStatus("ready"); }
    catch (error) { setStatus("error"); setNotice({ type: "error", text: error instanceof Error ? error.message : "چک‌ها دریافت نشدند." }); }
  }
  async function loadDues(date = duesDate) {
    setDuesStatus("loading");
    try { setDues(await api.dues(date)); setDuesStatus("ready"); }
    catch (error) { setDuesStatus("error"); setNotice({ type: "error", text: error instanceof Error ? error.message : "سررسیدها دریافت نشدند." }); }
  }
  useEffect(() => { load(); loadDues(); }, []);

  const pendingReceived = cheques.filter((cheque) => cheque.status === "pending" && cheque.cheque_type === "received");
  const pendingPaid = cheques.filter((cheque) => cheque.status === "pending" && cheque.cheque_type === "paid");
  const duePending = cheques.filter((cheque) => cheque.status === "pending" && cheque.due_jalali_date <= duesDate);
  const pendingTotal = [...pendingReceived, ...pendingPaid].reduce((sum, cheque) => sum + cheque.amount_rial, 0);
  const filteredCheques = cheques.filter((cheque) => {
    const person = people.find((item) => item.id === cheque.person_id);
    const matchesSearch = `${cheque.bank_name} ${cheque.cheque_number} ${person?.name ?? ""}`.toLowerCase().includes(search.trim().toLowerCase());
    return matchesSearch && (!typeFilter || cheque.cheque_type === typeFilter) && (!statusFilter || cheque.status === statusFilter) && (dueFilter === "all" || (cheque.status === "pending" && cheque.due_jalali_date <= duesDate));
  });
  const duesDebitRial = dues?.open_ledger_entries.filter((item) => item.entry_type === "debit").reduce((sum, item) => sum + item.remaining_rial, 0) ?? 0;
  const duesCreditRial = dues?.open_ledger_entries.filter((item) => item.entry_type === "credit").reduce((sum, item) => sum + item.remaining_rial, 0) ?? 0;

  async function submitCheque(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amountRial = normalizeMoney(amount);
    if (!bank.trim() || !number.trim() || amountRial <= 0) { setNotice({ type: "error", text: "بانک، شماره چک و مبلغ مثبت الزامی هستند." }); return; }
    if (dueDate < issueDate) { setNotice({ type: "error", text: "تاریخ سررسید نمی‌تواند پیش از تاریخ صدور باشد." }); return; }
    setSaving(true); setNotice(null);
    try {
      await api.createCheque({ cheque_type: chequeType, person_id: Number(personId) || null, bank_name: bank.trim(), cheque_number: number.trim(), amount_rial: amountRial, issue_jalali_date: issueDate, due_jalali_date: dueDate, local_time: currentLocalTime(), note: note.trim() || undefined });
      setBank(""); setNumber(""); setAmount(""); setNote(""); setPersonId(""); setNotice({ type: "success", text: "چک با موفقیت ثبت شد." }); await Promise.all([load(), loadDues()]);
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "ثبت چک انجام نشد." }); }
    finally { setSaving(false); }
  }

  function openEvent(cheque: Cheque, nextType: "cleared" | "bounced" | "canceled") {
    setEventCheque(cheque); setEventType(nextType); setEventDate(currentJalaliDate()); setEventNote(""); setEventDialogError(""); setNotice(null);
  }

  async function submitEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventCheque) return;
    const actionTime = currentLocalTime();
    const latestMoment = eventCheque.events.reduce((latest, item) => `${item.jalali_date} ${item.local_time}` > latest ? `${item.jalali_date} ${item.local_time}` : latest, `${eventCheque.issue_jalali_date} 00:00`);
    if (`${eventDate} ${actionTime}` < latestMoment) { setEventDialogError("زمان اقدام نمی‌تواند پیش از آخرین رویداد چک باشد."); return; }
    setEventSaving(true);
    try { await api.createChequeEvent(eventCheque.id, { event_type: eventType, jalali_date: eventDate, local_time: actionTime, note: eventNote.trim() || undefined }); setEventCheque(null); setNotice({ type: "success", text: "وضعیت چک ثبت شد." }); await Promise.all([load(), loadDues()]); }
    catch (error) { setEventDialogError(error instanceof Error ? error.message : "ثبت وضعیت انجام نشد."); }
    finally { setEventSaving(false); }
  }

  return (
    <CrudWorkspace title="دفتر چک‌ها و سررسیدها" eyebrow="دریافتی و پرداختی" onBack={onBack}>
      {notice ? <Alert severity={notice.type} onClose={() => setNotice(null)}>{notice.text}</Alert> : null}
      <div className="cheque-kpis"><div><small>دریافتی در انتظار</small><strong>{formatRial(pendingReceived.reduce((sum, item) => sum + item.amount_rial, 0))}</strong><span>{pendingReceived.length.toLocaleString("fa-IR")} فقره</span></div><div><small>پرداختی در انتظار</small><strong>{formatRial(pendingPaid.reduce((sum, item) => sum + item.amount_rial, 0))}</strong><span>{pendingPaid.length.toLocaleString("fa-IR")} فقره</span></div><div className="warning"><small>سررسید تا تاریخ پیگیری</small><strong>{duePending.length.toLocaleString("fa-IR")} فقره</strong><span>{toPersianDigits(duesDate)}</span></div><div><small>کل مبلغ در انتظار</small><strong>{formatRial(pendingTotal)}</strong><span>دریافتی و پرداختی</span></div></div>
      <div className="cheque-layout">
        <form className="sale-panel cheque-create-form" onSubmit={submitCheque} noValidate><div className="ledger-section-heading"><div><strong>ثبت چک جدید</strong><small>اطلاعات روی برگه چک را وارد کنید</small></div></div><div className="cheque-form-grid"><TextField select label="نوع چک" value={chequeType} onChange={(event) => setChequeType(event.target.value as "received" | "paid")} disabled={saving}><MenuItem value="received">دریافتی</MenuItem><MenuItem value="paid">پرداختی</MenuItem></TextField><TextField select label="شخص مرتبط (اختیاری)" value={personId} onChange={(event) => setPersonId(event.target.value)} disabled={saving}><MenuItem value="">بدون شخص</MenuItem>{people.map((person) => <MenuItem value={person.id} key={person.id}>{person.name}</MenuItem>)}</TextField><TextField label="نام بانک" value={bank} onChange={(event) => setBank(event.target.value)} required disabled={saving} error={bank.length > 0 && !bank.trim()} /><TextField label="شماره چک" value={number} onChange={(event) => setNumber(event.target.value)} required disabled={saving} slotProps={{ htmlInput: { dir: "ltr" } }} /><TextField label="مبلغ (تومان)" value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="numeric" required disabled={saving} /><JalaliDateField label="تاریخ صدور" value={issueDate} onChange={setIssueDate} required /><JalaliDateField label="تاریخ سررسید" value={dueDate} onChange={setDueDate} required /><TextField label="یادداشت (اختیاری)" value={note} onChange={(event) => setNote(event.target.value)} disabled={saving} /></div>{dueDate < issueDate ? <Alert severity="error">تاریخ سررسید نمی‌تواند پیش از تاریخ صدور باشد.</Alert> : null}<Button type="submit" variant="contained" size="large" disabled={saving || !bank.trim() || !number.trim() || normalizeMoney(amount) <= 0 || dueDate < issueDate} startIcon={saving ? <CircularProgress size={18} color="inherit" /> : <AddRounded />}>{saving ? "در حال ثبت…" : "ثبت چک"}</Button></form>
        <section className="sale-panel dues-panel"><div className="ledger-section-heading"><div><strong>سررسیدها</strong><small>تعهدهای باز تا تاریخ انتخابی</small></div></div><div className="dues-controls"><JalaliDateField label="تا تاریخ" value={duesDate} onChange={setDuesDate} /><Button variant="outlined" size="large" onClick={() => loadDues(duesDate)} disabled={duesStatus === "loading"}>{duesStatus === "loading" ? <CircularProgress size={18} /> : "به‌روزرسانی"}</Button></div>{duesStatus === "error" ? <div className="record-state record-state-error"><span>سررسیدها دریافت نشدند.</span><Button onClick={() => loadDues()}>تلاش دوباره</Button></div> : null}{duesStatus === "ready" && dues && dues.open_ledger_entries.length + dues.pending_cheques.length === 0 ? <div className="record-state"><FactCheckRounded /><strong>تعهد بازی تا این تاریخ نیست</strong></div> : null}{duesStatus === "ready" && dues ? <div className="dues-summary"><div><span>مانده بدهکار سررسیدشده</span><strong>{formatRial(duesDebitRial)}</strong><small>مطالبات فروشگاه</small></div><div><span>مانده بستانکار سررسیدشده</span><strong>{formatRial(duesCreditRial)}</strong><small>تعهد فروشگاه</small></div><div><span>خالص اسناد باز</span><strong>{formatRial(Math.abs(duesDebitRial - duesCreditRial))}</strong><small>{duesDebitRial > duesCreditRial ? "بدهکار" : duesCreditRial > duesDebitRial ? "بستانکار" : "تسویه"}</small></div><div><span>چک در انتظار</span><strong>{dues.pending_cheques.length.toLocaleString("fa-IR")} فقره</strong><small>{formatRial(dues.pending_cheques.reduce((sum, item) => sum + item.amount_rial, 0))}</small></div></div> : null}</section>
      </div>
      <section className="sale-panel cheque-list-panel"><div className="ledger-section-heading"><div><strong>فهرست چک‌ها</strong><small>جست‌وجو، پیگیری و مشاهده تاریخچه</small></div><Chip label={`${filteredCheques.length.toLocaleString("fa-IR")} نتیجه`} variant="outlined" /></div><div className="cheque-filters"><TextField size="small" label="بانک، شماره یا شخص" value={search} onChange={(event) => setSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} /><TextField select size="small" label="نوع" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as typeof typeFilter)}><MenuItem value="">همه</MenuItem><MenuItem value="received">دریافتی</MenuItem><MenuItem value="paid">پرداختی</MenuItem></TextField><TextField select size="small" label="وضعیت" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><MenuItem value="">همه</MenuItem><MenuItem value="pending">در انتظار</MenuItem><MenuItem value="cleared">وصول/پاس‌شده</MenuItem><MenuItem value="bounced">برگشتی</MenuItem><MenuItem value="canceled">باطل‌شده</MenuItem></TextField><TextField select size="small" label="سررسید" value={dueFilter} onChange={(event) => setDueFilter(event.target.value as typeof dueFilter)}><MenuItem value="all">همه تاریخ‌ها</MenuItem><MenuItem value="due">تا تاریخ پیگیری</MenuItem></TextField></div>{status === "loading" ? <div className="record-state"><CircularProgress size={26} /><span>در حال دریافت چک‌ها…</span></div> : null}{status === "error" ? <div className="record-state record-state-error"><span>فهرست چک‌ها دریافت نشد.</span><Button variant="outlined" startIcon={<RefreshRounded />} onClick={load}>تلاش دوباره</Button></div> : null}{status === "ready" && cheques.length === 0 ? <div className="record-state"><PaymentsRounded /><strong>هنوز چکی ثبت نشده است</strong></div> : null}{status === "ready" && cheques.length > 0 && filteredCheques.length === 0 ? <div className="record-state"><SearchRounded /><strong>چکی با این فیلتر پیدا نشد</strong></div> : null}<div className="cheque-cards">{filteredCheques.map((cheque) => { const person = people.find((item) => item.id === cheque.person_id); const statusLabel = ({ pending: "در انتظار", cleared: cheque.cheque_type === "received" ? "وصول‌شده" : "پاس‌شده", bounced: "برگشتی", canceled: "باطل‌شده" } as const)[cheque.status]; const canClear = cheque.status === "pending" || cheque.status === "bounced"; const canBounce = cheque.status === "pending"; const canCancel = cheque.status === "pending" || cheque.status === "bounced"; return <article className={`cheque-card status-${cheque.status}`} key={cheque.id}><div className="cheque-card-main"><div className="cheque-card-heading"><span className="cheque-bank-icon"><PaymentsRounded /></span><div><strong>{cheque.bank_name}</strong><small>شماره {toPersianDigits(cheque.cheque_number)}</small></div><Chip size="small" label={statusLabel} color={cheque.status === "cleared" ? "success" : cheque.status === "bounced" ? "error" : cheque.status === "pending" ? "warning" : "default"} /></div><div className="cheque-meta"><span><small>نوع</small><strong>{cheque.cheque_type === "received" ? "دریافتی" : "پرداختی"}</strong></span><span><small>شخص</small><strong>{person?.name || "ثبت نشده"}</strong></span><span><small>سررسید</small><strong>{toPersianDigits(cheque.due_jalali_date)}</strong></span></div></div><div className="cheque-card-amount"><small>مبلغ چک</small><strong>{formatRial(cheque.amount_rial)}</strong></div><div className="cheque-actions"><Button size="large" variant="outlined" color="success" disabled={!canClear} onClick={() => openEvent(cheque, "cleared")}>{cheque.cheque_type === "received" ? "وصول" : "پاس"}</Button><Button size="large" variant="outlined" color="error" disabled={!canBounce} onClick={() => openEvent(cheque, "bounced")}>برگشت</Button><Button size="large" disabled={!canCancel} onClick={() => openEvent(cheque, "canceled")}>ابطال</Button><Button size="large" startIcon={<HistoryRounded />} onClick={() => setHistoryId(historyId === cheque.id ? null : cheque.id)}>تاریخچه</Button></div>{historyId === cheque.id ? <div className="cheque-history">{cheque.events.map((item) => <div key={item.id}><span /><p><strong>{({ created: "ثبت چک", cleared: "وصول/پاس", bounced: "برگشت", canceled: "ابطال" } as const)[item.event_type]}</strong><small>{toPersianDigits(item.jalali_date)}، ساعت {toPersianDigits(item.local_time)}{item.note ? ` • ${item.note}` : ""}</small></p></div>)}</div> : null}</article>; })}</div></section>
      <Dialog open={eventCheque !== null} onClose={() => { if (!eventSaving) setEventCheque(null); }} fullWidth maxWidth="xs"><form onSubmit={submitEvent}><DialogTitle>{eventType === "cleared" ? (eventCheque?.cheque_type === "received" ? "ثبت وصول چک" : "ثبت پاس چک") : eventType === "bounced" ? "ثبت برگشت چک" : "ابطال چک"}</DialogTitle><DialogContent className="dialog-form"><Alert severity={eventType === "canceled" || eventType === "bounced" ? "warning" : "info"}>این اقدام در تاریخچه چک ثبت می‌شود. اطلاعات را پیش از تأیید بررسی کنید.</Alert>{eventDialogError ? <Alert severity="error">{eventDialogError}</Alert> : null}<JalaliDateField label="تاریخ اقدام" value={eventDate} onChange={(value) => { setEventDate(value); setEventDialogError(""); }} required /><TextField label="یادداشت (اختیاری)" value={eventNote} onChange={(event) => setEventNote(event.target.value)} multiline minRows={2} disabled={eventSaving} /></DialogContent><DialogActions><Button size="large" onClick={() => setEventCheque(null)} disabled={eventSaving}>انصراف</Button><Button size="large" type="submit" variant="contained" color={eventType === "cleared" ? "success" : "error"} disabled={eventSaving} startIcon={eventSaving ? <CircularProgress size={18} color="inherit" /> : <FactCheckRounded />}>تأیید و ثبت</Button></DialogActions></form></Dialog>
    </CrudWorkspace>
  );
}

function ReportsView({ onBack }: { onBack: () => void }) {
  type ReportKey = "sales" | "profit" | "inventory" | "cashflow" | "debts";
  type LoadState = "idle" | "loading" | "ready" | "error";
  const emptyStates: Record<ReportKey, LoadState> = { sales: "idle", profit: "idle", inventory: "idle", cashflow: "idle", debts: "idle" };
  const [from, setFrom] = useState(currentJalaliDate);
  const [to, setTo] = useState(currentJalaliDate);
  const [sales, setSales] = useState<SalesSummaryReport | null>(null);
  const [profit, setProfit] = useState<ProfitLossReport | null>(null);
  const [inventory, setInventory] = useState<InventoryReport | null>(null);
  const [cashflow, setCashflow] = useState<CashflowReport | null>(null);
  const [debts, setDebts] = useState<CustomerDebtsReport | null>(null);
  const [states, setStates] = useState<Record<ReportKey, LoadState>>(emptyStates);
  const [rangeError, setRangeError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  async function loadReports(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!from || !to || from > to) {
      setRangeError("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.");
      return;
    }
    setRangeError("");
    setStates({ sales: "loading", profit: "loading", inventory: "loading", cashflow: "loading", debts: "loading" });
    const jobs = [api.salesSummary(from, to), api.profitLoss(from, to), api.inventoryReport(), api.cashflow(to), api.customerDebts()] as const;
    const results = await Promise.allSettled(jobs);
    const nextStates = { ...emptyStates };
    const keys: ReportKey[] = ["sales", "profit", "inventory", "cashflow", "debts"];
    results.forEach((result, index) => { nextStates[keys[index]] = result.status === "fulfilled" ? "ready" : "error"; });
    if (results[0].status === "fulfilled") setSales(results[0].value); else setSales(null);
    if (results[1].status === "fulfilled") setProfit(results[1].value); else setProfit(null);
    if (results[2].status === "fulfilled") setInventory(results[2].value); else setInventory(null);
    if (results[3].status === "fulfilled") setCashflow(results[3].value); else setCashflow(null);
    if (results[4].status === "fulfilled") setDebts(results[4].value); else setDebts(null);
    setStates(nextStates);
    setLastUpdated(currentLocalTime());
  }
  useEffect(() => { loadReports(); }, []);

  const failedCount = Object.values(states).filter((state) => state === "error").length;
  const loading = Object.values(states).some((state) => state === "loading");
  const allFailed = failedCount === 5;
  const lowStockItems = inventory?.items.filter((item) => item.needs_reorder) ?? [];
  const collectionRate = sales && sales.registered_sales_rial > 0
    ? Math.round((sales.received_rial / sales.registered_sales_rial) * 100)
    : 0;

  return (
    <CrudWorkspace title="گزارش‌ها" eyebrow="فروش، سود، انبار و جریان نقد" onBack={onBack}>
      <form className="report-toolbar sale-panel" onSubmit={loadReports} noValidate>
        <div className="report-toolbar-copy"><strong>بازه گزارش</strong><small>فروش و سود در این بازه؛ جریان نقد تا تاریخ پایان</small></div>
        <JalaliDateField label="از تاریخ" value={from} onChange={(value) => { setFrom(value); setRangeError(""); }} required />
        <JalaliDateField label="تا تاریخ" value={to} onChange={(value) => { setTo(value); setRangeError(""); }} required />
        <Button type="submit" variant="contained" size="large" disabled={loading} startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <RefreshRounded />}>
          {loading ? "در حال دریافت…" : "به‌روزرسانی گزارش"}
        </Button>
        {lastUpdated ? <small className="report-updated">آخرین دریافت: ساعت {toPersianDigits(lastUpdated)}</small> : null}
      </form>
      {rangeError ? <Alert severity="error">{rangeError}</Alert> : null}
      {allFailed ? <Alert severity="error" action={<Button color="inherit" onClick={() => loadReports()}>تلاش دوباره</Button>}>هیچ‌یک از گزارش‌ها دریافت نشد.</Alert> : null}
      {failedCount > 0 && !allFailed ? <Alert severity="warning" action={<Button color="inherit" onClick={() => loadReports()}>دریافت دوباره</Button>}>بخشی از گزارش‌ها در دسترس نیست؛ اطلاعات موفق حفظ شده‌اند.</Alert> : null}
      {loading ? <LinearProgress aria-label="در حال دریافت گزارش‌ها" /> : null}

      <div className="report-kpis">
        <article><span>فروش ثبت‌شده</span><strong>{sales ? formatRial(sales.registered_sales_rial) : "—"}</strong><small>{sales ? `${sales.invoice_count.toLocaleString("fa-IR")} فاکتور • میانگین ${formatRial(sales.average_invoice_rial)}` : "در انتظار داده"}</small></article>
        <article className="positive"><span>وصول فروش</span><strong>{sales ? formatRial(sales.received_rial) : "—"}</strong><small>{sales ? `${collectionRate.toLocaleString("fa-IR")}٪ از فروش بازه` : "در انتظار داده"}</small></article>
        <article className={profit && profit.gross_profit_rial < 0 ? "negative" : "positive"}><span>سود ناخالص تخمینی</span><strong>{profit ? formatRial(profit.gross_profit_rial) : "—"}</strong><small>{profit ? `حاشیه ${profit.gross_margin_percent.toLocaleString("fa-IR")}٪ • بهای تخمینی ${formatRial(profit.estimated_cost_rial)}` : "در انتظار داده"}</small></article>
        <article><span>ارزش موجودی</span><strong>{inventory ? formatRial(inventory.total_value_rial) : "—"}</strong><small>{inventory ? `${inventory.item_count.toLocaleString("fa-IR")} گونه • ${inventory.low_stock_count.toLocaleString("fa-IR")} کم‌موجود` : "در انتظار داده"}</small></article>
        <article className={cashflow && cashflow.net_expected_rial < 0 ? "negative" : "positive"}><span>جریان نقد مورد انتظار</span><strong>{cashflow ? formatRial(cashflow.net_expected_rial) : "—"}</strong><small>تا پایان بازه انتخابی</small></article>
        <article className={debts?.total_remaining_rial ? "warning" : "positive"}><span>مطالبات از مشتریان</span><strong>{debts ? formatRial(debts.total_remaining_rial) : "—"}</strong><small>{debts ? `${debts.people.length.toLocaleString("fa-IR")} مشتری بدهکار` : "در انتظار داده"}</small></article>
      </div>

      <div className="report-detail-grid">
        <section className="sale-panel report-breakdown">
          <div className="ledger-section-heading"><div><strong>اجزای جریان نقد</strong><small>ورودی‌ها و تعهدها تا {toPersianDigits(to)}</small></div></div>
          {states.cashflow === "error" ? <div className="record-state record-state-error"><span>جریان نقد دریافت نشد.</span><Button onClick={() => loadReports()}>تلاش دوباره</Button></div> : null}
          {states.cashflow === "loading" && !cashflow ? <div className="record-state"><CircularProgress size={26} /><span>در حال محاسبه…</span></div> : null}
          {cashflow ? <div className="cashflow-components">
            <div><span>اقساط زمان‌بندی‌شده فروش</span><strong className="text-ok">+ {formatRial(cashflow.pending_sales_payments_rial)}</strong></div>
            <div><span>مانده تخصیص‌نیافته فروش</span><strong className="text-ok">+ {formatRial(cashflow.unallocated_sales_due_rial)}</strong></div>
            <div><span>اسناد بدهکار مشتریان</span><strong className="text-ok">+ {formatRial(cashflow.open_customer_receivables_rial)}</strong></div>
            <div><span>چک‌های دریافتی</span><strong className="text-ok">+ {formatRial(cashflow.pending_received_cheques_rial)}</strong></div>
            <div><span>تعهد تأمین‌کنندگان</span><strong className="text-danger">− {formatRial(cashflow.open_supplier_payables_rial)}</strong></div>
            <div><span>چک‌های پرداختی</span><strong className="text-danger">− {formatRial(cashflow.pending_paid_cheques_rial)}</strong></div>
          </div> : null}
        </section>

        <section className="sale-panel report-list-panel">
          <div className="ledger-section-heading"><div><strong>کالاهای کم‌موجود</strong><small>موجودی برابر یا کمتر از نقطه سفارش</small></div><Chip size="small" color={lowStockItems.length ? "warning" : "success"} label={`${lowStockItems.length.toLocaleString("fa-IR")} مورد`} /></div>
          {states.inventory === "error" ? <div className="record-state record-state-error"><span>جزئیات انبار دریافت نشد.</span></div> : null}
          {states.inventory === "loading" && !inventory ? <div className="record-state"><CircularProgress size={26} /></div> : null}
          {inventory && lowStockItems.length === 0 ? <div className="record-state"><FactCheckRounded /><strong>هیچ کالای کم‌موجودی نیست</strong></div> : null}
          <div className="report-item-list">{lowStockItems.map((item) => <article key={item.variant_id}><div><strong>{item.variant_name}</strong><small>ارزش {formatRial(item.estimated_value_rial)}</small></div><div><span>{formatDecimal(item.quantity_on_hand)} موجود</span><small>نقطه سفارش {formatDecimal(item.reorder_level ?? 0)}</small></div></article>)}</div>
        </section>

        <section className="sale-panel report-list-panel report-debtors">
          <div className="ledger-section-heading"><div><strong>بدهکاران</strong><small>مانده خالص بدهکار منهای بستانکار هر شخص</small></div><Chip size="small" label={debts ? formatRial(debts.total_remaining_rial) : "—"} /></div>
          {states.debts === "error" ? <div className="record-state record-state-error"><span>مطالبات مشتریان دریافت نشد.</span></div> : null}
          {states.debts === "loading" && !debts ? <div className="record-state"><CircularProgress size={26} /></div> : null}
          {debts && debts.people.length === 0 ? <div className="record-state"><FactCheckRounded /><strong>مشتری بدهکاری وجود ندارد</strong></div> : null}
          <div className="report-item-list">{debts?.people.map((person) => <article key={person.person_id}><div><strong>{person.person_name}</strong><small>مانده باز حساب</small></div><strong className="text-danger">{formatRial(person.remaining_rial)}</strong></article>)}</div>
        </section>
      </div>
    </CrudWorkspace>
  );
}

function OnlineView({ onBack }: { onBack: () => void }) {
  type OnlineSection = "channels" | "rules" | "reservations" | "orders" | "variants";
  type LoadState = "loading" | "ready" | "error";
  const initialStates: Record<OnlineSection, LoadState> = { channels: "loading", rules: "loading", reservations: "loading", orders: "loading", variants: "loading" };
  const [tab, setTab] = useState(0);
  const [channels, setChannels] = useState<OnlineChannel[]>([]);
  const [rules, setRules] = useState<OnlinePriceRule[]>([]);
  const [reservations, setReservations] = useState<StockReservation[]>([]);
  const [orders, setOrders] = useState<OnlineOrder[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [states, setStates] = useState(initialStates);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [channelName, setChannelName] = useState("");
  const [channelToken, setChannelToken] = useState("");
  const [showChannelToken, setShowChannelToken] = useState(false);
  const [channelNote, setChannelNote] = useState("");
  const [channelSaving, setChannelSaving] = useState(false);
  const [ruleChannelId, setRuleChannelId] = useState("");
  const [ruleVariantId, setRuleVariantId] = useState("");
  const [rulePrice, setRulePrice] = useState("");
  const [ruleMinQuantity, setRuleMinQuantity] = useState("1");
  const [ruleStarts, setRuleStarts] = useState(currentJalaliDate);
  const [ruleEnds, setRuleEnds] = useState("");
  const [ruleSaving, setRuleSaving] = useState(false);
  const [reservationChannelId, setReservationChannelId] = useState("");
  const [reservationVariantId, setReservationVariantId] = useState("");
  const [reservationQuantity, setReservationQuantity] = useState("1");
  const [reservationExpiry, setReservationExpiry] = useState(currentJalaliDate);
  const [reservationNote, setReservationNote] = useState("");
  const [reservationSaving, setReservationSaving] = useState(false);
  const [channelSearch, setChannelSearch] = useState("");
  const [ruleChannelFilter, setRuleChannelFilter] = useState("");
  const [ruleVariantFilter, setRuleVariantFilter] = useState("");
  const [reservationChannelFilter, setReservationChannelFilter] = useState("");
  const [reservationStatusFilter, setReservationStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [orderStatusFilter, setOrderStatusFilter] = useState("");
  const [orderSearch, setOrderSearch] = useState("");
  const [expandedOrder, setExpandedOrder] = useState<number | null>(null);

  async function loadSection(section: OnlineSection) {
    setStates((current) => ({ ...current, [section]: "loading" }));
    try {
      if (section === "channels") setChannels(await api.onlineChannels());
      if (section === "rules") setRules(await api.onlinePriceRules());
      if (section === "reservations") setReservations(await api.stockReservations({ asOf: currentJalaliDate() }));
      if (section === "orders") setOrders(await api.onlineOrders());
      if (section === "variants") setVariants((await api.productVariants()).filter((item) => item.is_active));
      setStates((current) => ({ ...current, [section]: "ready" }));
    } catch {
      setStates((current) => ({ ...current, [section]: "error" }));
    }
  }

  useEffect(() => {
    (["channels", "rules", "reservations", "orders", "variants"] as OnlineSection[]).forEach((section) => { loadSection(section); });
  }, []);

  async function submitChannel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!channelName.trim() || channelToken.length < 16) return;
    setChannelSaving(true); setNotice(null);
    try {
      await api.createOnlineChannel({ name: channelName.trim(), token: channelToken, note: channelNote.trim() || undefined });
      setChannelName(""); setChannelToken(""); setShowChannelToken(false); setChannelNote("");
      setNotice({ type: "success", text: "کانال آنلاین ثبت شد. توکن متنی دیگر از سرور قابل بازیابی نیست." });
      await loadSection("channels");
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "ثبت کانال انجام نشد." }); }
    finally { setChannelSaving(false); }
  }

  async function submitRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const price = normalizeMoney(rulePrice);
    const quantity = parseLocalizedNumber(ruleMinQuantity);
    if (!ruleChannelId || !ruleVariantId || price <= 0 || quantity <= 0 || (ruleEnds && ruleStarts > ruleEnds)) return;
    setRuleSaving(true); setNotice(null);
    try {
      await api.createOnlinePriceRule({ channel_id: Number(ruleChannelId), variant_id: Number(ruleVariantId), price_rial: price, min_quantity: quantity, starts_jalali_date: ruleStarts || null, ends_jalali_date: ruleEnds || null });
      setRulePrice(""); setRuleMinQuantity("1"); setRuleEnds("");
      setNotice({ type: "success", text: "قانون قیمت آنلاین ثبت شد." });
      await loadSection("rules");
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "ثبت قانون قیمت انجام نشد." }); }
    finally { setRuleSaving(false); }
  }

  async function submitReservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const quantity = parseLocalizedNumber(reservationQuantity);
    if (!reservationChannelId || !reservationVariantId || quantity <= 0 || reservationExpiry < currentJalaliDate()) return;
    setReservationSaving(true); setNotice(null);
    try {
      await api.createStockReservation({ channel_id: Number(reservationChannelId), variant_id: Number(reservationVariantId), quantity, expires_jalali_date: reservationExpiry || null, local_time: currentLocalTime(), note: reservationNote.trim() || undefined });
      setReservationQuantity("1"); setReservationNote("");
      setNotice({ type: "success", text: "رزرو دستی ثبت شد." });
      await loadSection("reservations");
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "ثبت رزرو انجام نشد." }); }
    finally { setReservationSaving(false); }
  }

  const filteredOrders = orders.filter((order) => {
    const matchesChannel = !channelFilter || order.channel_id === Number(channelFilter);
    const matchesStatus = !orderStatusFilter || order.status === orderStatusFilter;
    const needle = orderSearch.trim().toLocaleLowerCase("fa-IR");
    const matchesSearch = !needle || [order.external_order_id, order.customer_name, order.customer_phone].some((value) => value?.toLocaleLowerCase("fa-IR").includes(needle));
    return matchesChannel && matchesStatus && matchesSearch;
  });
  const filteredChannels = channels.filter((channel) => channel.name.toLocaleLowerCase("fa-IR").includes(channelSearch.trim().toLocaleLowerCase("fa-IR")));
  const filteredRules = rules.filter((rule) => (!ruleChannelFilter || rule.channel_id === Number(ruleChannelFilter)) && (!ruleVariantFilter || rule.variant_id === Number(ruleVariantFilter)));
  const filteredReservations = reservations.filter((reservation) => {
    const effectiveStatus = reservation.is_expired ? "expired" : reservation.status;
    return (!reservationChannelFilter || reservation.channel_id === Number(reservationChannelFilter)) && (!reservationStatusFilter || effectiveStatus === reservationStatusFilter);
  });
  const channelNameFor = (id: number) => channels.find((channel) => channel.id === id)?.name ?? `کانال ${id.toLocaleString("fa-IR")}`;
  const variantNameFor = (id: number) => variants.find((variant) => variant.id === id)?.name ?? `کالا ${id.toLocaleString("fa-IR")}`;
  const orderStatusLabel = (status: string) => ({ pending: "در انتظار", confirmed: "تأییدشده", canceled: "لغوشده", converted: "تبدیل‌شده" } as Record<string, string>)[status] ?? status;

  function retryFormDependencies() {
    if (states.channels === "error") loadSection("channels");
    if (states.variants === "error") loadSection("variants");
  }

  const SectionState = ({ section, empty, hasItems }: { section: OnlineSection; empty: string; hasItems: boolean }) => states[section] === "loading" ? <div className="record-state"><CircularProgress size={26} /><span>در حال دریافت…</span></div> : states[section] === "error" ? <div className="record-state record-state-error"><strong>دریافت اطلاعات انجام نشد</strong><Button variant="outlined" startIcon={<RefreshRounded />} onClick={() => loadSection(section)}>تلاش دوباره</Button></div> : !hasItems ? <div className="record-state"><StorefrontRounded /><strong>{empty}</strong></div> : null;

  return (
    <CrudWorkspace title="عملیات آنلاین" eyebrow="کانال‌ها، قیمت، رزرو و سفارش" onBack={onBack}>
      {notice ? <Alert severity={notice.type} onClose={() => setNotice(null)}>{notice.text}</Alert> : null}
      <section className="sale-panel online-tabs-panel">
        <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto" aria-label="بخش‌های عملیات آنلاین">
          <Tab label="کانال‌ها" /><Tab label="قیمت‌ها" /><Tab label="رزروها" /><Tab label="سفارش‌ها" />
        </Tabs>
      </section>

      {tab === 0 ? <div className="online-split">
        <form className="sale-panel online-form" onSubmit={submitChannel} noValidate>
          <div className="ledger-section-heading"><div><strong>اتصال کانال جدید</strong><small>برای سایت، اپ یا بازارگاه یک کلید مستقل بسازید</small></div></div>
          <TextField label="نام کانال" value={channelName} onChange={(event) => setChannelName(event.target.value)} required disabled={channelSaving} error={channelName.length > 0 && !channelName.trim()} />
          <TextField type={showChannelToken ? "text" : "password"} label="توکن اتصال" value={channelToken} onChange={(event) => setChannelToken(event.target.value)} required disabled={channelSaving} error={channelToken.length > 0 && channelToken.length < 16} helperText={channelToken.length > 0 && channelToken.length < 16 ? "توکن باید دست‌کم ۱۶ نویسه باشد." : "توکن فقط همین‌جا وارد می‌شود و بعداً از سرور قابل بازیابی نیست."} slotProps={{ htmlInput: { autoComplete: "new-password", dir: "ltr" }, input: { endAdornment: <InputAdornment position="end"><Button size="small" onClick={() => setShowChannelToken((value) => !value)}>{showChannelToken ? "پنهان" : "نمایش"}</Button></InputAdornment> } }} />
          <TextField label="یادداشت (اختیاری)" value={channelNote} onChange={(event) => setChannelNote(event.target.value)} multiline minRows={2} disabled={channelSaving} />
          <Alert severity="info">توکن را در مدیر رمز عبور امن نگه دارید؛ سامانه فقط هش آن را ذخیره می‌کند.</Alert>
          <Button type="submit" variant="contained" size="large" disabled={channelSaving || !channelName.trim() || channelToken.length < 16} startIcon={channelSaving ? <CircularProgress size={18} color="inherit" /> : <AddRounded />}>{channelSaving ? "در حال ثبت…" : "ثبت کانال"}</Button>
        </form>
        <section className="sale-panel online-list-panel"><div className="ledger-section-heading"><div><strong>کانال‌های فعال</strong><small>توکن ذخیره‌شده هیچ‌گاه نمایش داده نمی‌شود</small></div><Chip label={`${filteredChannels.length.toLocaleString("fa-IR")} کانال`} /></div><div className="online-list-filters single"><TextField size="small" label="جست‌وجوی کانال" value={channelSearch} onChange={(event) => setChannelSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} /></div><SectionState section="channels" hasItems={channels.length > 0} empty="هنوز کانالی تعریف نشده است" />{states.channels === "ready" && channels.length > 0 && filteredChannels.length === 0 ? <div className="record-state"><SearchRounded /><strong>کانالی با این جست‌وجو پیدا نشد</strong></div> : null}<div className="online-card-list">{filteredChannels.map((channel) => <article key={channel.id}><span className="online-card-icon"><SyncRounded /></span><div><strong>{channel.name}</strong><small>{channel.note || "بدون یادداشت"}</small></div><Chip size="small" color="success" label="فعال" /></article>)}</div></section>
      </div> : null}

      {tab === 1 ? <div className="online-split">
        <form className="sale-panel online-form" onSubmit={submitRule} noValidate>
          <div className="ledger-section-heading"><div><strong>قانون قیمت کانال</strong><small>قیمت ویژه یک کالا برای کانال و بازه مشخص</small></div></div>
          {states.channels === "error" || states.variants === "error" ? <Alert severity="error" action={<Button color="inherit" onClick={retryFormDependencies}>تلاش دوباره</Button>}>فهرست کانال یا کالا دریافت نشده و فرم فعلاً قابل ثبت نیست.</Alert> : null}
          <TextField select label="کانال" value={ruleChannelId} onChange={(event) => setRuleChannelId(event.target.value)} required disabled={ruleSaving || states.channels !== "ready"}><MenuItem value="">انتخاب کنید</MenuItem>{channels.map((channel) => <MenuItem key={channel.id} value={channel.id}>{channel.name}</MenuItem>)}</TextField>
          <TextField select label="کالا" value={ruleVariantId} onChange={(event) => setRuleVariantId(event.target.value)} required disabled={ruleSaving || states.variants !== "ready"}><MenuItem value="">انتخاب کنید</MenuItem>{variants.map((variant) => <MenuItem key={variant.id} value={variant.id}>{variant.name}</MenuItem>)}</TextField>
          <div className="online-form-row"><TextField label="قیمت آنلاین (تومان)" value={rulePrice} onChange={(event) => setRulePrice(event.target.value)} inputMode="numeric" required error={rulePrice.length > 0 && normalizeMoney(rulePrice) <= 0} /><TextField label="حداقل تعداد" value={ruleMinQuantity} onChange={(event) => setRuleMinQuantity(event.target.value)} inputMode="decimal" required error={parseLocalizedNumber(ruleMinQuantity) <= 0} /></div>
          <div className="online-form-row"><JalaliDateField label="شروع" value={ruleStarts} onChange={setRuleStarts} /><JalaliDateField label="پایان (اختیاری)" value={ruleEnds} onChange={setRuleEnds} /></div>
          {ruleEnds && ruleStarts > ruleEnds ? <Alert severity="error">تاریخ پایان نمی‌تواند پیش از شروع باشد.</Alert> : null}
          <Button type="submit" variant="contained" size="large" disabled={ruleSaving || states.channels !== "ready" || states.variants !== "ready" || !ruleChannelId || !ruleVariantId || normalizeMoney(rulePrice) <= 0 || parseLocalizedNumber(ruleMinQuantity) <= 0 || Boolean(ruleEnds && ruleStarts > ruleEnds)} startIcon={ruleSaving ? <CircularProgress size={18} color="inherit" /> : <LocalOfferRounded />}>{ruleSaving ? "در حال ثبت…" : "ثبت قانون قیمت"}</Button>
        </form>
        <section className="sale-panel online-list-panel"><div className="ledger-section-heading"><div><strong>قوانین فعال</strong><small>جدیدترین قانون در اولویت است</small></div><Chip label={`${filteredRules.length.toLocaleString("fa-IR")} قانون`} /></div><div className="online-list-filters"><TextField select size="small" label="کانال" value={ruleChannelFilter} onChange={(event) => setRuleChannelFilter(event.target.value)}><MenuItem value="">همه</MenuItem>{channels.map((channel) => <MenuItem key={channel.id} value={channel.id}>{channel.name}</MenuItem>)}</TextField><TextField select size="small" label="کالا" value={ruleVariantFilter} onChange={(event) => setRuleVariantFilter(event.target.value)}><MenuItem value="">همه</MenuItem>{variants.map((variant) => <MenuItem key={variant.id} value={variant.id}>{variant.name}</MenuItem>)}</TextField></div><SectionState section="rules" hasItems={rules.length > 0} empty="هنوز قانون قیمت آنلاینی ثبت نشده است" />{states.rules === "ready" && rules.length > 0 && filteredRules.length === 0 ? <div className="record-state"><SearchRounded /><strong>قانونی با این فیلتر پیدا نشد</strong></div> : null}<div className="online-card-list">{filteredRules.map((rule) => <article key={rule.id}><span className="online-card-icon"><LocalOfferRounded /></span><div><strong>{variantNameFor(rule.variant_id)}</strong><small>{channelNameFor(rule.channel_id)} • از تعداد {formatDecimal(rule.min_quantity)} • {rule.starts_jalali_date ? `از ${toPersianDigits(rule.starts_jalali_date)}` : "بدون شروع"}{rule.ends_jalali_date ? ` تا ${toPersianDigits(rule.ends_jalali_date)}` : ""}</small></div><strong>{formatRial(rule.price_rial)}</strong></article>)}</div></section>
      </div> : null}

      {tab === 2 ? <div className="online-split">
        <form className="sale-panel online-form" onSubmit={submitReservation} noValidate>
          <div className="ledger-section-heading"><div><strong>رزرو دستی موجودی</strong><small>رزرو منقضی به‌طور خودکار از موجودی قابل فروش کنار گذاشته می‌شود</small></div></div>
          {states.channels === "error" || states.variants === "error" ? <Alert severity="error" action={<Button color="inherit" onClick={retryFormDependencies}>تلاش دوباره</Button>}>فهرست کانال یا کالا دریافت نشده و فرم فعلاً قابل ثبت نیست.</Alert> : null}
          <TextField select label="کانال" value={reservationChannelId} onChange={(event) => setReservationChannelId(event.target.value)} required disabled={reservationSaving || states.channels !== "ready"}><MenuItem value="">انتخاب کنید</MenuItem>{channels.map((channel) => <MenuItem key={channel.id} value={channel.id}>{channel.name}</MenuItem>)}</TextField>
          <TextField select label="کالا" value={reservationVariantId} onChange={(event) => setReservationVariantId(event.target.value)} required disabled={reservationSaving || states.variants !== "ready"}><MenuItem value="">انتخاب کنید</MenuItem>{variants.map((variant) => <MenuItem key={variant.id} value={variant.id}>{variant.name}</MenuItem>)}</TextField>
          <div className="online-form-row"><TextField label="تعداد" value={reservationQuantity} onChange={(event) => setReservationQuantity(event.target.value)} inputMode="decimal" required error={parseLocalizedNumber(reservationQuantity) <= 0} /><JalaliDateField label="تاریخ انقضا" value={reservationExpiry} onChange={setReservationExpiry} required /></div>
          {reservationExpiry < currentJalaliDate() ? <Alert severity="error">تاریخ انقضا نمی‌تواند پیش از امروز باشد.</Alert> : null}
          <TextField label="یادداشت (اختیاری)" value={reservationNote} onChange={(event) => setReservationNote(event.target.value)} multiline minRows={2} />
          <Button type="submit" variant="contained" size="large" disabled={reservationSaving || states.channels !== "ready" || states.variants !== "ready" || !reservationChannelId || !reservationVariantId || parseLocalizedNumber(reservationQuantity) <= 0 || reservationExpiry < currentJalaliDate()} startIcon={reservationSaving ? <CircularProgress size={18} color="inherit" /> : <Inventory2Rounded />}>{reservationSaving ? "در حال ثبت…" : "ثبت رزرو"}</Button>
        </form>
        <section className="sale-panel online-list-panel"><div className="ledger-section-heading"><div><strong>رزروهای موجودی</strong><small>رزروهای سفارش و رزروهای دستی</small></div><Chip label={`${filteredReservations.length.toLocaleString("fa-IR")} رزرو`} /></div><div className="online-list-filters"><TextField select size="small" label="کانال" value={reservationChannelFilter} onChange={(event) => setReservationChannelFilter(event.target.value)}><MenuItem value="">همه</MenuItem>{channels.map((channel) => <MenuItem key={channel.id} value={channel.id}>{channel.name}</MenuItem>)}</TextField><TextField select size="small" label="وضعیت" value={reservationStatusFilter} onChange={(event) => setReservationStatusFilter(event.target.value)}><MenuItem value="">همه</MenuItem><MenuItem value="reserved">فعال</MenuItem><MenuItem value="expired">منقضی</MenuItem><MenuItem value="released">آزادشده</MenuItem></TextField></div><SectionState section="reservations" hasItems={reservations.length > 0} empty="هنوز رزروی ثبت نشده است" />{states.reservations === "ready" && reservations.length > 0 && filteredReservations.length === 0 ? <div className="record-state"><SearchRounded /><strong>رزروی با این فیلتر پیدا نشد</strong></div> : null}<div className="online-card-list">{filteredReservations.map((reservation) => <article key={reservation.id} className={reservation.is_expired ? "muted" : ""}><span className="online-card-icon"><Inventory2Rounded /></span><div><strong>{variantNameFor(reservation.variant_id)}</strong><small>{channelNameFor(reservation.channel_id)} • {formatDecimal(reservation.quantity)} واحد • {reservation.expires_jalali_date ? `تا ${toPersianDigits(reservation.expires_jalali_date)}` : "بدون انقضا"}{reservation.order_id ? ` • سفارش ${reservation.order_id.toLocaleString("fa-IR")}` : ""}</small></div><Chip size="small" color={reservation.is_expired ? "default" : reservation.status === "reserved" ? "warning" : "success"} label={reservation.is_expired ? "منقضی" : reservation.status === "reserved" ? "رزروشده" : reservation.status} /></article>)}</div></section>
      </div> : null}

      {tab === 3 ? <section className="sale-panel online-orders-panel">
        <div className="ledger-section-heading"><div><strong>سفارش‌های آنلاین</strong><small>جزئیات دریافتی از همه کانال‌ها</small></div><Chip label={`${filteredOrders.length.toLocaleString("fa-IR")} نتیجه`} /></div>
        <div className="online-order-filters"><TextField size="small" label="شناسه، مشتری یا تلفن" value={orderSearch} onChange={(event) => setOrderSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} /><TextField select size="small" label="کانال" value={channelFilter} onChange={(event) => setChannelFilter(event.target.value)}><MenuItem value="">همه کانال‌ها</MenuItem>{channels.map((channel) => <MenuItem key={channel.id} value={channel.id}>{channel.name}</MenuItem>)}</TextField><TextField select size="small" label="وضعیت" value={orderStatusFilter} onChange={(event) => setOrderStatusFilter(event.target.value)}><MenuItem value="">همه وضعیت‌ها</MenuItem><MenuItem value="pending">در انتظار</MenuItem><MenuItem value="confirmed">تأییدشده</MenuItem><MenuItem value="canceled">لغوشده</MenuItem><MenuItem value="converted">تبدیل‌شده</MenuItem></TextField></div>
        <SectionState section="orders" hasItems={orders.length > 0} empty="هنوز سفارش آنلاینی دریافت نشده است" />
        {states.orders === "ready" && orders.length > 0 && filteredOrders.length === 0 ? <div className="record-state"><SearchRounded /><strong>سفارشی با این فیلتر پیدا نشد</strong></div> : null}
        <div className="online-order-list">{filteredOrders.map((order) => <article key={order.id} className="online-order-card"><button type="button" className="online-order-summary" onClick={() => setExpandedOrder(expandedOrder === order.id ? null : order.id)} aria-expanded={expandedOrder === order.id}><div><strong>سفارش {toPersianDigits(order.external_order_id)}</strong><small>{channelNameFor(order.channel_id)} • {order.customer_name || "مشتری نامشخص"}</small></div><div><strong>{formatRial(order.total_rial)}</strong><Chip size="small" color={order.status === "canceled" ? "error" : order.status === "pending" ? "warning" : "success"} label={orderStatusLabel(order.status)} /></div></button>{expandedOrder === order.id ? <div className="online-order-details"><div className="online-order-meta"><span><small>تاریخ</small><strong>{toPersianDigits(order.jalali_date)}، {toPersianDigits(order.local_time)}</strong></span><span><small>تلفن مشتری</small><strong>{order.customer_phone ? toPersianDigits(order.customer_phone) : "ثبت نشده"}</strong></span><span><small>جمع قبل تخفیف</small><strong>{formatRial(order.subtotal_rial)}</strong></span><span><small>تخفیف</small><strong>{formatRial(order.discount_amount_rial)}</strong></span></div><div className="online-order-lines">{order.items.map((item) => <div key={item.id}><span><strong>{item.product_snapshot}</strong><small>{formatDecimal(item.quantity)} × {formatRial(item.unit_price_rial)}</small></span><strong>{formatRial(item.line_total_rial)}</strong></div>)}</div></div> : null}</article>)}</div>
      </section> : null}
    </CrudWorkspace>
  );
}

function CrudWorkspace({ title, eyebrow, onBack, children }: { title: string; eyebrow: string; onBack: () => void; children: ReactNode }) {
  return (
    <section className="sales-workspace">
      <div className="sales-header">
        <div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>
        <button type="button" className="ghost-button" onClick={onBack}>بازگشت به داشبورد</button>
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric-card"><span>{label}</span><strong>{value}</strong></div>;
}

function SimpleTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  if (!rows.length) return <p className="state-message">هنوز رکوردی برای نمایش وجود ندارد.</p>;
  return (
    <div className="inventory-table simple-table" role="table">
      <div className="inventory-row inventory-row-head" role="row">{headers.map((header) => <span key={header}>{header}</span>)}</div>
      {rows.map((row, index) => <div className="inventory-row" role="row" key={index}>{row.map((cell, cellIndex) => <span key={cellIndex}>{cell}</span>)}</div>)}
    </div>
  );
}

function SalesView({ onBack }: { onBack: () => void }) {
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [variantsStatus, setVariantsStatus] = useState<"loading" | "ready" | "error">("loading");
  const [variantsError, setVariantsError] = useState("");
  const [items, setItems] = useState<InvoiceDraftItem[]>([]);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [itemVariantId, setItemVariantId] = useState("");
  const [itemQuantity, setItemQuantity] = useState("1");
  const [itemUnitPrice, setItemUnitPrice] = useState("");
  const [itemDiscount, setItemDiscount] = useState("");
  const [itemError, setItemError] = useState("");
  const [payments, setPayments] = useState<PaymentDraft[]>([makeDraftPayment("cash")]);
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [customerName, setCustomerName] = useState("");
  const [saleNote, setSaleNote] = useState("");
  const [saleDate, setSaleDate] = useState(currentJalaliDate);
  const [saleTime, setSaleTime] = useState(currentLocalTime());
  const [submitStatus, setSubmitStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [submitMessage, setSubmitMessage] = useState("");
  const [lastSale, setLastSale] = useState<SaleInvoice | null>(null);
  const [journalDate, setJournalDate] = useState(currentJalaliDate);
  const [journal, setJournal] = useState<DailyJournal | null>(null);
  const [journalStatus, setJournalStatus] = useState<"idle" | "loading" | "error">("loading");
  const [journalError, setJournalError] = useState("");

  function loadSellableProducts() {
    setVariantsError("");
    setVariantsStatus("loading");
    return Promise.all([api.productVariants(), api.inventory()])
      .then(([nextVariants, nextInventory]) => {
        setVariants(nextVariants.filter((variant) => variant.is_active));
        setInventory(nextInventory);
        setVariantsStatus("ready" as const);
      })
      .catch((error) => {
        setVariantsError(error instanceof Error ? error.message : "کالاها و موجودی دریافت نشدند.");
        setVariantsStatus("error" as const);
      });
  }

  function loadJournal(date: string) {
    setJournalStatus("loading");
    setJournalError("");
    return api.dailyJournal(date)
      .then((result) => {
        setJournal(result);
        setJournalStatus("idle" as const);
      })
      .catch((error) => {
        setJournal(null);
        setJournalStatus("error" as const);
        setJournalError(error instanceof Error ? error.message : "دفتر روزانه دریافت نشد.");
      });
  }

  useEffect(() => {
    let isMounted = true;
    Promise.all([api.productVariants(), api.inventory()])
      .then(([nextVariants, nextInventory]) => {
        if (!isMounted) return;
        setVariants(nextVariants.filter((variant) => variant.is_active));
        setInventory(nextInventory);
        setVariantsStatus("ready");
      })
      .catch((error) => {
        if (!isMounted) return;
        setVariantsError(error instanceof Error ? error.message : "کالاها دریافت نشدند.");
        setVariantsStatus("error");
      });
    api.dailyJournal(currentJalaliDate())
      .then((nextJournal) => {
        if (!isMounted) return;
        setJournal(nextJournal);
        setJournalStatus("idle");
      })
      .catch(() => {
        if (!isMounted) return;
        setJournalStatus("error");
        setJournalError("اطلاعات دفتر روزانه دریافت نشد؛ دوباره تلاش کنید.");
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
  const receivedTotal = payments.reduce((sum, payment) => sum + (payment.status === "received" ? payment.amountRial : 0), 0);
  const pendingTotal = payments.reduce((sum, payment) => sum + (payment.status === "pending" ? payment.amountRial : 0), 0);
  const assignedTotal = receivedTotal + pendingTotal;
  const remaining = Math.max(0, total - receivedTotal);
  const estimatedProfit = total - items.reduce((sum, item) => sum + item.estimatedCostRial, 0);

  function resetItemForm() {
    setEditingItemId(null);
    setItemVariantId("");
    setItemQuantity("1");
    setItemUnitPrice("");
    setItemDiscount("");
    setItemError("");
  }

  function selectItemVariant(value: string) {
    setItemVariantId(value);
    const variant = variants.find((item) => item.id === Number(value));
    setItemUnitPrice(variant ? moneyInputValue(variant.retail_price_rial) : "");
    setItemError("");
  }

  function handleAddItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const variantId = Number(itemVariantId);
    const variant = variants.find((item) => item.id === variantId);
    const quantity = normalizeDecimal(itemQuantity);
    const unitPriceRial = normalizeMoney(itemUnitPrice);
    const discountAmountRial = normalizeMoney(itemDiscount);
    const inventoryItem = inventory.find((row) => row.variant_id === variantId);
    const reservedQuantity = items
      .filter((item) => item.variantId === variantId && item.id !== editingItemId)
      .reduce((sum, item) => sum + item.quantity, 0);
    const availableQuantity = Number(inventoryItem?.quantity_on_hand ?? 0) - reservedQuantity;

    if (!variant || quantity <= 0 || unitPriceRial <= 0) {
      setItemError("کالا، مقدار مثبت و قیمت واحد را کامل کنید.");
      return;
    }
    if (discountAmountRial > Math.round(quantity * unitPriceRial)) {
      setItemError("تخفیف ردیف نمی‌تواند از مبلغ همان ردیف بیشتر باشد.");
      return;
    }
    if (quantity > availableQuantity) {
      setItemError(`موجودی کافی نیست؛ حداکثر ${Math.max(0, availableQuantity).toLocaleString("fa-IR")} واحد قابل فروش است.`);
      return;
    }

    const nextItem: InvoiceDraftItem = {
        id: crypto.randomUUID(),
        variantId,
        variantName: variant.name,
        quantity,
        unitPriceRial,
        discountAmountRial,
        estimatedCostRial: Math.round(quantity * Number(inventoryItem?.weighted_average_cost_rial ?? 0)),
      };
    setItems((current) => editingItemId
      ? current.map((item) => (item.id === editingItemId ? { ...nextItem, id: editingItemId } : item))
      : [...current, nextItem]);
    setSubmitStatus("idle");
    setSubmitMessage("");
    resetItemForm();
  }

  function startItemEdit(item: InvoiceDraftItem) {
    setEditingItemId(item.id);
    setItemVariantId(String(item.variantId));
    setItemQuantity(String(item.quantity));
    setItemUnitPrice(moneyInputValue(item.unitPriceRial));
    setItemDiscount(moneyInputValue(item.discountAmountRial));
    setItemError("");
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

    if (!/^\d{4}\/\d{2}\/\d{2}$/.test(toEnglishDigits(saleDate)) || !/^([01]\d|2[0-3]):[0-5]\d$/.test(toEnglishDigits(saleTime))) {
      setSubmitStatus("error");
      setSubmitMessage("تاریخ و ساعت فروش را با قالب درست وارد کنید.");
      return;
    }

    if (invoiceDiscount > subtotal) {
      setSubmitStatus("error");
      setSubmitMessage("تخفیف فاکتور نمی‌تواند از جمع کالاها بیشتر باشد.");
      return;
    }

    const validPayments = payments.filter((payment) => payment.amountRial > 0);
    if (!validPayments.length) {
      setSubmitStatus("error");
      setSubmitMessage("حداقل یک ردیف پرداخت با مبلغ معتبر وارد کنید.");
      return;
    }
    if (assignedTotal > total) {
      setSubmitStatus("error");
      setSubmitMessage("جمع پرداخت‌ها نمی‌تواند از مبلغ فاکتور بیشتر باشد.");
      return;
    }

    const payloadPayments: PaymentCreate[] = validPayments.map((payment) => ({
      method: payment.method,
      amount_rial: payment.amountRial,
      status: payment.status,
      reference_number: payment.referenceNumber.trim() || undefined,
      jalali_date: saleDate,
      local_time: saleTime,
      due_jalali_date: payment.status === "pending" ? payment.dueJalaliDate.trim() || saleDate : undefined,
      note: payment.note.trim() || undefined,
    }));

    try {
      const sale = await api.createSale({
        customer_name: customerName.trim() || undefined,
        jalali_date: saleDate,
        local_time: saleTime,
        discount_amount_rial: invoiceDiscount,
        note: saleNote.trim() || undefined,
        items: items.map((item) => ({
          variant_id: item.variantId,
          quantity: item.quantity,
          unit_price_rial: item.unitPriceRial,
          discount_amount_rial: item.discountAmountRial,
          estimated_cost_rial: item.estimatedCostRial,
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
      setSaleNote("");
      resetItemForm();
      await loadSellableProducts();
      setJournalDate(saleDate);
      await loadJournal(saleDate);
    } catch (error) {
      setSubmitStatus("error");
      setSubmitMessage(error instanceof Error ? error.message : "ثبت فروش انجام نشد.");
    }
  }

  async function handleLoadJournal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadJournal(journalDate);
  }

  return (
    <section className="sales-workspace" aria-label="ثبت فروش روزانه">
      <div className="sales-header sales-hero">
        <div>
          <p className="eyebrow">فروش روزانه</p>
          <h2>فروش را سریع و مطمئن ثبت کنید</h2>
          <p className="sales-guide">ابتدا کالاها را به فاکتور اضافه کنید، سپس پرداخت‌های نقدی یا مدت‌دار را مشخص کنید.</p>
        </div>
        <Button variant="outlined" startIcon={<ArrowBackRounded />} onClick={onBack}>بازگشت به داشبورد</Button>
      </div>

      <div className="sales-grid">
        <Card variant="outlined" className="sale-panel sale-panel-main">
          <div className="sales-section-heading"><div><ReceiptLongRounded /><div><h3>مشخصات و پرداخت فاکتور</h3><p>اطلاعات مشتری اختیاری است.</p></div></div><Chip label={`${items.length.toLocaleString("fa-IR")} ردیف`} color={items.length ? "primary" : "default"} variant="outlined" /></div>
          <form className="sale-meta-grid" onSubmit={handleSubmitSale}>
            <TextField label="نام مشتری (اختیاری)" value={customerName} onChange={(event) => setCustomerName(event.target.value)} disabled={submitStatus === "loading"} />
            <JalaliDateField label="تاریخ شمسی" value={saleDate} onChange={setSaleDate} required />
            <TextField label="ساعت" value={saleTime} onChange={(event) => setSaleTime(toEnglishDigits(event.target.value))} placeholder="14:30" required disabled={submitStatus === "loading"} />
            <TextField label="تخفیف فاکتور (تومان)" inputMode="numeric" value={moneyInputValue(invoiceDiscount)} onChange={(event) => setInvoiceDiscount(normalizeMoney(event.target.value))} disabled={submitStatus === "loading"} />
            <TextField className="sale-note" label="یادداشت فاکتور (اختیاری)" value={saleNote} onChange={(event) => setSaleNote(event.target.value)} multiline minRows={2} disabled={submitStatus === "loading"} />

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
                <span>دریافت قطعی</span>
                <strong className="text-ok">{formatRial(receivedTotal)}</strong>
              </div>
              <div>
                <span>مانده مشتری</span>
                <strong className={remaining > 0 ? "text-danger" : "text-ok"}>{formatRial(remaining)}</strong>
              </div>
              <div><span>سود تخمینی</span><strong className={estimatedProfit < 0 ? "text-danger" : "text-ok"}>{formatRial(estimatedProfit)}</strong></div>
            </div>

            <div className="payment-list">
              <div className="mini-section-header">
                <div><h3>روش‌های پرداخت</h3><span>{formatRial(assignedTotal)} ثبت‌شده</span></div>
                <Button type="button" variant="outlined" startIcon={<AddRounded />} onClick={() => setPayments((current) => [...current, makeDraftPayment("cash", Math.max(0, total - assignedTotal))])}>افزودن پرداخت</Button>
              </div>
              {payments.map((payment) => (
                <div className={`payment-row payment-${payment.status}`} key={payment.id}>
                  <TextField select label="روش" value={payment.method} onChange={(event) => { const method = event.target.value as PaymentMethod; updatePayment(payment.id, { method, status: method === "credit" || method === "cheque" || method === "voucher" ? "pending" : "received" }); }}>
                    {paymentMethods.map((method) => (
                      <MenuItem value={method} key={method}>{paymentLabels[method]}</MenuItem>
                    ))}
                  </TextField>
                  <TextField label="مبلغ (تومان)"
                    inputMode="numeric"
                    value={moneyInputValue(payment.amountRial)}
                    onChange={(event) => updatePayment(payment.id, { amountRial: normalizeMoney(event.target.value) })}
                  />
                  <TextField select label="وضعیت" value={payment.status} onChange={(event) => updatePayment(payment.id, { status: event.target.value as PaymentStatus })}><MenuItem value="received">دریافت‌شده</MenuItem><MenuItem value="pending">در انتظار</MenuItem></TextField>
                  <TextField label="شماره پیگیری (اختیاری)" value={payment.referenceNumber} onChange={(event) => updatePayment(payment.id, { referenceNumber: event.target.value })} />
                  {payment.status === "pending" ? <JalaliDateField label="سررسید" value={payment.dueJalaliDate || saleDate} onChange={(dueJalaliDate) => updatePayment(payment.id, { dueJalaliDate })} /> : <div className="payment-status"><Chip color="success" label="به دریافتی‌ها افزوده می‌شود" size="small" /></div>}
                  <Button type="button" color="error" startIcon={<DeleteOutlineRounded />} aria-label="حذف پرداخت" onClick={() => setPayments((current) => current.filter((item) => item.id !== payment.id))}>حذف</Button>
                </div>
              ))}
              {payments.length === 0 ? <Alert severity="warning">برای ثبت فاکتور، حداقل یک روش پرداخت اضافه کنید.</Alert> : null}
            </div>

            {submitMessage ? (
              <Alert className="sale-message" severity={submitStatus === "success" ? "success" : "error"} role="status">{submitMessage}</Alert>
            ) : null}

            <Button type="submit" variant="contained" size="large" className="submit-sale-button" startIcon={submitStatus === "loading" ? <CircularProgress size={20} color="inherit" /> : <PointOfSaleRounded />} disabled={submitStatus === "loading" || variantsStatus !== "ready"}>{submitStatus === "loading" ? "در حال ثبت فروش…" : "ثبت نهایی فروش"}</Button>
          </form>
        </Card>

        <Card variant="outlined" component="aside" className="sale-panel sale-items-panel">
          <div className="mini-section-header">
            <div><h3>{editingItemId ? "ویرایش ردیف" : "افزودن کالا"}</h3><span>{variants.length.toLocaleString("fa-IR")} کالای فعال</span></div>
            {editingItemId ? <Chip label="حالت ویرایش" color="warning" size="small" /> : null}
          </div>

          {variantsStatus === "loading" ? <div className="record-state"><CircularProgress size={28} /><strong>در حال دریافت کالا و موجودی…</strong></div> : null}
          {variantsStatus === "error" ? <Alert severity="error" action={<Button color="inherit" startIcon={<RefreshRounded />} onClick={() => void loadSellableProducts()}>تلاش دوباره</Button>}>{variantsError}</Alert> : null}
          {variantsStatus === "ready" && variants.length === 0 ? <div className="record-state sale-empty"><Inventory2Rounded /><strong>کالای فعالی برای فروش ندارید</strong><span>ابتدا کالا و موجودی آن را ثبت کنید.</span></div> : null}

          {variantsStatus === "ready" && variants.length > 0 ? (
            <form className="add-item-form" onSubmit={handleAddItem}>
              <TextField select label="کالا" value={itemVariantId} onChange={(event) => selectItemVariant(event.target.value)} required>
                  <MenuItem value="">انتخاب کالا</MenuItem>
                  {variants.map((variant) => (
                    <MenuItem value={variant.id} key={variant.id}>{variant.name} — موجودی {Number(inventory.find((row) => row.variant_id === variant.id)?.quantity_on_hand ?? 0).toLocaleString("fa-IR")}</MenuItem>
                  ))}
              </TextField>
              <div className="compact-fields">
                <TextField label="مقدار" value={itemQuantity} onChange={(event) => setItemQuantity(event.target.value)} inputMode="decimal" required />
                <TextField label="قیمت واحد (تومان)" value={itemUnitPrice} onChange={(event) => setItemUnitPrice(event.target.value)} inputMode="numeric" required />
              </div>
              <TextField label="تخفیف ردیف (تومان)" value={itemDiscount} onChange={(event) => setItemDiscount(event.target.value)} inputMode="numeric" />
              {itemError ? <Alert severity="error">{itemError}</Alert> : null}
              <div className="sale-item-form-actions"><Button type="submit" variant="contained" startIcon={editingItemId ? <EditRounded /> : <AddRounded />}>{editingItemId ? "ذخیره تغییرات" : "افزودن به فاکتور"}</Button>{editingItemId ? <Button type="button" onClick={resetItemForm}>انصراف</Button> : null}</div>
            </form>
          ) : null}

          <div className="invoice-items">
            <div className="mini-section-header">
              <h3>اقلام فاکتور</h3>
              <span>{items.length.toLocaleString("fa-IR")} ردیف</span>
            </div>
            {items.length === 0 ? (
              <div className="record-state sale-empty"><ShoppingCartCheckoutRounded /><strong>فاکتور هنوز خالی است</strong><span>یک کالا را از فرم بالا اضافه کنید.</span></div>
            ) : (
              items.map((item) => {
                const lineTotal = Math.max(0, Math.round(item.quantity * item.unitPriceRial) - item.discountAmountRial);
                return (
                  <div className="invoice-item" key={item.id}>
                    <div className="invoice-item-main">
                      <strong>{item.variantName}</strong>
                      <span>
                        {item.quantity.toLocaleString("fa-IR")} × {formatRial(item.unitPriceRial)}{item.discountAmountRial ? ` • تخفیف ${formatRial(item.discountAmountRial)}` : ""}
                      </span>
                    </div>
                    <div className="invoice-item-end">
                      <strong>{formatRial(lineTotal)}</strong>
                      <div><Button size="small" startIcon={<EditRounded />} onClick={() => startItemEdit(item)}>ویرایش</Button><Button size="small" color="error" startIcon={<DeleteOutlineRounded />} onClick={() => { setItems((current) => current.filter((draft) => draft.id !== item.id)); if (editingItemId === item.id) resetItemForm(); }}>حذف</Button></div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>
      </div>

      <Card variant="outlined" component="section" className="journal-panel">
        <form className="journal-form" onSubmit={handleLoadJournal}>
          <div>
            <p className="eyebrow">دفتر روزانه</p>
            <h2>خلاصه فروش و وصول یک روز</h2>
          </div>
          <div className="journal-filter"><JalaliDateField label="تاریخ گزارش" value={journalDate} onChange={setJournalDate} required /><Button type="submit" variant="outlined" startIcon={journalStatus === "loading" ? <CircularProgress size={18} /> : <RefreshRounded />} disabled={journalStatus === "loading"}>{journalStatus === "loading" ? "در حال دریافت…" : "نمایش گزارش"}</Button></div>
        </form>

        {journalStatus === "loading" ? <LinearProgress aria-label="در حال دریافت دفتر روزانه" /> : null}
        {journalStatus === "error" ? <Alert severity="error" action={<Button color="inherit" onClick={() => void loadJournal(journalDate)}>تلاش دوباره</Button>}>{journalError}</Alert> : null}
        {lastSale ? <Alert severity="success">آخرین فاکتور ثبت‌شده: {lastSale.invoice_number ?? lastSale.id} • سود تخمینی {formatRial(lastSale.items.reduce((sum, item) => sum + (item.estimated_profit_rial ?? 0), 0) - lastSale.discount_amount_rial)}</Alert> : null}
        {journal && journalStatus !== "loading" && journal.invoice_count === 0 ? <div className="record-state journal-empty"><ReceiptLongRounded /><strong>برای این تاریخ فروشی ثبت نشده است</strong><span>تاریخ دیگری انتخاب کنید یا اولین فروش این روز را ثبت کنید.</span></div> : null}
        {journal && journal.invoice_count > 0 ? (
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
            <div><span>سود تخمینی</span><strong>{formatRial(journal.estimated_profit_rial)}</strong></div>
          </div>
        ) : null}

        {journal && journal.invoice_count > 0 && journal.payments.length ? (
          <div className="journal-breakdown">
            {journal.payments.map((payment) => (
              <div key={payment.method}>
                <strong>{paymentLabels[payment.method]}</strong>
                <span className="text-ok">دریافت‌شده: {formatRial(payment.received_rial)}</span>
                <span className={payment.pending_rial ? "text-danger" : ""}>در انتظار: {formatRial(payment.pending_rial)}</span>
              </div>
            ))}
          </div>
        ) : null}
      </Card>
    </section>
  );
}

export default AdminApp;
