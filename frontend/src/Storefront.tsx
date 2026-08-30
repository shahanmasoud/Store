import { useMemo, useState } from "react";
import {
  AppBar,
  Badge,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  InputAdornment,
  Snackbar,
  Stack,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import AdminPanelSettingsRounded from "@mui/icons-material/AdminPanelSettingsRounded";
import AddRounded from "@mui/icons-material/AddRounded";
import ArrowBackRounded from "@mui/icons-material/ArrowBackRounded";
import CheckCircleRounded from "@mui/icons-material/CheckCircleRounded";
import LocalShippingRounded from "@mui/icons-material/LocalShippingRounded";
import RemoveRounded from "@mui/icons-material/RemoveRounded";
import SearchRounded from "@mui/icons-material/SearchRounded";
import ShoppingBasketRounded from "@mui/icons-material/ShoppingBasketRounded";
import StorefrontRounded from "@mui/icons-material/StorefrontRounded";
import VerifiedRounded from "@mui/icons-material/VerifiedRounded";
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
            <Stack direction="row" spacing={1}>
              <Tooltip title="ورود مدیر">
                <Button color="inherit" startIcon={<AdminPanelSettingsRounded />} onClick={onOpenAdmin}>مدیریت</Button>
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
