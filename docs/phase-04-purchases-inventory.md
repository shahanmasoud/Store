# Phase 04: Purchases And Inventory

## Goal

Phase 04 adds the backend foundation for purchase invoices, purchase lots, inventory balances, inventory transactions, and weighted-average costing.

## Backend Contract

Protected endpoints under `/api/v1`:

```text
POST /purchase-invoices
GET  /purchase-invoices
GET  /purchase-invoices/{id}
POST /purchase-invoices/{id}/cancel
GET  /inventory
```

Core records:

- `PurchaseInvoice`: purchase header with Jalali date/time, payment totals, status, and soft cancellation.
- `PurchaseInvoiceItem`: purchased variant, quantity, unit cost, extra item cost, and line total.
- `PurchaseLot`: cost snapshot created from each purchase item.
- `InventoryItem`: current quantity and weighted-average cost per product variant.
- `InventoryTransaction`: audit trail for purchase entry and purchase cancellation.

## Business Rules

- `jalali_date` uses `1405/06/01` format and `local_time` uses `10:15` format.
- Purchase payloads must include at least one item and positive item quantities.
- Purchase total is `subtotal_rial + extra_cost_rial - discount_amount_rial` and cannot be negative.
- Creating a purchase creates purchase lots, inventory transactions, and updates inventory.
- Weighted average cost is recalculated after purchase entry.
- Canceling a purchase is soft-only and reverses inventory when enough stock remains.
- Canceling fails with `409` if stock is insufficient.

## Acceptance

- Creating a purchase creates invoice, item, lot, inventory item, and transaction records.
- A second purchase recalculates weighted-average cost.
- Canceling a purchase reverses inventory and marks the invoice inactive/canceled.
- Bad dates, bad times, empty item lists, and insufficient stock cancellation are rejected.
