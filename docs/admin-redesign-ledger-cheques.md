# Admin redesign: ledger and cheques

## Scope

This slice turns the existing ledger and cheque MVP into a Persian, RTL, beginner-friendly admin workflow. It must preserve the current FastAPI, SQLAlchemy/SQLite, React, and Material UI patterns.

## Current contracts

- People: create and list active customers/suppliers.
- Ledger: list one person's entries, create a manual debit/credit entry, and settle open entries oldest-first.
- Cheques: create received/paid cheques, list them, and append cleared/bounced/canceled lifecycle events.
- Dues: list open ledger entries and pending cheques up to a Jalali date.

## Confirmed gaps

- Both screens still use the early raw HTML forms and have no complete loading, empty, error, retry, saving, or field-validation states.
- Ledger selection does not explain whether the net balance is debtor, creditor, or settled; it has no search, person summary, source/status labels, or mobile-friendly transaction cards.
- Person creation, manual entries, and settlements do not surface request errors safely. Settlement amount is not checked against the visible balance before submission.
- Cheques have no filters, KPI/overdue summary, Persian status labels, event history, action confirmation, action-time date/note, or disabled state for terminal actions.
- Cheque issue/due ordering is not validated. Repeating or reversing lifecycle events is only partly constrained by the backend.
- `GET /cheques` and `GET /dues` are available but not filterable; client-side filtering is acceptable for the current data size.
- Automatic ledger posting from sales/purchases and automatic settlement from cleared cheques remain explicitly out of this UI slice unless implemented with focused tests and a clear migration-safe rule.

## Deliverable A: ledger and people

- Responsive MUI workspace with person search/selection and a clear debtor/creditor/settled balance card.
- Create-person dialog/form with Persian validation and saving/error feedback.
- Manual debit/credit entry and settlement forms with Jalali date, money parsing, explanatory copy, and safeguards against zero/over-settlement.
- Transaction timeline/cards with Persian labels for type, status, and source; newest-first presentation without changing accounting semantics.
- Loading, empty, filtered-empty, error/retry, and success states.

## Deliverable B: cheques and dues

- KPI cards for pending received, pending paid, overdue/near-due, and total pending value.
- Search plus type/status/due filters; responsive cards with person, bank, number, amount, due date, and Persian state.
- Controlled create form with validation: required bank/number, positive amount, valid Jalali dates, and due date not earlier than issue date.
- Lifecycle dialog for cleared/bounced/canceled with action date, optional note, confirmation, saving state, and backend error feedback.
- Event history available without crowding the primary card.
- Dues view or section driven by the existing cutoff-date endpoint.

## Acceptance checks

- Targeted backend tests and the full backend suite pass.
- TypeScript and production build pass.
- No destructive browser action or financial submission is finalized during QA without confirmation; API tests cover those mutations.
- Desktop and 390px mobile QA cover loading, populated, empty/filter-empty, validation, dialog, and retry behavior.
- At 390px there is no horizontal document overflow, clipped action, overlapping card, or control smaller than 44px.
- No merge or push to `main`; the parent agent reviews and commits only on the feature branch.

## Manual test

1. Open **دفتر حساب**, create one person of type **هر دو**, then add one debit and one credit document.
2. Select that person and verify the debit, credit, and net balance cards; enter a settlement above either side and confirm the submit action stays disabled.
3. Register a smaller settlement for one side and verify only the oldest open entries on that side are reduced.
4. Open **چک‌ها**, enter a due date before the issue date, and verify the form blocks submission with a Persian error.
5. Expand a cheque history, open a lifecycle action, verify the date/note confirmation dialog, then cancel it without saving.
6. Repeat the ledger selection, cheque filters, history, and dialog checks at `390 × 844`; confirm there is no document-level horizontal overflow or clipped action.

The valid cheque state machine is `pending → cleared | bounced | canceled` and `bounced → cleared | canceled`; cleared and canceled states are terminal, and event timestamps cannot move backward.
