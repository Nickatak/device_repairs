# device_repair_website

The operations system for the device-repair venture — **two surfaces, one database.**

- **Admin surface (Nick only)** — the working system: the **reference/price sheet**
  (model catalog + comp pulls + stop prices, absorbing `~/learning/device_repair/references/prices.md`),
  the **ledger** (purchases → units → exits, absorbing the tracking CSVs), and the
  **repair log** (repairs → steps → measurements → media). Single source of truth once
  migrated; the markdown/CSV layer retires as each piece goes live.
- **Guest surface (unauthenticated, link-only)** — per-device share links, no accounts,
  no browse/index. Two uses of the same mechanism: a customer sees the work/media on
  *their* device; a B2B prospect gets sent any device's link as proof. Read-only,
  curated projection: bench narrative + media, **never** money fields (acquisition,
  comps, stops, sale, fees) or people.

Explicitly **not** in scope: storefront/marketing layer, case studies, intake funnel,
customer accounts. The old "trust-asset storefront" framing is dead (2026-07-21).

## Domain shape (summary — detail in `docs/domain.md`)

**Purchase** (transaction grain: order #, source, cost, qty — lots split to units on
arrival) → **Device** (progressively identified: category → exact model → board rev;
lifecycle status `lead → shipped → acquired → … → sold/parted/scrapped/gifted/lost`;
nullable `owner` / `sold_to` → Person) → **Repair** → **Step** (the spine) →
Measurements / Parts / Media. **Catalog entry** (reference identity per model) ←
append-only **comp pulls** + hand-set stop price; lane-level policy as text.

## Build order

1. **Price sheet first** — catalog + comp pulls + stops. Everything else depends on it.
2. Ledger (purchases/units/exits) + reconciliation checks.
3. Guest share-links + media.

## Stack

- **Backend:** Django + DRF (Django REST Framework), Postgres
- **Frontend:** Next.js
- **Layout:** monorepo, `backend/` + `frontend/`

Single-user admin (no auth until it's exposed beyond the LAN); guest links are
capability URLs (unguessable tokens). Private data lives in this tree's database —
treat the repo/database as **private**.
