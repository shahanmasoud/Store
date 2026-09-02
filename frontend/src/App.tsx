import { useEffect, useMemo, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { Alert, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, InputAdornment, LinearProgress, MenuItem, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";
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
import Storefront from "./Storefront";
import {
  api,
  type DailyJournal,
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
const DEFAULT_JALALI_DATE = "1405/06/02";
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
                    <div className="inventory-transaction-main"><strong>{transaction.variant_name}</strong><span>{transaction.transaction_type === "purchase_in" ? "ورود خرید" : transaction.transaction_type === "cancel_purchase" ? "لغو خرید" : transaction.transaction_type}</span><small>{transaction.note ?? (transaction.purchase_invoice_id ? `فاکتور خرید ${transaction.purchase_invoice_id}` : "گردش انبار")}</small></div>
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
  const [priceDate, setPriceDate] = useState(DEFAULT_JALALI_DATE);
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
