# Phase 09 - Integration Handoff

## Demo seed

Phase 09 adds a bounded backend-only demo seed for local UI testing:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.scripts.seed_demo
```

The script is idempotent. It creates the default admin and base catalog when missing, then adds Persian demo catalog rows for legumes, one purchase invoice to populate inventory, and one sale invoice that appears in the daily journal and reports.

Stable demo keys:

- SKUs: `DEMO-BEAN-PINTO`, `DEMO-LENTIL-IR`, `DEMO-CHICKPEA-KSH`
- Purchase note: `PHASE09_DEMO_PURCHASE`
- Sale payment reference: `PHASE09-DEMO-SALE`

The script does not edit frontend files and does not require a migration.
