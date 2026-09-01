import { useEffect, useMemo, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { Alert, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
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
import Storefront from "./Storefront";
import {
  api,
  type DailyJournal,
  type CashflowReport,
  type Category,
  type Cheque,
  type CustomerDebtsReport,
  type InventoryItem,
  type InventoryReport,
  type LedgerEntry,
  type OnlineChannel,
  type OnlineOrder,
  type PaymentCreate,
  type PaymentMethod,
  type PaymentStatus,
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
const DEFAULT_JALALI_DATE = "1405/06/02";

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

function splitJalaliDate(value: string) {
  const [year = "1405", month = "06", day = "02"] = toEnglishDigits(value).split("/");
  return {
    year: Number(year) || 1405,
    month: Math.min(12, Math.max(1, Number(month) || 6)),
    day: Math.min(31, Math.max(1, Number(day) || 2)),
  };
}

function buildJalaliDate(year: number, month: number, day: number) {
  return `${year}/${String(month).padStart(2, "0")}/${String(day).padStart(2, "0")}`;
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
  const years = Array.from({ length: 5 }, (_, index) => 1403 + index);

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

function App() {
  const [surface, setSurface] = useState<"storefront" | "admin">(() =>
    window.location.pathname.startsWith("/admin") ? "admin" : "storefront",
  );

  useEffect(() => {
    const handlePopState = () => setSurface(window.location.pathname.startsWith("/admin") ? "admin" : "storefront");
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigate(path: "/" | "/admin") {
    window.history.pushState({}, "", path);
    setSurface(path === "/admin" ? "admin" : "storefront");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return surface === "admin" ? <AdminApp onOpenStore={() => navigate("/")} /> : <Storefront onOpenAdmin={() => navigate("/admin")} />;
}

function AdminApp({ onOpenStore }: { onOpenStore: () => void }) {
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
        <nav className="sidebar-nav">
          <span className="sidebar-section-label">مدیریت روزانه</span>
          <button type="button" className={`sidebar-link ${view === "dashboard" ? "active" : ""}`} onClick={() => setView("dashboard")}>
            <DashboardRounded />
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
                onClick={() => setView(target)}
                key={card.key}
              >
                <Icon aria-hidden="true" />
                {card.title}
              </button>
            );
          })}
        </nav>
      </aside>
      <div className="app-main">
      <header className="topbar">
        <div>
          <p className="eyebrow">{viewMeta[view].eyebrow}</p>
          <h1>{viewMeta[view].title}</h1>
          <span className="topbar-user">سلام {displayName}</span>
        </div>
        <div className="topbar-actions">
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

      {view === "sales" ? <SalesView onBack={() => setView("dashboard")} /> : null}
      {view === "purchase" ? <PurchaseView onBack={() => setView("dashboard")} onOpenInventory={() => setView("inventory")} /> : null}
      {view === "inventory" ? <InventoryView onBack={() => setView("dashboard")} /> : null}
      {view === "products" ? <ProductsView onBack={() => setView("dashboard")} /> : null}
      {view === "ledger" ? <LedgerView onBack={() => setView("dashboard")} /> : null}
      {view === "cheques" ? <ChequesView onBack={() => setView("dashboard")} /> : null}
      {view === "reports" ? <ReportsView onBack={() => setView("dashboard")} /> : null}
      {view === "online" ? <OnlineView onBack={() => setView("dashboard")} /> : null}
      {view === "dashboard" ? (
        <DashboardView
          onOpenSales={() => setView("sales")}
          onOpenPurchase={() => setView("purchase")}
          onOpenInventory={() => setView("inventory")}
          onOpenProducts={() => setView("products")}
          onOpenLedger={() => setView("ledger")}
          onOpenCheques={() => setView("cheques")}
          onOpenReports={() => setView("reports")}
          onOpenOnline={() => setView("online")}
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

      <Box component="section" className="dashboard-kpis" aria-label="وضعیت امروز">
        <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">فروش امروز</Typography><PointOfSaleRounded color="primary" /></Stack><Typography variant="h5">۱۲٬۴۵۰٬۰۰۰ تومان</Typography><Chip size="small" label="۱۲ فاکتور" color="primary" variant="outlined" /></CardContent></Card>
        <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">دریافت واقعی</Typography><ReceiptLongRounded color="info" /></Stack><Typography variant="h5">۱۰٬۸۲۰٬۰۰۰ تومان</Typography><LinearProgress variant="determinate" value={87} sx={{ mt: 1.5 }} /></CardContent></Card>
        <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">هشدار موجودی</Typography><Inventory2Rounded color="warning" /></Stack><Typography variant="h5">۳ کالا</Typography><Button size="small" onClick={onOpenInventory}>بررسی موجودی</Button></CardContent></Card>
        <Card><CardContent><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography color="text.secondary">سررسید نزدیک</Typography><PaymentsRounded color="secondary" /></Stack><Typography variant="h5">۲ چک</Typography><Button size="small" onClick={onOpenCheques}>مشاهده چک‌ها</Button></CardContent></Card>
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
  const [purchaseDate, setPurchaseDate] = useState(DEFAULT_JALALI_DATE);
  const [purchaseTime, setPurchaseTime] = useState(currentLocalTime());
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [extraCost, setExtraCost] = useState(0);
  const [paidAmount, setPaidAmount] = useState(0);
  const [note, setNote] = useState("");
  const [submitStatus, setSubmitStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [submitMessage, setSubmitMessage] = useState("");
  const [lastPurchase, setLastPurchase] = useState<PurchaseInvoice | null>(null);

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
    return items.reduce((sum, item) => sum + Math.round(item.quantity * item.unitCostRial) + item.extraCostRial, 0);
  }, [items]);
  const total = Math.max(0, subtotal + extraCost - invoiceDiscount);
  const dueTotal = Math.max(0, total - paidAmount);

  function handleAddPurchaseItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const variantId = Number(form.get("variantId"));
    const variant = variants.find((item) => item.id === variantId);
    const quantity = normalizeDecimal(form.get("quantity"));
    const unitCostRial = normalizeMoney(form.get("unitCostRial"));
    const extraCostRial = normalizeMoney(form.get("itemExtraCost"));

    if (!variant || quantity <= 0 || unitCostRial <= 0) {
      setSubmitStatus("error");
      setSubmitMessage("برای افزودن ردیف خرید، کالا، مقدار و قیمت خرید را کامل کنید.");
      return;
    }

    setItems((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        variantId,
        variantName: variant.name,
        quantity,
        unitCostRial,
        extraCostRial,
      },
    ]);
    setSubmitStatus("idle");
    setSubmitMessage("");
    event.currentTarget.reset();
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
    } catch (error) {
      setSubmitStatus("error");
      setSubmitMessage(error instanceof Error ? error.message : "ثبت خرید انجام نشد.");
    }
  }

  return (
    <section className="sales-workspace" aria-label="ثبت خرید">
      <div className="sales-header">
        <div>
          <p className="eyebrow">خرید و تأمین کالا</p>
          <h2>ثبت فاکتور خرید و به‌روزرسانی موجودی</h2>
        </div>
        <div className="header-actions">
          <button type="button" className="ghost-button" onClick={onOpenInventory}>
            نمایش انبار
          </button>
          <button type="button" className="ghost-button" onClick={onBack}>
            بازگشت به داشبورد
          </button>
        </div>
      </div>

      <div className="sales-grid">
        <section className="sale-panel sale-panel-main">
          <form className="sale-meta-grid" onSubmit={handleSubmitPurchase}>
            <label>
              نام تأمین‌کننده
              <input value={supplierName} onChange={(event) => setSupplierName(event.target.value)} placeholder="مثلا عمده‌فروش بازار" required />
            </label>
            <JalaliDateField label="تاریخ شمسی" value={purchaseDate} onChange={setPurchaseDate} required />
            <label>
              ساعت
              <input value={purchaseTime} onChange={(event) => setPurchaseTime(event.target.value)} placeholder="14:30" required />
            </label>
            <label>
              پرداخت‌شده
              <input inputMode="numeric" value={moneyInputValue(paidAmount)} onChange={(event) => setPaidAmount(normalizeMoney(event.target.value))} placeholder="۰ تومان" />
            </label>
            <label>
              تخفیف فاکتور
              <input inputMode="numeric" value={moneyInputValue(invoiceDiscount)} onChange={(event) => setInvoiceDiscount(normalizeMoney(event.target.value))} placeholder="۰ تومان" />
            </label>
            <label>
              هزینه اضافه فاکتور
              <input inputMode="numeric" value={moneyInputValue(extraCost)} onChange={(event) => setExtraCost(normalizeMoney(event.target.value))} placeholder="۰ تومان" />
            </label>
            <label className="wide-field">
              توضیح
              <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="اختیاری" />
            </label>

            <div className="invoice-summary" aria-label="جمع فاکتور خرید">
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

            {submitMessage ? (
              <p className={submitStatus === "success" ? "success-message" : "error-message"} role="status">
                {submitMessage}
              </p>
            ) : null}

            <button type="submit" className="primary-button submit-sale-button" disabled={submitStatus === "loading"}>
              {submitStatus === "loading" ? "در حال ثبت..." : "ثبت خرید"}
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
          {variantsStatus === "ready" && variants.length === 0 ? <p className="state-message">هنوز کالایی برای خرید ثبت نشده است.</p> : null}

          {variantsStatus === "ready" && variants.length > 0 ? (
            <form className="add-item-form" onSubmit={handleAddPurchaseItem}>
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
                  قیمت خرید واحد
                  <input name="unitCostRial" inputMode="numeric" placeholder="تومان" required />
                </label>
              </div>
              <label>
                هزینه اضافه ردیف
                <input name="itemExtraCost" inputMode="numeric" placeholder="باربری/کیسه/..." />
              </label>
              <button type="submit" className="soft-button">
                افزودن به خرید
              </button>
            </form>
          ) : null}

          <div className="invoice-items">
            <div className="mini-section-header">
              <h3>اقلام خرید</h3>
              <span>{items.length.toLocaleString("fa-IR")} ردیف</span>
            </div>
            {items.length === 0 ? (
              <p className="state-message">کالایی به فاکتور خرید اضافه نشده است.</p>
            ) : (
              items.map((item) => {
                const lineTotal = Math.round(item.quantity * item.unitCostRial) + item.extraCostRial;
                return (
                  <div className="invoice-item" key={item.id}>
                    <div>
                      <strong>{item.variantName}</strong>
                      <span>
                        {item.quantity.toLocaleString("fa-IR")} × {formatRial(item.unitCostRial)}
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
          {lastPurchase ? <p className="success-message">آخرین خرید ثبت‌شده: {lastPurchase.invoice_number ?? lastPurchase.id}</p> : null}
        </aside>
      </div>
    </section>
  );
}

function InventoryView({ onBack }: { onBack: () => void }) {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;
    setStatus("loading");
    api
      .inventory()
      .then((result) => {
        if (!isMounted) return;
        setItems(result);
        setStatus("ready");
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "موجودی دریافت نشد.");
        setStatus("error");
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const totalValue = items.reduce((sum, item) => sum + Number(item.quantity_on_hand) * item.weighted_average_cost_rial, 0);

  return (
    <section className="sales-workspace" aria-label="انبار">
      <div className="sales-header">
        <div>
          <p className="eyebrow">انبار</p>
          <h2>موجودی و میانگین موزون کالاها</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onBack}>
          بازگشت به داشبورد
        </button>
      </div>

      <section className="inventory-summary">
        <div>
          <span>تعداد ردیف موجودی</span>
          <strong>{items.length.toLocaleString("fa-IR")}</strong>
        </div>
        <div>
          <span>ارزش تقریبی موجودی</span>
          <strong>{formatRial(totalValue)}</strong>
        </div>
      </section>

      <section className="sale-panel">
        {status === "loading" ? <p className="state-message">در حال دریافت موجودی...</p> : null}
        {status === "error" ? <p className="error-message">{error}</p> : null}
        {status === "ready" && items.length === 0 ? <p className="state-message">هنوز موجودی برای کالاها ثبت نشده است.</p> : null}
        {status === "ready" && items.length > 0 ? (
          <div className="inventory-table" role="table" aria-label="لیست موجودی">
            <div className="inventory-row inventory-row-head" role="row">
              <span role="columnheader">کالا</span>
              <span role="columnheader">موجودی</span>
              <span role="columnheader">میانگین موزون</span>
              <span role="columnheader">نقطه سفارش</span>
            </div>
            {items.map((item) => (
              <div className="inventory-row" role="row" key={item.id}>
                <strong role="cell">{item.variant_name}</strong>
                <span role="cell">{formatDecimal(item.quantity_on_hand)}</span>
                <span role="cell">{formatRial(item.weighted_average_cost_rial)}</span>
                <span role="cell">{item.reorder_level == null ? "ثبت نشده" : formatDecimal(item.reorder_level)}</span>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </section>
  );
}

function ProductsView({ onBack }: { onBack: () => void }) {
  const [units, setUnits] = useState<Unit[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [message, setMessage] = useState("");
  const [categoryStatus, setCategoryStatus] = useState<"loading" | "ready" | "error">("loading");
  const [categoryNotice, setCategoryNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [categoryName, setCategoryName] = useState("");
  const [categoryParentId, setCategoryParentId] = useState("");
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null);
  const [categorySaving, setCategorySaving] = useState(false);
  const [deactivatingCategoryId, setDeactivatingCategoryId] = useState<number | null>(null);
  const [pendingDeactivateCategory, setPendingDeactivateCategory] = useState<Category | null>(null);

  const load = () => {
    setCategoryStatus("loading");
    setCategoryNotice(null);
    return Promise.all([api.units(), api.categories(), api.products(), api.productVariants()])
      .then(([nextUnits, nextCategories, nextProducts, nextVariants]) => {
        setUnits(nextUnits);
        setCategories(nextCategories);
        setProducts(nextProducts);
        setVariants(nextVariants);
        setCategoryStatus("ready");
      })
      .catch((error) => {
        const text = error instanceof Error ? error.message : "دریافت اطلاعات کالا انجام نشد.";
        setCategoryNotice({ type: "error", text });
        setCategoryStatus("error");
      });
  };

  useEffect(() => {
    void load();
  }, []);

  async function submitUnit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createUnit({ name: String(form.get("name") ?? ""), symbol: String(form.get("symbol") ?? "") });
    event.currentTarget.reset();
    setMessage("واحد با موفقیت ثبت شد.");
    load();
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

  async function submitProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const categoryId = Number(form.get("categoryId"));
    await api.createProduct({
      name: String(form.get("name") ?? ""),
      description: String(form.get("description") ?? ""),
      category_id: categoryId || null,
    });
    event.currentTarget.reset();
    setMessage("کالا ثبت شد.");
    load();
  }

  async function submitVariant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createProductVariant({
      product_id: Number(form.get("productId")),
      unit_id: Number(form.get("unitId")),
      name: String(form.get("name") ?? ""),
      sku: String(form.get("sku") ?? ""),
      retail_price_rial: normalizeMoney(form.get("retail")),
      wholesale_price_rial: normalizeMoney(form.get("wholesale")) || null,
      min_wholesale_quantity: normalizeDecimal(form.get("minWholesale")) || null,
    });
    event.currentTarget.reset();
    setMessage("گونه و قیمت کالا ثبت شد.");
    load();
  }

  async function submitPrice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createPrice({
      variant_id: Number(form.get("variantId")),
      price_type: String(form.get("priceType")) as "retail" | "wholesale" | "online",
      amount_rial: normalizeMoney(form.get("amount")),
      jalali_date: String(form.get("date") ?? DEFAULT_JALALI_DATE),
      local_time: currentLocalTime(),
    });
    event.currentTarget.reset();
    setMessage("قیمت جدید ثبت شد.");
    load();
  }

  return (
    <CrudWorkspace title="کالاها و قیمت‌ها" eyebrow="مدیریت کاتالوگ" onBack={onBack}>
      {message ? <p className="success-message">{message}</p> : null}
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
            {categoryStatus === "error" ? <div className="category-state category-state-error"><span>دریافت دسته‌ها انجام نشد.</span><Button variant="outlined" onClick={() => load()}>تلاش دوباره</Button></div> : null}
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
      <div className="management-grid">
        <form className="sale-panel compact-panel" onSubmit={submitUnit}>
          <h3>واحد</h3>
          <input name="name" placeholder="نام واحد، مثلا کیلوگرم" required />
          <input name="symbol" placeholder="نماد، مثلا kg" required />
          <button className="soft-button">ثبت واحد</button>
        </form>
        <form className="sale-panel compact-panel" onSubmit={submitProduct}>
          <h3>کالا</h3>
          <input name="name" placeholder="نام کالا" required />
          <select name="categoryId">
            <option value="">بدون دسته</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <input name="description" placeholder="توضیح کوتاه" />
          <button className="soft-button">ثبت کالا</button>
        </form>
        <form className="sale-panel compact-panel" onSubmit={submitVariant}>
          <h3>گونه و قیمت پایه</h3>
          <select name="productId" required>
            <option value="">انتخاب کالا</option>
            {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
          </select>
          <select name="unitId" required>
            <option value="">انتخاب واحد</option>
            {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
          </select>
          <input name="name" placeholder="مثلا عدس درجه یک کیلویی" required />
          <input name="sku" placeholder="کد کالا" />
          <input name="retail" inputMode="numeric" placeholder="قیمت خرده‌فروشی تومان" required />
          <input name="wholesale" inputMode="numeric" placeholder="قیمت عمده تومان" />
          <input name="minWholesale" inputMode="decimal" placeholder="حداقل عمده" />
          <button className="soft-button">ثبت گونه</button>
        </form>
        <form className="sale-panel compact-panel" onSubmit={submitPrice}>
          <h3>به‌روزرسانی قیمت</h3>
          <select name="variantId" required>
            <option value="">انتخاب گونه</option>
            {variants.map((variant) => <option key={variant.id} value={variant.id}>{variant.name}</option>)}
          </select>
          <select name="priceType">
            <option value="retail">خرده</option>
            <option value="wholesale">عمده</option>
            <option value="online">آنلاین</option>
          </select>
          <input name="amount" inputMode="numeric" placeholder="مبلغ تومان" required />
          <input name="date" defaultValue={DEFAULT_JALALI_DATE} />
          <button className="soft-button">ثبت قیمت</button>
        </form>
      </div>
      <SimpleTable headers={["کالا", "کد", "قیمت خرده", "قیمت عمده"]} rows={variants.map((v) => [v.name, v.sku || "-", formatRial(v.retail_price_rial), v.wholesale_price_rial ? formatRial(v.wholesale_price_rial) : "-"])} />
    </CrudWorkspace>
  );
}

function LedgerView({ onBack }: { onBack: () => void }) {
  const [people, setPeople] = useState<Person[]>([]);
  const [selectedId, setSelectedId] = useState(0);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [message, setMessage] = useState("");
  const selected = people.find((person) => person.id === selectedId);
  const balance = entries.reduce((sum, entry) => sum + (entry.entry_type === "debit" ? entry.remaining_rial : -entry.remaining_rial), 0);

  const loadPeople = () => api.persons().then(setPeople).catch((error) => setMessage(error instanceof Error ? error.message : "اشخاص دریافت نشدند."));
  useEffect(() => {
    loadPeople();
  }, []);
  useEffect(() => {
    if (selectedId) api.personLedger(selectedId).then(setEntries).catch((error) => setMessage(error instanceof Error ? error.message : "دفتر حساب دریافت نشد."));
  }, [selectedId]);

  async function submitPerson(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createPerson({ name: String(form.get("name") ?? ""), phone: String(form.get("phone") ?? ""), person_type: String(form.get("type")) as Person["person_type"] });
    event.currentTarget.reset();
    setMessage("شخص ثبت شد.");
    loadPeople();
  }

  async function submitEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createManualEntry({
      person_id: selectedId,
      entry_type: String(form.get("entryType")) as "debit" | "credit",
      amount_rial: normalizeMoney(form.get("amount")),
      jalali_date: String(form.get("date") ?? DEFAULT_JALALI_DATE),
      local_time: currentLocalTime(),
      description: String(form.get("description") ?? ""),
    });
    event.currentTarget.reset();
    setMessage("سند دستی ثبت شد.");
    api.personLedger(selectedId).then(setEntries);
  }

  async function submitSettlement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createSettlement({ person_id: selectedId, amount_rial: normalizeMoney(form.get("amount")), jalali_date: String(form.get("date") ?? DEFAULT_JALALI_DATE), local_time: currentLocalTime(), note: String(form.get("note") ?? "") });
    event.currentTarget.reset();
    setMessage("تسویه ثبت شد.");
    api.personLedger(selectedId).then(setEntries);
  }

  return (
    <CrudWorkspace title="دفتر حساب اشخاص" eyebrow="مشتری و تامین‌کننده" onBack={onBack}>
      {message ? <p className="success-message">{message}</p> : null}
      <div className="management-grid">
        <form className="sale-panel compact-panel" onSubmit={submitPerson}>
          <h3>شخص جدید</h3>
          <input name="name" placeholder="نام شخص" required />
          <input name="phone" placeholder="تلفن" />
          <select name="type"><option value="customer">مشتری</option><option value="supplier">تامین‌کننده</option><option value="both">هر دو</option></select>
          <button className="soft-button">ثبت شخص</button>
        </form>
        <section className="sale-panel compact-panel">
          <h3>انتخاب حساب</h3>
          <select value={selectedId} onChange={(event) => setSelectedId(Number(event.target.value))}>
            <option value={0}>انتخاب شخص</option>
            {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
          </select>
          <strong>{selected ? `مانده: ${formatRial(Math.abs(balance))}` : "حسابی انتخاب نشده"}</strong>
        </section>
        <form className="sale-panel compact-panel" onSubmit={submitEntry}>
          <h3>سند دستی</h3>
          <select name="entryType"><option value="debit">بدهکار</option><option value="credit">بستانکار</option></select>
          <input name="amount" inputMode="numeric" placeholder="مبلغ تومان" required />
          <input name="date" defaultValue={DEFAULT_JALALI_DATE} />
          <input name="description" placeholder="شرح" />
          <button className="soft-button" disabled={!selectedId}>ثبت سند</button>
        </form>
        <form className="sale-panel compact-panel" onSubmit={submitSettlement}>
          <h3>تسویه</h3>
          <input name="amount" inputMode="numeric" placeholder="مبلغ تومان" required />
          <input name="date" defaultValue={DEFAULT_JALALI_DATE} />
          <input name="note" placeholder="یادداشت" />
          <button className="soft-button" disabled={!selectedId}>ثبت تسویه</button>
        </form>
      </div>
      <SimpleTable headers={["تاریخ", "نوع", "مبلغ", "مانده", "شرح"]} rows={entries.map((entry) => [entry.jalali_date, entry.entry_type === "debit" ? "بدهکار" : "بستانکار", formatRial(entry.amount_rial), formatRial(entry.remaining_rial), entry.description || entry.source_type])} />
    </CrudWorkspace>
  );
}

function ChequesView({ onBack }: { onBack: () => void }) {
  const [people, setPeople] = useState<Person[]>([]);
  const [cheques, setCheques] = useState<Cheque[]>([]);
  const [message, setMessage] = useState("");
  const load = () => Promise.all([api.persons(), api.cheques()]).then(([nextPeople, nextCheques]) => { setPeople(nextPeople); setCheques(nextCheques); });
  useEffect(() => { load().catch((error) => setMessage(error instanceof Error ? error.message : "چک‌ها دریافت نشدند.")); }, []);

  async function submitCheque(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const personId = Number(form.get("personId"));
    await api.createCheque({
      cheque_type: String(form.get("chequeType")) as "received" | "paid",
      person_id: personId || null,
      bank_name: String(form.get("bank") ?? ""),
      cheque_number: String(form.get("number") ?? ""),
      amount_rial: normalizeMoney(form.get("amount")),
      issue_jalali_date: String(form.get("issueDate") ?? DEFAULT_JALALI_DATE),
      due_jalali_date: String(form.get("dueDate") ?? DEFAULT_JALALI_DATE),
      local_time: currentLocalTime(),
      note: String(form.get("note") ?? ""),
    });
    event.currentTarget.reset();
    setMessage("چک ثبت شد.");
    load();
  }

  async function markCheque(id: number, eventType: "cleared" | "bounced" | "canceled") {
    await api.createChequeEvent(id, { event_type: eventType, jalali_date: DEFAULT_JALALI_DATE, local_time: currentLocalTime() });
    setMessage("وضعیت چک ثبت شد.");
    load();
  }

  return (
    <CrudWorkspace title="دفتر چک‌ها و سررسیدها" eyebrow="دریافتی و پرداختی" onBack={onBack}>
      {message ? <p className="success-message">{message}</p> : null}
      <form className="sale-panel cheque-form" onSubmit={submitCheque}>
        <select name="chequeType"><option value="received">دریافتی</option><option value="paid">پرداختی</option></select>
        <select name="personId"><option value="">بدون شخص</option>{people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select>
        <input name="bank" placeholder="بانک" required />
        <input name="number" placeholder="شماره چک" required />
        <input name="amount" inputMode="numeric" placeholder="مبلغ تومان" required />
        <input name="issueDate" defaultValue={DEFAULT_JALALI_DATE} />
        <input name="dueDate" defaultValue={DEFAULT_JALALI_DATE} />
        <input name="note" placeholder="یادداشت" />
        <button className="soft-button">ثبت چک</button>
      </form>
      <div className="table-list">
        {cheques.map((cheque) => (
          <article className="table-card" key={cheque.id}>
            <div><strong>{cheque.bank_name} - {cheque.cheque_number}</strong><span>{cheque.cheque_type === "received" ? "دریافتی" : "پرداختی"} | سررسید {cheque.due_jalali_date}</span></div>
            <strong>{formatRial(cheque.amount_rial)}</strong>
            <span className="badge">{cheque.status}</span>
            <button className="link-button" onClick={() => markCheque(cheque.id, "cleared")}>وصول/پاس</button>
            <button className="link-button" onClick={() => markCheque(cheque.id, "bounced")}>برگشت</button>
          </article>
        ))}
      </div>
    </CrudWorkspace>
  );
}

function ReportsView({ onBack }: { onBack: () => void }) {
  const [from, setFrom] = useState(DEFAULT_JALALI_DATE);
  const [to, setTo] = useState(DEFAULT_JALALI_DATE);
  const [sales, setSales] = useState<SalesSummaryReport | null>(null);
  const [profit, setProfit] = useState<ProfitLossReport | null>(null);
  const [inventory, setInventory] = useState<InventoryReport | null>(null);
  const [cashflow, setCashflow] = useState<CashflowReport | null>(null);
  const [debts, setDebts] = useState<CustomerDebtsReport | null>(null);
  const [message, setMessage] = useState("");

  async function loadReports(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    try {
      const [nextSales, nextProfit, nextInventory, nextCashflow, nextDebts] = await Promise.all([api.salesSummary(from, to), api.profitLoss(from, to), api.inventoryReport(), api.cashflow(to), api.customerDebts()]);
      setSales(nextSales); setProfit(nextProfit); setInventory(nextInventory); setCashflow(nextCashflow); setDebts(nextDebts);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "گزارش‌ها دریافت نشدند.");
    }
  }
  useEffect(() => { loadReports(); }, []);

  return (
    <CrudWorkspace title="گزارش‌ها" eyebrow="فروش، سود، انبار و جریان نقد" onBack={onBack}>
      <form className="journal-form sale-panel" onSubmit={loadReports}>
        <JalaliDateField label="از تاریخ" value={from} onChange={setFrom} required />
        <JalaliDateField label="تا تاریخ" value={to} onChange={setTo} required />
        <button className="ghost-button">به‌روزرسانی</button>
      </form>
      {message ? <p className="error-message">{message}</p> : null}
      <div className="metric-grid">
        <Metric label="تعداد فاکتور" value={sales?.invoice_count.toLocaleString("fa-IR") ?? "-"} />
        <Metric label="فروش ثبت‌شده" value={sales ? formatRial(sales.registered_sales_rial) : "-"} />
        <Metric label="دریافت‌شده" value={sales ? formatRial(sales.received_rial) : "-"} />
        <Metric label="مانده فروش" value={sales ? formatRial(sales.pending_rial) : "-"} />
        <Metric label="سود ناخالص" value={profit ? formatRial(profit.gross_profit_rial) : "-"} />
        <Metric label="حاشیه سود" value={profit ? `${profit.gross_margin_percent.toLocaleString("fa-IR")}٪` : "-"} />
        <Metric label="ارزش انبار" value={inventory ? formatRial(inventory.total_value_rial) : "-"} />
        <Metric label="جریان نقد مورد انتظار" value={cashflow ? formatRial(cashflow.net_expected_rial) : "-"} />
        <Metric label="بدهی مشتریان" value={debts ? formatRial(debts.total_remaining_rial) : "-"} />
      </div>
    </CrudWorkspace>
  );
}

function OnlineView({ onBack }: { onBack: () => void }) {
  const [channels, setChannels] = useState<OnlineChannel[]>([]);
  const [orders, setOrders] = useState<OnlineOrder[]>([]);
  const [message, setMessage] = useState("");
  const load = () => Promise.all([api.onlineChannels(), api.onlineOrders()]).then(([nextChannels, nextOrders]) => { setChannels(nextChannels); setOrders(nextOrders); });
  useEffect(() => { load().catch((error) => setMessage(error instanceof Error ? error.message : "اطلاعات آنلاین دریافت نشد.")); }, []);

  async function submitChannel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createOnlineChannel({ name: String(form.get("name") ?? ""), token: String(form.get("token") ?? ""), note: String(form.get("note") ?? "") });
    event.currentTarget.reset();
    setMessage("کانال آنلاین ثبت شد.");
    load();
  }

  return (
    <CrudWorkspace title="اتصال آنلاین" eyebrow="کانال‌ها و سفارش‌های سایت" onBack={onBack}>
      {message ? <p className="success-message">{message}</p> : null}
      <form className="sale-panel cheque-form" onSubmit={submitChannel}>
        <input name="name" placeholder="نام کانال، مثلا سایت فروشگاه" required />
        <input name="token" placeholder="توکن اتصال" required />
        <input name="note" placeholder="یادداشت" />
        <button className="soft-button">ثبت کانال</button>
      </form>
      <div className="management-grid">
        <section className="sale-panel compact-panel"><h3>کانال‌ها</h3>{channels.map((channel) => <p key={channel.id}>{channel.name} <span className="badge">{channel.is_active ? "فعال" : "غیرفعال"}</span></p>)}</section>
        <section className="sale-panel compact-panel"><h3>سفارش‌های آنلاین</h3>{orders.length ? orders.map((order) => <p key={order.id}>{order.customer_name} - {formatRial(order.total_rial)} - {order.status}</p>) : <p className="state-message">هنوز سفارشی ثبت نشده است.</p>}</section>
      </div>
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
            <JalaliDateField label="تاریخ شمسی" value={saleDate} onChange={setSaleDate} required />
            <label>
              ساعت
              <input value={saleTime} onChange={(event) => setSaleTime(event.target.value)} placeholder="14:30" required />
            </label>
            <label>
              تخفیف فاکتور
              <input inputMode="numeric" value={moneyInputValue(invoiceDiscount)} onChange={(event) => setInvoiceDiscount(normalizeMoney(event.target.value))} placeholder="۰ تومان" />
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
                    value={moneyInputValue(payment.amountRial)}
                    onChange={(event) => updatePayment(payment.id, { amountRial: normalizeMoney(event.target.value) })}
                    placeholder="مبلغ تومان"
                  />
                  <select value={payment.status} onChange={(event) => updatePayment(payment.id, { status: event.target.value as PaymentStatus })}>
                    <option value="received">دریافت‌شده</option>
                    <option value="pending">در انتظار</option>
                  </select>
                  <input value={payment.referenceNumber} onChange={(event) => updatePayment(payment.id, { referenceNumber: event.target.value })} placeholder="شماره پیگیری/چک" />
                  <JalaliDateField value={payment.dueJalaliDate || saleDate} onChange={(dueJalaliDate) => updatePayment(payment.id, { dueJalaliDate })} />
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
                  <input name="unitPriceRial" inputMode="numeric" placeholder="تومان" required />
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
          <JalaliDateField value={journalDate} onChange={setJournalDate} required />
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
