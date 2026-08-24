export type User = {
  id: number | string;
  username: string;
  full_name?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type ProductVariant = {
  id: number;
  product_id: number;
  unit_id: number;
  name: string;
  sku?: string | null;
  retail_price_rial: number;
  wholesale_price_rial?: number | null;
  min_wholesale_quantity?: string | number | null;
  is_active: boolean;
};

export type PaymentMethod = "cash" | "card" | "transfer" | "credit" | "cheque" | "voucher";
export type PaymentStatus = "received" | "pending";

export type SaleInvoiceItemCreate = {
  variant_id: number;
  quantity: number;
  unit_price_rial: number;
  discount_amount_rial?: number;
  estimated_cost_rial?: number;
};

export type PaymentCreate = {
  method: PaymentMethod;
  amount_rial: number;
  status?: PaymentStatus;
  reference_number?: string;
  jalali_date?: string;
  local_time?: string;
  due_jalali_date?: string;
  note?: string;
};

export type SaleInvoiceCreate = {
  customer_name?: string;
  jalali_date: string;
  local_time: string;
  discount_amount_rial: number;
  note?: string;
  items: SaleInvoiceItemCreate[];
  payments: PaymentCreate[];
};

export type SaleInvoice = {
  id: number;
  invoice_number?: string | null;
  customer_name?: string | null;
  subtotal_rial: number;
  discount_amount_rial: number;
  total_rial: number;
  paid_total_rial: number;
  due_total_rial: number;
  status: "active" | "canceled";
  is_active: boolean;
  jalali_date: string;
  local_time: string;
  timezone: string;
};

export type DailyJournalPayment = {
  method: PaymentMethod;
  received_rial: number;
  pending_rial: number;
};

export type DailyJournal = {
  jalali_date: string;
  invoice_count: number;
  sales_total_rial: number;
  received_total_rial: number;
  pending_total_rial: number;
  payments: DailyJournalPayment[];
};

export type PurchaseInvoiceItemCreate = {
  variant_id: number;
  quantity: number;
  unit_cost_rial: number;
  extra_cost_rial?: number;
};

export type PurchaseInvoiceItem = {
  id: number;
  variant_id: number;
  quantity: number | string;
  unit_cost_rial: number;
  extra_cost_rial: number;
  line_total_rial: number;
};

export type PurchaseInvoiceCreate = {
  supplier_id?: number | null;
  supplier_name?: string | null;
  jalali_date: string;
  local_time: string;
  discount_amount_rial: number;
  extra_cost_rial: number;
  paid_total_rial: number;
  note?: string | null;
  items: PurchaseInvoiceItemCreate[];
};

export type PurchaseInvoice = {
  id: number;
  invoice_number?: string | null;
  supplier_id?: number | null;
  supplier_name?: string | null;
  subtotal_rial: number;
  discount_amount_rial: number;
  extra_cost_rial: number;
  total_rial: number;
  paid_total_rial: number;
  due_total_rial: number;
  status: "active" | "canceled";
  is_active: boolean;
  jalali_date: string;
  local_time: string;
  timezone: string;
  note?: string | null;
  items: PurchaseInvoiceItem[];
};

export type InventoryItem = {
  id: number;
  variant_id: number;
  variant_name: string;
  quantity_on_hand: number | string;
  weighted_average_cost_rial: number;
  reorder_level?: number | string | null;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("store_auth_token");
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "ارتباط با سرور برقرار نشد. دوباره تلاش کنید.";
    try {
      const body = await response.json();
      message = body.detail ?? body.message ?? message;
      if (Array.isArray(body.detail)) {
        message = body.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("، ");
      }
    } catch {
      message =
        response.status === 401 ? "نام کاربری یا رمز عبور درست نیست." : message;
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  login(username: string, password: string) {
    return request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  me() {
    return request<User>("/auth/me");
  },
  productVariants() {
    return request<ProductVariant[]>("/product-variants");
  },
  createSale(payload: SaleInvoiceCreate) {
    return request<SaleInvoice>("/sales", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  dailyJournal(jalaliDate: string) {
    return request<DailyJournal>(`/daily-journal?jalali_date=${encodeURIComponent(jalaliDate)}`);
  },
  createPurchaseInvoice(payload: PurchaseInvoiceCreate) {
    return request<PurchaseInvoice>("/purchase-invoices", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  purchaseInvoices() {
    return request<PurchaseInvoice[]>("/purchase-invoices");
  },
  purchaseInvoice(id: number) {
    return request<PurchaseInvoice>(`/purchase-invoices/${id}`);
  },
  cancelPurchaseInvoice(id: number) {
    return request<PurchaseInvoice>(`/purchase-invoices/${id}/cancel`, {
      method: "POST",
    });
  },
  inventory() {
    return request<InventoryItem[]>("/inventory");
  },
};
