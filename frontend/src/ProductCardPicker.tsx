import { useMemo, useState } from "react";
import { Button, InputAdornment, MenuItem, TextField } from "@mui/material";
import SearchRounded from "@mui/icons-material/SearchRounded";
import Inventory2Rounded from "@mui/icons-material/Inventory2Rounded";
import CheckCircleRounded from "@mui/icons-material/CheckCircleRounded";
import { apiAssetUrl, type Category, type Product, type ProductVariant, type Unit } from "./api";
import { formatRial, toEnglishDigits, toPersianDigits } from "./numberUtils";

export type PickerCatalog = { products: Product[]; categories: Category[]; units: Unit[] };
export const emptyPickerCatalog: PickerCatalog = { products: [], categories: [], units: [] };
const normalizeSearch = (value: string) => toEnglishDigits(value).replace(/ي/g, "ی").replace(/ك/g, "ک").trim().toLocaleLowerCase("fa");

export function ProductCardPicker({ variants, catalog, value, onSelect, quantities, available, disabled = false, mode }: {
  variants: ProductVariant[]; catalog: PickerCatalog; value: string; onSelect: (value: string) => void;
  quantities: Record<number, number>; available?: Record<number, number>; disabled?: boolean; mode: "sale" | "purchase";
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());
  const products = useMemo(() => new Map(catalog.products.map((item) => [item.id, item])), [catalog.products]);
  const units = useMemo(() => new Map(catalog.units.map((item) => [item.id, item.name])), [catalog.units]);
  const filtered = variants.filter((variant) => {
    const product = products.get(variant.product_id);
    return (!category || String(product?.category_id ?? "none") === category) && normalizeSearch(`${variant.name} ${variant.sku ?? ""} ${product?.name ?? ""}`).includes(normalizeSearch(search));
  });
  const selected = variants.find((variant) => String(variant.id) === value);
  return <section className="product-picker" aria-label={mode === "sale" ? "انتخاب کالای فروش" : "انتخاب کالای خرید"}>
    <div className="product-picker-filters">
      <TextField size="small" label="جستجوی کالا" placeholder="نام یا کد کالا" value={search} onChange={(event) => setSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} />
      <TextField select size="small" slotProps={{ select: { displayEmpty: true } }} label="دسته‌بندی کالا" value={category} onChange={(event) => setCategory(event.target.value)}>
        <MenuItem value="">همه دسته‌ها</MenuItem>
        {catalog.categories.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.name}</MenuItem>)}
        <MenuItem value="none">بدون دسته‌بندی</MenuItem>
      </TextField>
    </div>
    <div className="product-picker-count" role="status">{toPersianDigits(filtered.length)} کالا{selected ? ` · انتخاب فعلی: ${selected.name}` : ""}</div>
    <div className="product-picker-grid">
      {filtered.map((variant) => {
        const product = products.get(variant.product_id);
        const image = apiAssetUrl(product?.image_url);
        const isSelected = value === String(variant.id);
        const quantity = quantities[variant.id] ?? 0;
        const stock = available?.[variant.id];
        return <button type="button" className={`product-picker-card${isSelected ? " is-selected" : ""}`} key={variant.id} aria-label={`انتخاب ${variant.name}`} aria-pressed={isSelected} data-testid={`product-card-${variant.id}`} disabled={disabled} onClick={() => onSelect(String(variant.id))}>
          <span className="product-picker-image">{image && !failedImages.has(image) ? <img src={image} alt="" loading="lazy" onError={() => setFailedImages((current) => new Set(current).add(image))} /> : <Inventory2Rounded />}{isSelected ? <CheckCircleRounded className="product-picker-check" /> : null}</span>
          <span className="product-picker-identity"><strong>{toPersianDigits(variant.name)}</strong>
          <span className="product-picker-unit">{units.get(variant.unit_id) ?? "واحد"}{variant.sku ? ` · ${toPersianDigits(variant.sku)}` : ""}</span></span>
          {mode === "sale" ? <span className="product-picker-price">{formatRial(variant.retail_price_rial)}</span> : null}
          {stock !== undefined ? <span className={stock <= 0 ? "product-picker-stock is-empty" : "product-picker-stock"}>{stock <= 0 ? "ناموجود" : `موجودی: ${stock.toLocaleString("fa-IR")}`}</span> : null}
          {quantity > 0 ? <span className="product-picker-added">{quantity.toLocaleString("fa-IR")} در فاکتور</span> : null}
        </button>;
      })}
    </div>
    {filtered.length === 0 ? <div className="record-state"><SearchRounded /><strong>کالایی پیدا نشد</strong><Button type="button" onClick={() => { setSearch(""); setCategory(""); }}>پاک کردن فیلترها</Button></div> : null}
  </section>;
}
