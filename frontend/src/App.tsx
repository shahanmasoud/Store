import { useEffect, useMemo, useState } from "react";
import { api, type User } from "./api";

const TOKEN_KEY = "store_auth_token";

type AuthStatus = "checking" | "guest" | "authenticated";

const moduleCards = [
  {
    title: "فروش",
    description: "ثبت فروش سریع، پرداخت و صدور فاکتور روزانه",
    icon: "ف",
    accent: "teal",
  },
  {
    title: "کالاها",
    description: "تعریف کالا، واحدها و قیمت‌های پایه",
    icon: "ک",
    accent: "blue",
  },
  {
    title: "خرید",
    description: "ثبت خرید از تامین‌کننده و قیمت تمام‌شده",
    icon: "خ",
    accent: "amber",
  },
  {
    title: "انبار",
    description: "موجودی، ورود و خروج و هشدار کمبود",
    icon: "ا",
    accent: "green",
  },
  {
    title: "دفتر حساب",
    description: "حساب مشتریان، تامین‌کنندگان و تسویه‌ها",
    icon: "د",
    accent: "violet",
  },
  {
    title: "چک‌ها",
    description: "چک‌های دریافتی، پرداختی و سررسیدها",
    icon: "چ",
    accent: "rose",
  },
  {
    title: "گزارش‌ها",
    description: "گزارش فروش، سود، بدهکاران و عملکرد روز",
    icon: "گ",
    accent: "slate",
  },
];

function App() {
  const [status, setStatus] = useState<AuthStatus>("checking");
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

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
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
            فاز اول با یک ورود ساده و داشبورد عملیاتی شروع می‌شود تا مسیر ثبت
            فروش، انبار و گزارش‌ها مرحله‌به‌مرحله روی همین پایه ساخته شود.
          </p>
          <div className="status-strip" aria-label="وضعیت فاز اول">
            <span>فاز ۱</span>
            <strong>هوم و لاگین</strong>
          </div>
        </section>

        <section className="login-panel" aria-label="فرم ورود">
          <div className="panel-header">
            <h2>ورود مدیر</h2>
            <p>نام کاربری و رمز عبور حساب مدیر را وارد کنید.</p>
          </div>
          <form onSubmit={handleLogin} className="login-form">
            <label htmlFor="username">نام کاربری</label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              placeholder="مثلا admin"
              required
            />

            <label htmlFor="password">رمز عبور</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="رمز عبور"
              required
            />

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

      <section className="overview-band" aria-label="وضعیت امروز">
        <div>
          <span>امروز</span>
          <strong>آماده ثبت عملیات</strong>
        </div>
        <div>
          <span>مرحله پروژه</span>
          <strong>فاز ۱ فعال</strong>
        </div>
        <div>
          <span>ماژول‌ها</span>
          <strong>در حال آماده‌سازی</strong>
        </div>
      </section>

      <section className="section-header">
        <div>
          <h2>بخش‌های اصلی سیستم</h2>
          <p>
            در این فاز ساختار اصلی آماده شده و ماژول‌ها در فازهای بعدی فعال
            می‌شوند.
          </p>
        </div>
        <span className="badge">نسخه اولیه</span>
      </section>

      <section className="module-grid" aria-label="ماژول‌های سیستم">
        {moduleCards.map((card) => {
          return (
            <article className={`module-card accent-${card.accent}`} key={card.title}>
              <div className="module-icon">
                <span aria-hidden="true">{card.icon}</span>
              </div>
              <div>
                <h3>{card.title}</h3>
                <p>{card.description}</p>
              </div>
              <span className="coming-soon">به‌زودی</span>
            </article>
          );
        })}
      </section>

      <section className="next-step-panel">
        <span className="next-step-icon" aria-hidden="true">
          ۲
        </span>
        <div>
          <h2>قدم بعدی</h2>
          <p>
            بعد از تایید فاز ۱، مدل‌های داده، زمان شمسی و APIهای پایه را اضافه
            می‌کنیم.
          </p>
        </div>
      </section>
    </main>
  );
}

export default App;
