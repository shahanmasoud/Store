# Phase 02: Core Data And Catalog

## Goal

Phase 02 builds the shared data foundation for sales, purchases, inventory, pricing, and future online catalog APIs.

## Backend Contract

Protected catalog endpoints under `/api/v1`:

```text
GET  /units
POST /units
GET  /categories
POST /categories
GET  /products
POST /products
GET  /product-variants
POST /product-variants
POST /prices
POST /price-rules
```

Core records:

- `Unit`: measurement units such as kilogram.
- `Category`: multi-level category tree with `parent_id`.
- `Product`: base product such as rice or beans.
- `ProductVariant`: sellable item such as Iranian Tarem rice.
- `PriceList`: dated retail, wholesale, or online price record.
- `PriceRule`: quantity-based discount or wholesale rule.

## Time Contract

Financial and pricing records keep both technical and display time fields:

- `occurred_at_utc` for sorting, API safety, and future online use.
- `jalali_date` in `1405/05/29` format for user-facing filters.
- `local_time` in `09:30` format for daily journal and invoices.
- `timezone` fixed to `Asia/Tehran` unless a future migration changes it.

## Acceptance

- Catalog endpoints require authentication.
- Unit, category, product, variant, and price records can be created through API.
- Bad Jalali date input is rejected with validation error.
- Seed command creates admin plus basic catalog sample data without duplicating rows.
- Alembic has an initial migration for users and catalog core tables.
