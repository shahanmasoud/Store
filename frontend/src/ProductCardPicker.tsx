import { useMemo, useState } from "react";
import { Button, InputAdornment, MenuItem, TextField } from "@mui/material";
import ArrowBackRounded from "@mui/icons-material/ArrowBackRounded";
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
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());
  const products = useMemo(() => new Map(catalog.products.map((item) => [item.id, item])), [catalog.products]);
  const units = useMemo(() => new Map(catalog.units.map((item) => [item.id, item.name])), [catalog.units]);
  const orderedCategories = useMemo(() => {
    const children = new Map<number | null, Category[]>();
    catalog.categories.forEach((item) => {
      const parentId = item.parent_id ?? null;
      children.set(parentId, [...(children.get(parentId) ?? []), item]);
    });
    children.forEach((items) => items.sort((a, b) => a.name.localeCompare(b.name, "fa")));
    const result: Array<Category & { depth: number }> = [];
    const seen = new Set<number>();
    const visit = (parentId: number | null, depth: number) => {
      (children.get(parentId) ?? []).forEach((item) => {
        if (seen.has(item.id)) return;
        seen.add(item.id);
        result.push({ ...item, depth });
        visit(item.id, depth + 1);
      });
    };
    visit(null, 0);
    catalog.categories.forEach((item) => {
      if (!seen.has(item.id)) result.push({ ...item, depth: 0 });
    });
    return result;
  }, [catalog.categories]);
  const selectedCategoryIds = useMemo(() => {
    if (!category || category === "none") return null;
    const rootId = Number(category);
    const ids = new Set<number>([rootId]);
    let changed = true;
    while (changed) {
      changed = false;
      catalog.categories.forEach((item) => {
        if (item.parent_id != null && ids.has(item.parent_id) && !ids.has(item.id)) {
          ids.add(item.id);
          changed = true;
        }
      });
    }
    return ids;
  }, [catalog.categories, category]);
  const matchesCategory = (categoryId: number | null | undefined) => !category
    || (category === "none" ? categoryId == null : selectedCategoryIds?.has(categoryId ?? -1) === true);
  const selected = variants.find((variant) => String(variant.id) === value);
  const hierarchical = mode === "sale";
  const productRows = useMemo(() => catalog.products.map((product) => ({ product, variants: variants.filter((variant) => variant.product_id === product.id) })).filter((row) => row.variants.length > 0), [catalog.products, variants]);
  const filteredProducts = productRows.filter(({ product, variants: childVariants }) => matchesCategory(product.category_id) && normalizeSearch(`${product.name} ${product.description ?? ""} ${childVariants.map((variant) => `${variant.name} ${variant.sku ?? ""}`).join(" ")}`).includes(normalizeSearch(search)));
  const filteredVariants = variants.filter((variant) => {
    const product = products.get(variant.product_id);
    return (!hierarchical || selectedProductId === null || variant.product_id === selectedProductId) && matchesCategory(product?.category_id) && normalizeSearch(`${variant.name} ${variant.sku ?? ""} ${product?.name ?? ""}`).includes(normalizeSearch(search));
  });
  const activeProduct = selectedProductId === null ? undefined : products.get(selectedProductId);
  const showingProducts = hierarchical && selectedProductId === null;
  const visibleCount = showingProducts ? filteredProducts.length : filteredVariants.length;
  const clearFilters = () => { setSearch(""); setCategory(""); };

  return <section className="product-picker" aria-label={mode === "sale" ? "انتخاب کالای فروش" : "انتخاب کالای خرید"}>
    {activeProduct ? <div className="product-picker-level-heading"><Button type="button" size="small" variant="outlined" startIcon={<ArrowBackRounded />} onClick={() => { setSelectedProductId(null); setSearch(""); }}>بازگشت به کالاها</Button><div><span>گونه‌های کالا</span><strong>{toPersianDigits(activeProduct.name)}</strong></div></div> : null}
    <div className="product-picker-filters">
      <TextField size="small" label={showingProducts ? "جستجوی کالا" : "جستجوی گونه"} placeholder={showingProducts ? "نام کالا" : "نام یا کد گونه"} value={search} onChange={(event) => setSearch(event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} />
      <TextField select size="small" slotProps={{ select: { displayEmpty: true } }} label="دسته‌بندی کالا" value={category} onChange={(event) => { setCategory(event.target.value); if (activeProduct) setSelectedProductId(null); }}>
        <MenuItem value="">همه دسته‌ها</MenuItem>{orderedCategories.map((item) => <MenuItem key={item.id} value={String(item.id)}>{`${"— ".repeat(item.depth)}${item.name}`}</MenuItem>)}<MenuItem value="none">بدون دسته‌بندی</MenuItem>
      </TextField>
    </div>
    <div className="product-picker-count" role="status">{toPersianDigits(visibleCount)} {showingProducts ? "کالا" : hierarchical ? "گونه" : "کالا"}{selected ? ` · انتخاب فعلی: ${selected.name}` : ""}</div>
    <div className="product-picker-grid">
      {showingProducts ? filteredProducts.map(({ product, variants: childVariants }) => {
        const image = apiAssetUrl(product.image_url ?? childVariants.find((variant) => variant.image_url)?.image_url);
        const quantity = childVariants.reduce((sum, variant) => sum + (quantities[variant.id] ?? 0), 0);
        const stocks = childVariants.map((variant) => available?.[variant.id]).filter((item): item is number => item !== undefined);
        const stock = stocks.length ? stocks.reduce((sum, item) => sum + item, 0) : undefined;
        const prices = childVariants.map((variant) => variant.retail_price_rial), minPrice = Math.min(...prices), maxPrice = Math.max(...prices);
        return <button type="button" className="product-picker-card product-picker-product-card" key={product.id} aria-label={`انتخاب کالای ${product.name}`} data-testid={`product-group-${product.id}`} disabled={disabled} onClick={() => { setSelectedProductId(product.id); setSearch(""); }}>
          <span className="product-picker-image">{image && !failedImages.has(image) ? <img src={image} alt="" loading="lazy" onError={() => setFailedImages((current) => new Set(current).add(image))} /> : <Inventory2Rounded />}</span>
          <span className="product-picker-identity"><strong>{toPersianDigits(product.name)}</strong><span className="product-picker-unit">{toPersianDigits(childVariants.length)} گونه</span></span>
          <span className="product-picker-price">{minPrice === maxPrice ? formatRial(minPrice) : `${formatRial(minPrice)} تا ${formatRial(maxPrice)}`}</span>
          {stock !== undefined ? <span className={stock <= 0 ? "product-picker-stock is-empty" : "product-picker-stock"}>{stock <= 0 ? "ناموجود" : `موجودی کل: ${stock.toLocaleString("fa-IR")}`}</span> : null}
          {quantity > 0 ? <span className="product-picker-added">{quantity.toLocaleString("fa-IR")} در فاکتور</span> : <span className="product-picker-next">مشاهده گونه‌ها</span>}
        </button>;
      }) : filteredVariants.map((variant) => {
        const product = products.get(variant.product_id), image = apiAssetUrl(variant.image_url ?? product?.image_url), isSelected = value === String(variant.id), quantity = quantities[variant.id] ?? 0, stock = available?.[variant.id];
        return <button type="button" className={`product-picker-card${isSelected ? " is-selected" : ""}`} key={variant.id} aria-label={hierarchical ? `انتخاب گونه ${variant.name}` : `انتخاب ${variant.name}`} aria-pressed={isSelected} data-testid={`product-card-${variant.id}`} disabled={disabled} onClick={() => onSelect(String(variant.id))}>
          <span className="product-picker-image">{image && !failedImages.has(image) ? <img src={image} alt="" loading="lazy" onError={() => setFailedImages((current) => new Set(current).add(image))} /> : <Inventory2Rounded />}{isSelected ? <CheckCircleRounded className="product-picker-check" /> : null}</span>
          <span className="product-picker-identity"><strong>{toPersianDigits(variant.name)}</strong><span className="product-picker-unit">{units.get(variant.unit_id) ?? "واحد"}{variant.sku ? ` · ${toPersianDigits(variant.sku)}` : ""}</span></span>
          {mode === "sale" ? <span className="product-picker-price">{formatRial(variant.retail_price_rial)}</span> : null}{stock !== undefined ? <span className={stock <= 0 ? "product-picker-stock is-empty" : "product-picker-stock"}>{stock <= 0 ? "ناموجود" : `موجودی: ${stock.toLocaleString("fa-IR")}`}</span> : null}{quantity > 0 ? <span className="product-picker-added">{quantity.toLocaleString("fa-IR")} در فاکتور</span> : null}
        </button>;
      })}
    </div>
    {visibleCount === 0 ? <div className="record-state"><SearchRounded /><strong>{showingProducts ? "کالایی پیدا نشد" : "گونه‌ای پیدا نشد"}</strong><Button type="button" onClick={clearFilters}>پاک کردن فیلترها</Button></div> : null}
  </section>;
}
