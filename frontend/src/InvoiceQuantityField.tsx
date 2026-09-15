import { IconButton } from "@mui/material";
import AddRounded from "@mui/icons-material/AddRounded";
import RemoveRounded from "@mui/icons-material/RemoveRounded";
import { LocalizedDecimalField } from "./LocalizedDecimalField";
import { normalizeDecimal } from "./numberUtils";

export function InvoiceQuantityField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const quantity = normalizeDecimal(value);
  return <div className="invoice-quantity-control">
    <IconButton aria-label="افزایش مقدار" onClick={() => onChange(String(Math.round((quantity + 1) * 1000000) / 1000000))}><AddRounded /></IconButton>
    <LocalizedDecimalField label="مقدار" value={value} onValueChange={onChange} required />
    <IconButton aria-label="کاهش مقدار" disabled={quantity <= 1} onClick={() => onChange(String(Math.round((quantity - 1) * 1000000) / 1000000))}><RemoveRounded /></IconButton>
  </div>;
}
