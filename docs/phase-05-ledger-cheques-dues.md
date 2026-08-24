# Phase 05: Ledger, Cheques, And Due Reminders

## Summary

Phase 05 adds the backend MVP for people, manual ledger entries, settlements, cheques, and due reminders. It intentionally stays independent from sales and purchases automation; those flows can create ledger entries in a later integration pass.

## Backend Contracts

- `POST /api/v1/persons`, `GET /api/v1/persons`
- `GET /api/v1/ledger/persons/{person_id}`
- `POST /api/v1/ledger/manual-entry`
- `POST /api/v1/settlements`
- `GET /api/v1/dues?jalali_date_to=1405/06/30`
- `POST /api/v1/cheques`
- `POST /api/v1/cheques/{id}/events`
- `GET /api/v1/cheques`

## Rules

- Jalali dates use `1405/06/30` format and local times use `09:30` format.
- Money amounts must be positive.
- Settlements consume oldest open ledger entries first.
- Settlements over the open balance return `409`.
- Cheques start as `pending` with a `created` event.
- Cheque events update status; canceling a cheque also sets `is_active=false`.

## Known Gaps

- Sales and purchase invoices do not auto-create ledger entries yet.
- Cheque clearing does not auto-create settlements yet.
- Frontend screens for ledger and cheques are planned for the UI pass.
