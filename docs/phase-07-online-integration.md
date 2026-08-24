# Phase 07 - Backend Online Integration

## Scope

Phase 07 adds a backend-only integration layer for online sales channels. No frontend files are changed in this phase.

## Delivered API

Admin endpoints require the normal bearer login token:

- `GET /api/v1/online/channels`
- `POST /api/v1/online/channels`
- `POST /api/v1/online/price-rules`
- `POST /api/v1/online/reservations`
- `GET /api/v1/online/orders`

Online channel endpoints require `X-Online-Token`:

- `GET /api/v1/online/public/catalog`
- `POST /api/v1/online/public/orders`

## Data Model

- `online_channels`: active online channels with a hashed API token.
- `online_price_rules`: per-channel per-variant online prices.
- `stock_reservations`: reserved stock with soft status transitions.
- `online_orders` and `online_order_items`: imported online orders with source identifiers.

## Business Rules

- Public online endpoints are not anonymous; they require an active channel token.
- Channel tokens are hashed at rest and are not returned by admin API responses.
- Online catalog exposes active variants, online price, retail price, and available quantity after reservations.
- Online orders reject duplicate `external_order_id` values per active channel.
- Online order creation reserves stock but does not physically delete or decrement inventory.
- Reservations and orders reject requests when available stock is not enough.
- Jalali dates and local times follow existing validation conventions.

## Acceptance Checks

- Backend tests cover channel auth, online catalog price rules, order creation, reservation side effect, duplicate order rejection, stock shortage rejection, and admin reservation.
- Alembic migration `0005_online_integration_tables` creates the new backend tables.
