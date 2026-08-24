# Phase 06 - Reports and Analytics Backend

## Scope

Phase 06 adds backend reporting endpoints for management dashboards without touching the frontend branch.

## Delivered API

- `GET /api/v1/reports/sales-summary`
- `GET /api/v1/reports/profit-loss`
- `GET /api/v1/reports/inventory`
- `GET /api/v1/reports/cashflow`
- `GET /api/v1/reports/customer-debts`

All endpoints require authentication and return structured JSON contracts for the React UI.

## Business Rules

- Sales reports exclude canceled and inactive invoices.
- Sales summary separates received and pending payments.
- Profit and loss uses final invoice totals after invoice-level discounts and recorded estimated costs.
- Inventory report exposes on-hand quantity, weighted average cost, stock value, and reorder flags.
- Cashflow combines pending sale payments, net open ledger balances, pending received cheques, and pending paid cheques.
- Customer debt report includes open debit ledger entries only.

## Acceptance Checks

- Backend report contract tests cover sales summary, profit/loss, inventory valuation, cashflow, customer debts, and Jalali date validation.
- No frontend files are changed in this phase to avoid conflicts with the active UI branch.
