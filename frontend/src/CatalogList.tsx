import { useState } from "react";
import { IconButton, Menu, MenuItem, ListItemIcon } from "@mui/material";
import EditRounded from "@mui/icons-material/EditRounded";
import MoreVertRounded from "@mui/icons-material/MoreVertRounded";
import ImageRounded from "@mui/icons-material/ImageRounded";
import AddPhotoAlternateRounded from "@mui/icons-material/AddPhotoAlternateRounded";
import DeleteOutlineRounded from "@mui/icons-material/DeleteOutlineRounded";
import { apiAssetUrl, type Category, type Product, type ProductVariant, type Unit } from "./api";
import { formatRial, toPersianDigits } from "./numberUtils";
import "./catalog.css";

type Props = {
  variants: ProductVariant[];
  products: Product[];
  categories: Category[];
  units: Unit[];
  isSuperuser: boolean;
  onEdit: (item: ProductVariant) => void;
  onImage: (variant: ProductVariant) => void;
  onDeactivate: (item: ProductVariant) => void;
};

export function CatalogList({ variants, products, categories, units, isSuperuser, onEdit, onImage, onDeactivate }: Props) {
  const [menu, setMenu] = useState<{ anchor: HTMLElement; variant: ProductVariant } | null>(null);
  const productById = new Map(products.map((item) => [item.id, item]));
  const categoryById = new Map(categories.map((item) => [item.id, item.name]));
  const unitById = new Map(units.map((item) => [item.id, item.name]));
  return <>
    <table className="catalog-table" aria-label="فهرست کالاها">
      <thead><tr><th>کالا / کد</th><th>دسته‌بندی</th><th>واحد</th><th>قیمت فروش</th><th>قیمت عمده</th><th>عملیات</th></tr></thead>
      <tbody>{variants.map((variant) => {
        const product = productById.get(variant.product_id);
        return <tr className="catalog-product-card" key={variant.id}>
          <td className="catalog-name"><div className="catalog-identity"><span className="catalog-thumbnail">{variant.image_url ? <img src={apiAssetUrl(variant.image_url) ?? undefined} alt="" loading="lazy" /> : <ImageRounded />}</span><div><strong>{variant.name}</strong>{variant.sku && <small>{toPersianDigits(variant.sku)}</small>}</div></div></td>
          <td className="catalog-category">{categoryById.get(product?.category_id ?? -1) ?? "بدون دسته‌بندی"}</td>
          <td className="catalog-unit">{unitById.get(variant.unit_id) ?? "واحد نامشخص"}</td>
          <td className="catalog-retail"><span className="catalog-mobile-label">فروش </span>{formatRial(variant.retail_price_rial)}</td>
          <td className="catalog-wholesale"><span className="catalog-mobile-label">عمده </span>{variant.wholesale_price_rial == null ? "—" : formatRial(variant.wholesale_price_rial)}</td>
          <td className="catalog-actions"><IconButton aria-label="ویرایش" title="ویرایش" onClick={() => onEdit(variant)}><EditRounded fontSize="small" /></IconButton>{isSuperuser && <IconButton aria-label="عملیات کالا" title="عملیات کالا" aria-haspopup="menu" aria-expanded={menu?.variant.id === variant.id || undefined} onClick={(event) => setMenu({ anchor: event.currentTarget, variant })}><MoreVertRounded fontSize="small" /></IconButton>}</td>
        </tr>;
      })}</tbody>
    </table>
    <Menu anchorEl={menu?.anchor} open={Boolean(menu)} onClose={() => setMenu(null)}>
      {menu && <MenuItem onClick={() => { onImage(menu.variant); setMenu(null); }}><ListItemIcon><AddPhotoAlternateRounded fontSize="small" /></ListItemIcon>{menu.variant.image_url ? "تعویض عکس" : "افزودن عکس"}</MenuItem>}
      <MenuItem sx={{ color: "error.main" }} onClick={() => { if (menu) onDeactivate(menu.variant); setMenu(null); }}><ListItemIcon><DeleteOutlineRounded color="error" fontSize="small" /></ListItemIcon>غیرفعال</MenuItem>
    </Menu>
  </>;
}
