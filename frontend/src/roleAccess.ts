export type AdminView = "dashboard" | "sales" | "purchase" | "inventory" | "products" | "ledger" | "cheques" | "reports" | "online" | "users";

export type RolePermissions = {
  is_superuser?: boolean;
  can_sales?: boolean;
  can_catalog_inventory?: boolean;
  can_ledger?: boolean;
  can_cheques_reports?: boolean;
};

export function canAccessAdminView(user: RolePermissions | null | undefined, view: AdminView): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (view === "dashboard") return true;
  if (view === "sales") return Boolean(user.can_sales);
  if (view === "products" || view === "purchase" || view === "inventory") return Boolean(user.can_catalog_inventory);
  if (view === "ledger") return Boolean(user.can_ledger);
  if (view === "cheques" || view === "reports") return Boolean(user.can_cheques_reports);
  return false;
}
