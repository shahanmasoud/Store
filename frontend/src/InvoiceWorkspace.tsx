import type { ReactNode } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, useMediaQuery, useTheme } from "@mui/material";
import EditRounded from "@mui/icons-material/EditRounded";
import DeleteOutlineRounded from "@mui/icons-material/DeleteOutlineRounded";
import CloseRounded from "@mui/icons-material/CloseRounded";
import ShoppingCartCheckoutRounded from "@mui/icons-material/ShoppingCartCheckoutRounded";
import { formatRial } from "./numberUtils";
import "./invoiceWorkspace.css";

export type CartRow = { id: string; name: string; detail: string; total: number };

export function InvoiceCart({ mode, items, total, busy, onEdit, onRemove, onContinue }: {
  mode: "sale" | "purchase"; items: CartRow[]; total: number; busy: boolean;
  onEdit: (id: string) => void; onRemove: (id: string) => void; onContinue: () => void;
}) {
  return <aside className="invoice-cart" aria-label={mode === "sale" ? "سبد فروش" : "سبد خرید"}>
    <header className="invoice-cart-heading"><h3>{mode === "sale" ? "اقلام فاکتور" : "اقلام خرید"}</h3><span>{items.length.toLocaleString("fa-IR")} ردیف</span></header>
    <div className="invoice-items">
      {items.length === 0 ? <div className="invoice-cart-empty"><ShoppingCartCheckoutRounded /><strong>فاکتور هنوز خالی است</strong><span>کالا را انتخاب و مقدار آن را وارد کنید.</span></div> : items.map((item) => <article key={item.id} className={`invoice-item${mode === "purchase" ? " purchase-invoice-item" : ""}`}>
        <div className="invoice-item-main"><strong>{item.name}</strong><span>{item.detail}</span></div>
        <div className="invoice-item-end"><strong>{formatRial(item.total)}</strong><div><IconButton aria-label="ویرایش" title="ویرایش" disabled={busy} onClick={() => onEdit(item.id)}><EditRounded fontSize="small" /></IconButton><IconButton aria-label="حذف" title="حذف" color="error" disabled={busy} onClick={() => onRemove(item.id)}><DeleteOutlineRounded fontSize="small" /></IconButton></div></div>
      </article>)}
    </div>
    <footer className="invoice-cart-footer"><div><span>جمع فاکتور</span><strong>{formatRial(total)}</strong></div><Button fullWidth variant="contained" disabled={busy || items.length === 0} onClick={onContinue} startIcon={<ShoppingCartCheckoutRounded />}>{mode === "sale" ? "ادامه و پرداخت" : "ادامه و ثبت خرید"}</Button></footer>
  </aside>;
}

export function InvoiceCheckout({ open, mode, busy, onClose, children, action }: {
  open: boolean; mode: "sale" | "purchase"; busy: boolean; onClose: () => void; children: ReactNode; action: ReactNode;
}) {
  const mobile = useMediaQuery(useTheme().breakpoints.down("sm"));
  const titleId = `${mode}-checkout-title`;
  return <Dialog open={open} onClose={() => { if (!busy) onClose(); }} fullScreen={mobile} fullWidth maxWidth="md" className="invoice-checkout" aria-labelledby={titleId}>
    <DialogTitle id={`${titleId}-heading`}><div className="invoice-checkout-heading"><div><span className="invoice-step">۲ / مشخصات و تسویه</span><span id={titleId}>{mode === "sale" ? "تکمیل فروش" : "تکمیل خرید"}</span></div><IconButton aria-label="بستن" disabled={busy} onClick={onClose}><CloseRounded /></IconButton></div></DialogTitle>
    <DialogContent dividers>{children}</DialogContent>
    <DialogActions><Button disabled={busy} onClick={onClose}>بازگشت به اقلام</Button>{action}</DialogActions>
  </Dialog>;
}
