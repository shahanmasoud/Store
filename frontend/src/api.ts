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

export type Unit = { id: number; name: string; symbol: string; is_active: boolean };
export type Category = { id: number; name: string; parent_id?: number | null; is_active: boolean };
export type Product = { id: number; name: string; description?: string | null; category_id?: number | null; is_active: boolean };
export type PersonType = "customer" | "supplier" | "both";
export type Person = { id: number; name: string; phone?: string | null; person_type: PersonType; is_active: boolean };
export type LedgerEntry = {
  id: number;
  person_id: number;
  entry_type: "debit" | "credit";
  amount_rial: number;
  remaining_rial: number;
  source_type: string;
  source_id?: number | null;
  jalali_date: string;
  local_time: string;
  description?: string | null;
  status: string;
  is_active: boolean;
};
export type ChequeType = "received" | "paid";
export type Cheque = {
  id: number;
  cheque_type: ChequeType;
  person_id?: number | null;
  bank_name: string;
  cheque_number: string;
  amount_rial: number;
  issue_jalali_date: string;
  due_jalali_date: string;
  local_time: string;
  note?: string | null;
  status: string;
  is_active: boolean;
  events: unknown[];
};
export type Dues = { jalali_date_to: string; open_ledger_entries: LedgerEntry[]; pending_cheques: Cheque[] };
export type SalesSummaryReport = {
  from_jalali: string;
  to_jalali: string;
  invoice_count: number;
  registered_sales_rial: number;
  received_rial: number;
  pending_rial: number;
  average_invoice_rial: number;
};
export type ProfitLossReport = {
  sales_rial: number;
  estimated_cost_rial: number;
  gross_profit_rial: number;
  gross_margin_percent: number;
};
export type InventoryReport = {
  item_count: number;
  total_value_rial: number;
  low_stock_count: number;
  items: InventoryItem[];
};
export type CashflowReport = {
  pending_sales_payments_rial: number;
  open_ledger_rial: number;
  pending_received_cheques_rial: number;
  pending_paid_cheques_rial: number;
  net_expected_rial: number;
};
export type CustomerDebtsReport = { total_remaining_rial: number; people: Array<Person & { remaining_rial: number }> };
export type OnlineChannel = { id: number; name: string; note?: string | null; is_active: boolean };
export type OnlineOrder = {
  id: number;
  channel_id: number;
  customer_name: string;
  customer_phone?: string | null;
  status: string;
  total_rial: number;
  jalali_date: string;
  local_time: string;
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
  units() {
    return request<Unit[]>("/units");
  },
  createUnit(payload: { name: string; symbol: string }) {
    return request<Unit>("/units", { method: "POST", body: JSON.stringify(payload) });
  },
  categories() {
    return request<Category[]>("/categories");
  },
  createCategory(payload: { name: string; parent_id?: number | null }) {
    return request<Category>("/categories", { method: "POST", body: JSON.stringify(payload) });
  },
  products() {
    return request<Product[]>("/products");
  },
  createProduct(payload: { name: string; description?: string; category_id?: number | null }) {
    return request<Product>("/products", { method: "POST", body: JSON.stringify(payload) });
  },
  createProductVariant(payload: {
    product_id: number;
    unit_id: number;
    name: string;
    sku?: string;
    retail_price_rial: number;
    wholesale_price_rial?: number | null;
    min_wholesale_quantity?: number | null;
  }) {
    return request<ProductVariant>("/product-variants", { method: "POST", body: JSON.stringify(payload) });
  },
  createPrice(payload: { variant_id: number; price_type: "retail" | "wholesale" | "online"; amount_rial: number; jalali_date: string; local_time: string }) {
    return request<unknown>("/prices", { method: "POST", body: JSON.stringify(payload) });
  },
  persons() {
    return request<Person[]>("/persons");
  },
  createPerson(payload: { name: string; phone?: string; person_type: PersonType }) {
    return request<Person>("/persons", { method: "POST", body: JSON.stringify(payload) });
  },
  personLedger(personId: number) {
    return request<LedgerEntry[]>(`/ledger/persons/${personId}`);
  },
  createManualEntry(payload: { person_id: number; entry_type: "debit" | "credit"; amount_rial: number; jalali_date: string; local_time: string; description?: string }) {
    return request<LedgerEntry>("/ledger/manual-entry", { method: "POST", body: JSON.stringify(payload) });
  },
  createSettlement(payload: { person_id: number; amount_rial: number; jalali_date: string; local_time: string; note?: string }) {
    return request<unknown>("/settlements", { method: "POST", body: JSON.stringify(payload) });
  },
  dues(jalaliDateTo: string) {
    return request<Dues>(`/dues?jalali_date_to=${encodeURIComponent(jalaliDateTo)}`);
  },
  cheques() {
    return request<Cheque[]>("/cheques");
  },
  createCheque(payload: {
    cheque_type: ChequeType;
    person_id?: number | null;
    bank_name: string;
    cheque_number: string;
    amount_rial: number;
    issue_jalali_date: string;
    due_jalali_date: string;
    local_time: string;
    note?: string;
  }) {
    return request<Cheque>("/cheques", { method: "POST", body: JSON.stringify(payload) });
  },
  createChequeEvent(id: number, payload: { event_type: "cleared" | "bounced" | "canceled"; jalali_date: string; local_time: string; note?: string }) {
    return request<Cheque>(`/cheques/${id}/events`, { method: "POST", body: JSON.stringify(payload) });
  },
  salesSummary(from: string, to: string) {
    return request<SalesSummaryReport>(`/reports/sales-summary?from_jalali=${encodeURIComponent(from)}&to_jalali=${encodeURIComponent(to)}`);
  },
  profitLoss(from: string, to: string) {
    return request<ProfitLossReport>(`/reports/profit-loss?from_jalali=${encodeURIComponent(from)}&to_jalali=${encodeURIComponent(to)}`);
  },
  inventoryReport() {
    return request<InventoryReport>("/reports/inventory");
  },
  cashflow(jalaliDateTo: string) {
    return request<CashflowReport>(`/reports/cashflow?jalali_date_to=${encodeURIComponent(jalaliDateTo)}`);
  },
  customerDebts() {
    return request<CustomerDebtsReport>("/reports/customer-debts");
  },
  onlineChannels() {
    return request<OnlineChannel[]>("/online/channels");
  },
  createOnlineChannel(payload: { name: string; token: string; note?: string }) {
    return request<OnlineChannel>("/online/channels", { method: "POST", body: JSON.stringify(payload) });
  },
  onlineOrders(channelId?: number) {
    const query = channelId ? `?channel_id=${channelId}` : "";
    return request<OnlineOrder[]>(`/online/orders${query}`);
  },
};
