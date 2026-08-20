# Phase 03: Sales MVP Backend

## Goal

Phase 03 adds the backend contract for daily sale invoices, mixed payments, cancellation, and the daily journal. It does not implement frontend screens, purchases, inventory, ledger posting, or cheque lifecycle workflows.

## Backend Contract

Protected endpoints under `/api/v1`:

```text
POST /sales
GET  /sales
GET  /sales/{id}
POST /sales/{id}/cancel
GET  /daily-journal?jalali_date=1405/05/29
```

Core records:

- `SaleInvoice`: active or canceled sale with `subtotal_rial`, `discount_amount_rial`, `total_rial`, `paid_total_rial`, `due_total_rial`, and `is_active`.
- `SaleInvoiceItem`: sold product variant snapshot with positive quantity, item discount, line total, estimated cost, and estimated profit.
- `Payment`: invoice-linked payment with method, status, amount, and local date/time.

Payment methods are `cash`, `card`, `transfer`, `credit`, `cheque`, and `voucher`.
`cash`, `card`, and `transfer` default to `received`; `credit`, `cheque`, and `voucher` default to `pending` unless a request explicitly sets `status` to `received`.

## Business Rules

- `jalali_date` must use `1405/05/29` format and `local_time` must use `09:30` format.
- Sale payloads must include at least one item and every item quantity must be greater than zero.
- Invoice subtotal is calculated from item quantity times unit price.
- Item discount is subtracted before invoice-level discount.
- Invoice total is `subtotal_rial - discount_amount_rial` and cannot be negative.
- Canceled invoices keep their records but are excluded from daily journal totals.
- Payments for canceled invoices are also excluded from daily journal totals.

## Acceptance

- Creating a sale returns computed invoice totals, item totals, and default payment statuses.
- The daily journal separates received and pending payments.
- Canceling a sale changes invoice status to `canceled` and removes it from journal totals.
- Bad Jalali date, bad local time, empty item list, zero payment amount, and negative invoice total are rejected.
