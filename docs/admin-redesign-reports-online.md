# Admin redesign: reports and online operations

## Scope

This slice completes the remaining operational admin surfaces: management reports and online-channel monitoring/configuration. It keeps the current React, Material UI, FastAPI, SQLAlchemy, and SQLite architecture and the Persian RTL visual system.

## Current contracts

- Reports provide sales summary, estimated profit/loss, inventory valuation, expected cashflow, and customer debts.
- Online integration provides channels, per-channel price rules, manual reservations, online catalog/order ingestion, and admin order listing.
- Public online requests authenticate with a hashed-at-rest channel token; admin requests use the normal bearer login.

## Confirmed report gaps

- The current page only renders nine scalar metrics; inventory rows, low-stock items, debtors, cashflow components, and useful comparisons are discarded.
- Initial loading is visually indistinguishable from missing data, and there are no empty, error/retry, partial-failure, refresh, or last-updated states.
- Date range ordering is not validated in the client before five requests are sent.
- All five requests fail as one `Promise.all`, hiding reports that did load successfully.
- The layout has no responsive detail cards/tables and no accessible visual hierarchy for positive/negative values.
- `customer-debts` currently sums open debit rows without offsetting the same person's open credit rows, so a customer can be shown as owing more than their net balance.
- Reports must distinguish scheduled pending payment rows from the invoice's full `due_total_rial`; an unassigned unpaid remainder must not silently disappear from receivables/cashflow.

## Report deliverable

- Controlled Jalali range with validation and an explicit refresh action.
- Loading skeleton/progress, error with retry, empty state, and safe partial results.
- Clear KPI groups for sales, collection, profit/margin, stock value, and expected cashflow.
- Component breakdowns for cashflow, low-stock inventory, and customer debts using responsive cards on mobile.
- Customer debt is calculated per person as net open debit minus open credit, clamped at zero; supplier credit remains a separate cashflow obligation.
- Avoid decorative charts unless the relationship is genuinely clearer than compact cards/bars.

## Confirmed online gaps

- The current UI only creates channels and shows minimal channel/order text. It does not expose admin price rules or manual stock reservations despite existing POST APIs.
- There are no list endpoints for price rules/reservations, so administrators cannot verify what they configured.
- Expired reservations remain counted forever because availability only checks `status=reserved` and ignores `expires_jalali_date`.
- Channel tokens need password-style entry, explicit minimum-length guidance, and a warning that the plaintext token is not recoverable from the server.
- Orders lack channel/status search, item details, localized states, loading/error/empty states, and mobile-safe cards.

## Online deliverable

- Channel creation with controlled secret input, validation, saving/error/success states, and safe explanatory copy.
- Admin list/filter endpoints for active online price rules and stock reservations, plus typed frontend clients.
- Reservation availability must ignore/expire reservations whose Jalali expiry is before the effective current/request date; behavior must be deterministic and tested.
- MUI tabs or sections for channels, price rules, reservations, and orders; each has loading, empty/filter-empty, error/retry, and responsive cards.
- Price-rule date ordering and positive-price validation; reservation channel/variant/quantity/expiry validation.
- Order detail expansion with localized status, channel, customer, totals, dates, and line items. Order state mutation/conversion is out of scope unless a tested backend contract is introduced.

## Cross-cutting date requirement

- Replace the hard-coded `DEFAULT_JALALI_DATE` with a runtime Tehran/Persian-calendar date helper. All sale, purchase, ledger, cheque, report, and online defaults must reflect the actual current local date.

## Acceptance checks

- Targeted and full backend tests, TypeScript, and production build pass.
- Desktop and 390px mobile QA cover each section, filters, details, loading, empty, error/retry, and validation; no horizontal document overflow or clipped controls.
- Do not reveal stored token hashes or persist plaintext tokens in browser storage.
- Browser QA must not submit a channel token, reservation, online order, or other consequential form without action-time confirmation; automated API tests cover mutations.
- No merge or push to `main` before review in the original chat.

## Implemented contracts

- `GET /api/v1/online/price-rules` lists active rules and accepts optional `channel_id` and `variant_id` filters.
- `GET /api/v1/online/reservations` lists active rows and accepts optional `channel_id`, `variant_id`, `status`, and read-only `as_of_jalali_date` filters. The response includes a computed `is_expired` flag.
- Stock availability always uses the server's current Tehran/Jalali date. A caller-supplied order date can select a dated price rule, but cannot bypass a currently active reservation.
- Cashflow reports expose scheduled sale payments, unallocated invoice debt, customer ledger receivables, supplier ledger obligations, received cheques, and paid cheques as separate components.
- Customer debts net each customer's open debit and credit rows before clamping the result at zero; people of type `both` participate on the appropriate side.
- Runtime Persian-calendar helpers now provide Tehran dates for all admin forms instead of a frozen constant.

No database schema change was required for this slice.

## Manual review checklist

1. Open **گزارش‌ها**, reverse the date range, and verify that validation prevents network refresh. Restore the range and verify KPI, cashflow, low-stock, and debtor sections.
2. During a simulated single report failure, verify the warning and retry action while successful sections remain available and failed data is not shown as stale.
3. Open **عملیات آنلاین** at desktop and 390px widths. Visit all four tabs and verify each loading, empty/filter-empty, error/retry, and populated layout without horizontal document overflow.
4. In the channel form, verify the 16-character validation, password masking, show/hide action, and non-recoverability guidance. Do not submit a real secret during browser QA.
5. In price and reservation forms, verify required fields, positive numeric values, reversed date validation, and expired-reservation validation without submitting consequential data.
6. Filter orders by text, channel, and status; expand one order and verify customer, date, totals, discount, and line items remain legible at 390px.
