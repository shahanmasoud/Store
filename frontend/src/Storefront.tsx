import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  AppBar,
  Badge,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  InputAdornment,
  LinearProgress,
  Snackbar,
  Stack,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import AccessTimeRounded from "@mui/icons-material/AccessTimeRounded";
import AdminPanelSettingsRounded from "@mui/icons-material/AdminPanelSettingsRounded";
import AddRounded from "@mui/icons-material/AddRounded";
import ArrowBackRounded from "@mui/icons-material/ArrowBackRounded";
import CheckCircleRounded from "@mui/icons-material/CheckCircleRounded";
import ContentCopyRounded from "@mui/icons-material/ContentCopyRounded";
import LoginRounded from "@mui/icons-material/LoginRounded";
import LogoutRounded from "@mui/icons-material/LogoutRounded";
import LocalShippingRounded from "@mui/icons-material/LocalShippingRounded";
import OpenInNewRounded from "@mui/icons-material/OpenInNewRounded";
import RefreshRounded from "@mui/icons-material/RefreshRounded";
import RemoveRounded from "@mui/icons-material/RemoveRounded";
import SearchRounded from "@mui/icons-material/SearchRounded";
import ShoppingBasketRounded from "@mui/icons-material/ShoppingBasketRounded";
import StorefrontRounded from "@mui/icons-material/StorefrontRounded";
import VerifiedRounded from "@mui/icons-material/VerifiedRounded";
import { QRCodeSVG } from "qrcode.react";
import { api, type BaleCustomer, type BaleLoginChallenge } from "./api";
import heroImage from "./assets/storefront-hero.png";

type StorefrontProps = { onOpenAdmin: () => void };
type Product = { id: number; name: string; category: string; price: number; unit: string; badge?: string; position: string };

const categories = ["همه", "حبوبات", "برنج", "غلات", "آجیل و خشکبار"];
const products: Product[] = [
  { id: 1, name: "لوبیا قرمز ممتاز", category: "حبوبات", price: 153500, unit: "کیلوگرم", badge: "پرفروش", position: "8% 78%" },
  { id: 2, name: "نخود کرمانشاه", category: "حبوبات", price: 112000, unit: "کیلوگرم", position: "32% 86%" },
  { id: 3, name: "عدس سبز درجه یک", category: "حبوبات", price: 91000, unit: "کیلوگرم", badge: "تازه", position: "53% 76%" },
  { id: 4, name: "برنج ایرانی خوش‌عطر", category: "برنج", price: 148000, unit: "کیلوگرم", position: "60% 46%" },
  { id: 5, name: "لپه آذرشهر", category: "حبوبات", price: 125000, unit: "کیلوگرم", position: "78% 82%" },
  { id: 6, name: "ماش سبز", category: "غلات", price: 98000, unit: "کیلوگرم", position: "44% 68%" },
];

function formatToman(value: number) {
  return `${value.toLocaleString("fa-IR")} تومان`;
}

type BaleLoginUiState = "idle" | "creating" | "pending" | "approved" | "expired" | "error" | "authenticated";

const CUSTOMER_TOKEN_KEY = "store_customer_token";
const CUSTOMER_INFO_KEY = "store_customer_info";
const BALE_CHALLENGE_KEY = "store_bale_login_challenge";

function readStoredCustomer(): BaleCustomer | null {
  if (!localStorage.getItem(CUSTOMER_TOKEN_KEY)) return null;
  try {
    const value = localStorage.getItem(CUSTOMER_INFO_KEY);
    return value ? (JSON.parse(value) as BaleCustomer) : { id: "customer", provider: "bale" };
  } catch {
    return { id: "customer", provider: "bale" };
  }
}

function formatCountdown(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes.toLocaleString("fa-IR")}:${remainder.toLocaleString("fa-IR", { minimumIntegerDigits: 2, useGrouping: false })}`;
}

function BaleCustomerLogin({ onToast }: { onToast: (message: string) => void }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [open, setOpen] = useState(false);
  const [customer, setCustomer] = useState<BaleCustomer | null>(() => readStoredCustomer());
  const [state, setState] = useState<BaleLoginUiState>(() => readStoredCustomer() ? "authenticated" : "idle");
  const [challenge, setChallenge] = useState<BaleLoginChallenge | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [secondsLeft, setSecondsLeft] = useState(120);
  const exchangeStarted = useRef(false);
  const pollingFailures = useRef(0);

  const exchangeChallenge = useCallback(async (challengeId: string) => {
    if (exchangeStarted.current) return;
    exchangeStarted.current = true;
    setState("approved");
    try {
      const result = await api.exchangeBaleLoginChallenge(challengeId);
      localStorage.setItem(CUSTOMER_TOKEN_KEY, result.access_token);
      localStorage.setItem(CUSTOMER_INFO_KEY, JSON.stringify(result.customer));
      sessionStorage.removeItem(BALE_CHALLENGE_KEY);
      setCustomer(result.customer);
      setState("authenticated");
      onToast(`خوش آمدید${result.customer.display_name ? `، ${result.customer.display_name}` : ""}`);
      window.setTimeout(() => setOpen(false), 900);
    } catch (error) {
      exchangeStarted.current = false;
      setErrorMessage(error instanceof Error ? error.message : "تکمیل ورود انجام نشد. دوباره تلاش کنید.");
      setState("error");
    } finally {
      const cleanUrl = new URL(window.location.href);
      if (cleanUrl.searchParams.has("bale_login")) {
        cleanUrl.searchParams.delete("bale_login");
        window.history.replaceState({}, "", `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`);
      }
    }
  }, [onToast]);

  useEffect(() => {
    const challengeId = new URLSearchParams(window.location.search).get("bale_login");
    if (!challengeId) return;
    if (customer) {
      const cleanUrl = new URL(window.location.href);
      cleanUrl.searchParams.delete("bale_login");
      window.history.replaceState({}, "", `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`);
      return;
    }
    setOpen(true);
    setState("approved");
    void exchangeChallenge(challengeId);
  }, [customer, exchangeChallenge]);

  useEffect(() => {
    const token = localStorage.getItem(CUSTOMER_TOKEN_KEY);
    if (!token || !customer) return;
    let active = true;
    api.baleCustomerMe(token).then((currentCustomer) => {
      if (!active) return;
      setCustomer(currentCustomer);
      localStorage.setItem(CUSTOMER_INFO_KEY, JSON.stringify(currentCustomer));
    }).catch(() => {
      if (!active) return;
      localStorage.removeItem(CUSTOMER_TOKEN_KEY);
      localStorage.removeItem(CUSTOMER_INFO_KEY);
      setCustomer(null);
      setState("idle");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (customer) return;
    const saved = sessionStorage.getItem(BALE_CHALLENGE_KEY);
    if (!saved) return;
    try {
      const restored = JSON.parse(saved) as BaleLoginChallenge;
      const remaining = Math.ceil((Date.parse(restored.expires_at_utc) - Date.now()) / 1000);
      setChallenge(restored);
      setSecondsLeft(Math.max(0, remaining));
      setState(remaining > 0 ? "pending" : "expired");
      setOpen(true);
    } catch {
      sessionStorage.removeItem(BALE_CHALLENGE_KEY);
    }
  }, [customer]);

  useEffect(() => {
    if (!challenge || state !== "pending") return;
    const updateCountdown = () => {
      const remaining = Math.max(0, Math.ceil((Date.parse(challenge.expires_at_utc) - Date.now()) / 1000));
      setSecondsLeft(remaining);
      if (remaining === 0) {
        setState("expired");
        sessionStorage.removeItem(BALE_CHALLENGE_KEY);
      }
    };
    updateCountdown();
    const timer = window.setInterval(updateCountdown, 1000);
    return () => window.clearInterval(timer);
  }, [challenge, state]);

  useEffect(() => {
    if (!challenge || state !== "pending") return;
    let active = true;
    let timeoutId: number;
    const poll = async () => {
      try {
        const result = await api.baleLoginChallenge(challenge.id);
        if (!active) return;
        pollingFailures.current = 0;
        if (result.status === "approved") {
          void exchangeChallenge(challenge.id);
          return;
        }
        if (result.status === "expired" || result.status === "consumed") {
          setState("expired");
          sessionStorage.removeItem(BALE_CHALLENGE_KEY);
          return;
        }
        timeoutId = window.setTimeout(poll, Math.max(1, result.poll_after_seconds ?? challenge.poll_after_seconds ?? 2) * 1000);
      } catch (error) {
        if (!active) return;
        const remaining = Math.ceil((Date.parse(challenge.expires_at_utc) - Date.now()) / 1000);
        pollingFailures.current += 1;
        if (remaining > 0 && pollingFailures.current < 3) {
          timeoutId = window.setTimeout(poll, Math.max(1, challenge.poll_after_seconds ?? 2) * 1000);
          return;
        }
        setErrorMessage(error instanceof Error ? error.message : "بررسی وضعیت ورود ممکن نشد.");
        setState("error");
      }
    };
    timeoutId = window.setTimeout(poll, Math.max(1, challenge.poll_after_seconds ?? 2) * 1000);
    return () => {
      active = false;
      window.clearTimeout(timeoutId);
    };
  }, [challenge, exchangeChallenge, state]);

  async function startLogin() {
    setOpen(true);
    setState("creating");
    setErrorMessage("");
    setChallenge(null);
    exchangeStarted.current = false;
    pollingFailures.current = 0;
    try {
      const created = await api.createBaleLoginChallenge("/");
      setChallenge(created);
      setSecondsLeft(created.expires_in_seconds);
      setState("pending");
      sessionStorage.setItem(BALE_CHALLENGE_KEY, JSON.stringify(created));
      if (isMobile) window.location.assign(created.bot_url);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "ساخت کد ورود ممکن نشد. دوباره تلاش کنید.");
      setState("error");
    }
  }

  async function copyCode() {
    if (!challenge) return;
    try {
      await navigator.clipboard.writeText(challenge.code);
      onToast("کد ورود کپی شد");
    } catch {
      onToast("کد را به‌صورت دستی در بازوی بله وارد کنید");
    }
  }

  function logoutCustomer() {
    localStorage.removeItem(CUSTOMER_TOKEN_KEY);
    localStorage.removeItem(CUSTOMER_INFO_KEY);
    sessionStorage.removeItem(BALE_CHALLENGE_KEY);
    exchangeStarted.current = false;
    pollingFailures.current = 0;
    setCustomer(null);
    setChallenge(null);
    setErrorMessage("");
    setState("idle");
    setOpen(false);
    onToast("از حساب مشتری خارج شدید");
  }

  return (
    <>
      <Button
        className="bale-login-trigger"
        variant={state === "authenticated" ? "outlined" : "contained"}
        color={state === "authenticated" ? "success" : "primary"}
        startIcon={state === "authenticated" ? <CheckCircleRounded /> : <LoginRounded />}
        onClick={() => state === "authenticated" ? setOpen(true) : void startLogin()}
      >
        {state === "authenticated" ? customer?.display_name || "وارد شده‌اید" : "ورود با بله"}
      </Button>

      <Dialog
        open={open}
        onClose={() => state !== "creating" && state !== "approved" && setOpen(false)}
        fullWidth
        maxWidth="sm"
        fullScreen={isMobile}
        dir="rtl"
        className="bale-login-dialog"
        aria-labelledby="bale-login-title"
      >
        <DialogTitle id="bale-login-title">
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <Box className="bale-mark"><LoginRounded /></Box>
            <Box>
              <Typography component="span" variant="h6">ورود امن با بله</Typography>
              <Typography component="p" variant="caption" color="text.secondary">بدون رمز عبور و در کمتر از دو دقیقه</Typography>
            </Box>
          </Stack>
        </DialogTitle>
        <DialogContent dividers className="bale-login-content">
          {state === "creating" ? (
            <Box className="bale-centered-state" role="status">
              <CircularProgress size={42} />
              <Typography variant="h6">در حال ساخت کد امن…</Typography>
              <Typography color="text.secondary">چند لحظه صبر کنید.</Typography>
            </Box>
          ) : null}

          {state === "pending" && challenge ? (
            <Box className="bale-pending-layout">
              {!isMobile ? (
                <Box className="bale-qr-panel">
                  <Box className="bale-qr-frame">
                    <QRCodeSVG value={challenge.bot_url} size={196} level="M" marginSize={2} title="کد QR ورود با بله" />
                  </Box>
                  <Typography variant="body2" color="text.secondary">با دوربین موبایل اسکن کنید</Typography>
                </Box>
              ) : null}
              <Box className="bale-login-details">
                <Box className="bale-timer" role="timer" aria-live="polite">
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}><AccessTimeRounded /><Typography>زمان باقی‌مانده</Typography></Stack>
                  <Typography variant="h5">{formatCountdown(secondsLeft)}</Typography>
                </Box>
                <LinearProgress variant="determinate" value={Math.min(100, (secondsLeft / 120) * 100)} aria-label="زمان باقی‌مانده کد ورود" />
                <Box className="bale-code-box">
                  <Typography variant="caption" color="text.secondary">کد ورود یک‌بارمصرف</Typography>
                  <Typography className="bale-login-code" dir="ltr">{challenge.code.replace(/(.{3})/, "$1 ")}</Typography>
                  <Button size="small" startIcon={<ContentCopyRounded />} onClick={() => void copyCode()}>کپی کد</Button>
                </Box>
                <ol className="bale-login-steps">
                  <li>{isMobile ? "بازوی فروشگاه را در بله باز کنید." : "QR را با موبایل اسکن کنید."}</li>
                  <li>در بازو دکمه «تأیید ورود» را بزنید.</li>
                  <li>این صفحه خودکار وارد حساب شما می‌شود.</li>
                </ol>
                <Alert severity="info" icon={false}>اگر کد خودکار ارسال نشد، همین کد شش‌رقمی را برای بازو بفرستید.</Alert>
                {isMobile ? <Button fullWidth size="large" variant="contained" href={challenge.bot_url} startIcon={<OpenInNewRounded />}>بازکردن بازوی بله</Button> : null}
              </Box>
            </Box>
          ) : null}

          {state === "approved" ? (
            <Box className="bale-centered-state bale-success-state" role="status">
              <CircularProgress size={42} color="success" />
              <Typography variant="h6">تأیید انجام شد</Typography>
              <Typography color="text.secondary">در حال ورود به فروشگاه…</Typography>
            </Box>
          ) : null}
          {state === "authenticated" ? (
            <Box className="bale-centered-state bale-success-state" role="status">
              <CheckCircleRounded className="bale-success-icon" />
              <Typography variant="h6">شما وارد فروشگاه شده‌اید</Typography>
              <Typography color="text.secondary">{customer?.display_name ? `${customer.display_name} عزیز، خوش آمدید.` : "خوش آمدید؛ خریدتان را ادامه دهید."}</Typography>
              <Alert severity="success" icon={false}>پروفایل مشتری در فاز بعدی اضافه می‌شود.</Alert>
              <Button color="inherit" size="large" startIcon={<LogoutRounded />} onClick={logoutCustomer}>خروج از حساب</Button>
            </Box>
          ) : null}
          {state === "expired" ? (
            <Box className="bale-centered-state" role="alert">
              <AccessTimeRounded className="bale-expired-icon" />
              <Typography variant="h6">زمان این کد تمام شد</Typography>
              <Typography color="text.secondary">برای حفظ امنیت، هر کد فقط دو دقیقه معتبر است.</Typography>
              <Button size="large" variant="contained" startIcon={<RefreshRounded />} onClick={() => void startLogin()}>دریافت کد جدید</Button>
            </Box>
          ) : null}
          {state === "error" ? (
            <Box className="bale-centered-state" role="alert">
              <Alert severity="error" sx={{ width: "100%" }}>{errorMessage}</Alert>
              <Typography color="text.secondary">اتصال اینترنت را بررسی کنید و دوباره تلاش کنید.</Typography>
              <Button size="large" variant="contained" startIcon={<RefreshRounded />} onClick={() => void startLogin()}>تلاش دوباره</Button>
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions className="bale-dialog-actions">
          <Button onClick={() => setOpen(false)} disabled={state === "creating" || state === "approved"}>{state === "authenticated" ? "بستن" : "فعلاً نه"}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default function Storefront({ onOpenAdmin }: StorefrontProps) {
  const [category, setCategory] = useState("همه");
  const [query, setQuery] = useState("");
  const [cart, setCart] = useState<Record<number, number>>({});
  const [cartOpen, setCartOpen] = useState(false);
  const [toast, setToast] = useState("");

  const visibleProducts = useMemo(() => {
    return products.filter((product) => {
      const matchesCategory = category === "همه" || product.category === category;
      const matchesQuery = product.name.includes(query.trim());
      return matchesCategory && matchesQuery;
    });
  }, [category, query]);

  const cartItems = products.filter((product) => cart[product.id]);
  const cartCount = Object.values(cart).reduce((sum, quantity) => sum + quantity, 0);
  const cartTotal = cartItems.reduce((sum, product) => sum + product.price * cart[product.id], 0);

  function changeQuantity(product: Product, delta: number) {
    setCart((current) => {
      const next = Math.max(0, (current[product.id] ?? 0) + delta);
      const updated = { ...current, [product.id]: next };
      if (!next) delete updated[product.id];
      return updated;
    });
    if (delta > 0) setToast(`${product.name} به سبد اضافه شد`);
  }

  return (
    <Box className="storefront" dir="rtl">
      <AppBar position="sticky" color="inherit" elevation={0} className="storefront-appbar">
        <Container maxWidth="xl">
          <Toolbar disableGutters className="storefront-toolbar">
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }} className="storefront-brand">
              <Box className="storefront-logo"><StorefrontRounded /></Box>
              <Box>
                <Typography variant="h6">حبوباتین</Typography>
                <Typography variant="caption" color="text.secondary">خرید تازه و مطمئن</Typography>
              </Box>
            </Stack>
            <TextField
              className="storefront-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="جست‌وجوی کالا..."
              size="small"
              slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }}
            />
            <Stack direction="row" spacing={1} className="storefront-actions">
              <BaleCustomerLogin onToast={setToast} />
              <Tooltip title="ورود مدیر">
                <IconButton color="default" onClick={onOpenAdmin} aria-label="ورود مدیر"><AdminPanelSettingsRounded /></IconButton>
              </Tooltip>
              <Tooltip title="سبد خرید">
                <IconButton color="primary" onClick={() => setCartOpen(true)} aria-label="سبد خرید">
                  <Badge badgeContent={cartCount} color="secondary"><ShoppingBasketRounded /></Badge>
                </IconButton>
              </Tooltip>
            </Stack>
          </Toolbar>
        </Container>
      </AppBar>

      <Box component="section" className="storefront-hero" sx={{ backgroundImage: `url(${heroImage})` }}>
        <Container maxWidth="xl" className="storefront-hero-inner">
          <Box className="storefront-hero-copy">
            <Chip icon={<VerifiedRounded />} label="تضمین تازگی و کیفیت" color="primary" variant="outlined" />
            <Typography component="h1" variant="h2">خرید روزانه، تازه و بی‌دردسر</Typography>
            <Typography color="text.secondary">حبوبات، برنج و غلات منتخب را با قیمت روشن انتخاب کن و سفارش را در چند قدم کوتاه ثبت کن.</Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <Button variant="contained" size="large" endIcon={<ArrowBackRounded />} href="#products">مشاهده محصولات</Button>
              <Button variant="outlined" size="large" startIcon={<LocalShippingRounded />}>ارسال سریع تهران</Button>
            </Stack>
          </Box>
        </Container>
      </Box>

      <Container maxWidth="xl" component="main" id="products" className="storefront-main">
        <Box className="storefront-section-heading">
          <Box>
            <Typography variant="h4">انتخاب محصولات</Typography>
            <Typography color="text.secondary">دسته را انتخاب کن یا نام کالا را جست‌وجو کن.</Typography>
          </Box>
          <Typography color="text.secondary">{visibleProducts.length.toLocaleString("fa-IR")} کالا</Typography>
        </Box>

        <Stack direction="row" spacing={1} className="category-scroll">
          {categories.map((item) => (
            <Chip key={item} label={item} clickable color={category === item ? "primary" : "default"} variant={category === item ? "filled" : "outlined"} onClick={() => setCategory(item)} />
          ))}
        </Stack>

        {visibleProducts.length ? (
          <Box className="storefront-product-grid">
            {visibleProducts.map((product) => (
              <Card key={product.id} className="storefront-product-card">
                <Box className="product-photo" sx={{ backgroundImage: `url(${heroImage})`, backgroundPosition: product.position }}>
                  {product.badge ? <Chip label={product.badge} color="secondary" size="small" /> : null}
                </Box>
                <CardContent>
                  <Typography variant="h6">{product.name}</Typography>
                  <Typography variant="body2" color="text.secondary">بسته‌بندی بهداشتی، انتخاب وزن هنگام سفارش</Typography>
                  <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "end", mt: 2 }}>
                    <Box><Typography variant="h6" color="primary.main">{formatToman(product.price)}</Typography><Typography variant="caption" color="text.secondary">هر {product.unit}</Typography></Box>
                    {cart[product.id] ? (
                      <Stack direction="row" sx={{ alignItems: "center" }} className="quantity-stepper">
                        <IconButton size="small" onClick={() => changeQuantity(product, -1)}><RemoveRounded /></IconButton>
                        <Typography sx={{ fontWeight: 900 }}>{cart[product.id].toLocaleString("fa-IR")}</Typography>
                        <IconButton size="small" onClick={() => changeQuantity(product, 1)}><AddRounded /></IconButton>
                      </Stack>
                    ) : null}
                  </Stack>
                </CardContent>
                <CardActions>
                  <Button fullWidth variant={cart[product.id] ? "outlined" : "contained"} startIcon={<ShoppingBasketRounded />} onClick={() => changeQuantity(product, 1)}>
                    {cart[product.id] ? "افزودن یکی دیگر" : "افزودن به سبد"}
                  </Button>
                </CardActions>
              </Card>
            ))}
          </Box>
        ) : (
          <Box className="storefront-empty"><SearchRounded /><Typography variant="h6">کالایی پیدا نشد</Typography><Button onClick={() => { setQuery(""); setCategory("همه"); }}>پاک‌کردن فیلترها</Button></Box>
        )}

        <Box className="storefront-trust-band">
          <Stack><VerifiedRounded color="primary" /><Box><Typography sx={{ fontWeight: 900 }}>کنترل کیفیت</Typography><Typography variant="body2" color="text.secondary">بررسی تازگی پیش از بسته‌بندی</Typography></Box></Stack>
          <Stack><LocalShippingRounded color="info" /><Box><Typography sx={{ fontWeight: 900 }}>ارسال قابل پیگیری</Typography><Typography variant="body2" color="text.secondary">اطلاع از وضعیت سفارش</Typography></Box></Stack>
          <Stack><CheckCircleRounded color="secondary" /><Box><Typography sx={{ fontWeight: 900 }}>قیمت شفاف</Typography><Typography variant="body2" color="text.secondary">بدون هزینه پنهان</Typography></Box></Stack>
        </Box>
      </Container>

      <Dialog open={cartOpen} onClose={() => setCartOpen(false)} fullWidth maxWidth="sm" dir="rtl">
        <DialogTitle>سبد خرید شما</DialogTitle>
        <DialogContent dividers>
          {cartItems.length ? cartItems.map((product) => (
            <Box className="cart-dialog-row" key={product.id}>
              <Box><Typography sx={{ fontWeight: 900 }}>{product.name}</Typography><Typography variant="body2" color="text.secondary">{formatToman(product.price)} × {cart[product.id].toLocaleString("fa-IR")}</Typography></Box>
              <Stack direction="row" sx={{ alignItems: "center" }} className="quantity-stepper"><IconButton size="small" onClick={() => changeQuantity(product, -1)}><RemoveRounded /></IconButton><Typography sx={{ fontWeight: 900 }}>{cart[product.id].toLocaleString("fa-IR")}</Typography><IconButton size="small" onClick={() => changeQuantity(product, 1)}><AddRounded /></IconButton></Stack>
            </Box>
          )) : <Box className="storefront-empty"><ShoppingBasketRounded /><Typography>سبد خرید هنوز خالی است.</Typography></Box>}
          {cartItems.length ? <><Divider sx={{ my: 2 }} /><Stack direction="row" sx={{ justifyContent: "space-between" }}><Typography sx={{ fontWeight: 900 }}>جمع سفارش</Typography><Typography variant="h6" color="primary.main">{formatToman(cartTotal)}</Typography></Stack></> : null}
        </DialogContent>
        <DialogActions><Button onClick={() => setCartOpen(false)}>ادامه خرید</Button><Button variant="contained" disabled={!cartItems.length}>ادامه ثبت سفارش</Button></DialogActions>
      </Dialog>

      <Snackbar open={Boolean(toast)} autoHideDuration={2200} onClose={() => setToast("")} message={toast} />
    </Box>
  );
}
