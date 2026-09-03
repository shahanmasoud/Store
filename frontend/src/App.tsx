import { lazy, Suspense, useEffect, useState } from "react";
import Storefront from "./Storefront";

const AdminApp = lazy(() => import("./AdminApp"));

function AppLoading() {
  return (
    <main className="shell center-shell" aria-busy="true">
      <section className="checking-panel" aria-live="polite">
        <div className="loader" />
        <p>در حال آماده‌سازی پنل مدیریت...</p>
      </section>
    </main>
  );
}

export default function App() {
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
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  if (surface === "admin") {
    return (
      <Suspense fallback={<AppLoading />}>
        <AdminApp onOpenStore={() => navigate("/")} />
      </Suspense>
    );
  }

  return <Storefront onOpenAdmin={() => navigate("/admin")} />;
}
