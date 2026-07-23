# API runbook — recording orders, arrivals, bench work, exits

Written for an agent (Claude session in `~/learning/device_repair` or elsewhere)
that needs to write to the device ledger without reading the backend source.
Verified against the code 2026-07-22; if a call 400s in a way this doc doesn't
predict, the source under `backend/repairs/` wins.

## Base URL and ground rules

- **Canonical instance: `http://10.20.0.110:8000/api/v1/`** (dock01, LAN-direct
  to Django). The site at `http://repairs.home.arpa` is the same DB's frontend —
  use it to eyeball results, not for API calls (Caddy only proxies the frontend).
- No auth (LAN-only, deliberate for now). JSON in/out; send
  `Content-Type: application/json`. **Trailing slashes required.**
- The site DB is the canonical device ledger (since 2026-07-21). The old
  tracking CSVs are frozen — never "help" by editing them.
- **PII goes in the DB, not in the repo.** Order numbers, seller handles,
  serials, prices all belong in these API payloads — the DB is private. What
  they must never enter is committed seed files in the public repo.
- **Never run seed commands** (`seed_purchases`, `seed_units`, `seed_pricesheet`,
  `seed_reference`) against this DB — they're historical imports and clobber
  post-freeze edits. (`seed_issues` / `seed_repairs` are upsert-safe but still
  not yours to run casually.)
- **No DELETE anywhere** — by design. Corrections are PATCHes.
- Money fields are JSON **strings** of decimals (`"37.87"`); dates are
  `"YYYY-MM-DD"`; datetimes ISO-8601 UTC. Send numbers for money if easier —
  DRF (Django REST Framework) accepts either — but you'll read strings back.
- All detail endpoints accept **PATCH with partial payloads** — send only the
  fields you're changing.
- `ledger_ref` fields are read-only CSV-import keys. Site-created rows leave
  them blank and display as `#<id>` — that's correct, don't try to continue the
  `0004`-style numbering.
- After writing, GET the object back (or load the page) and confirm the state
  you meant to create. Report IDs to Nick so rows are findable.

## Recipe: record an order (the main workflow)

Nick reports something like: *"Ordered 2x DS4 + 1x DS5 on eBay, order
12-34567-89012, $52.50 shipped, seller somehandle."*

**1. Resolve reference IDs** — `GET /options/` → `references` is a light list
of catalog rows (`id`, `brand`, `name`, `sku_prefix`, `model_numbers`),
most-recently-used first. Match the models Nick named; if a unit has no catalog
row, use `reference: null` and put what's known in the device's `notes`.
`options` also carries `sources`, `people` (from_who pool), `locations`,
`statuses`, and recent `purchases` — check it before inventing spellings so
lookups reuse existing rows ("eBay", not "Ebay").

**2. Create the purchase** — `POST /purchases/`

```json
{
  "kind": "device",
  "source": "eBay",
  "order_ref": "12-34567-89012",
  "url": "https://order.ebay.com/ord/show?orderId=12-34567-89012",
  "total_price": "52.50",
  "purchased_on": "2026-07-22",
  "from_who": "somehandle",
  "expected_units": 3,
  "note": "2x DS4 + 1x DS5, untested lot"
}
```

- `source` is free text; the backend get-or-creates the lookup row.
- `kind`: `"device"` (default) or `"parts"`. Parts orders are ledger-only —
  give them a `label` ("DS4 hall module 20-pack"), set `expected_units` to the
  piece count, and **stop here** (no device rows hang off parts purchases).
- `expected_units` matters: it's the unit-price divisor before all device rows
  exist. Set it to what the lot should yield.
- `url` convention: the ORDER page, not the listing (eBay:
  `https://order.ebay.com/ord/show?orderId=<order_ref>`).
- Response includes the new `id` — keep it.

**3. Spawn the device rows** — `POST /inventory/bulk/`

```json
{
  "purchase": 34,
  "status": "shipped",
  "lines": [
    {"reference": 12, "quantity": 2},
    {"reference": 15, "quantity": 1}
  ]
}
```

- Lines carry heterogeneity — one line per model in the lot. ≤100 units total.
- `status: "shipped"` for a fresh order (it's inbound). The arrival call flips
  these later.
- Optional shared `location` / `notes` apply to every spawned row.
- Returns `{"created": 3, "ids": [101, 102, 103]}`.

**4. Mixed-lot pricing (only when Nick states per-unit values)** — the default
is an even split of `total_price`. If the lot is lopsided ("the DS5 was
basically $30 of it"), set that unit's explicit cost:
`PATCH /inventory/103/` `{"cost_override": "30.00"}`. Overridden units take
their cost out of the pot; the rest split the remainder. Don't invent
overrides — no statement from Nick = even split.

**5. Verify** — `GET /purchases/34/` returns the purchase with its `devices`
array and computed `unit_price`. Check unit count and money, then tell Nick the
purchase ID and device IDs (page: `http://repairs.home.arpa/purchases/34`).

## Recipe: the lot arrived

`POST /purchases/<id>/arrive/` with optional `{"date": "YYYY-MM-DD"}` (default
today). Stamps `arrived_on` and flips that lot's `shipped` units to `acquired`
in one stroke; units already past shipped are untouched. Returns
`{"arrived_on": ..., "units_acquired": N}`.

Per-unit facts learned at intake (serial, actual model, condition) go on each
device: `PATCH /inventory/<id>/` with any of `serial`, `reference`, `location`,
`notes`, `status`, `cost_override`, `purchase`.

## Recipe: a unit left (sold / gifted / scrapped…)

`POST /exits/`

```json
{
  "device": 101,
  "kind": "sold",
  "happened_on": "2026-07-25",
  "sale_price": "42.87",
  "fees": "7.10",
  "to_who": "buyerhandle",
  "note": "eBay auction"
}
```

- `kind`: `sold | gifted | parted | scrapped | returned | lost`.
- Creating an exit **auto-flips the device to `exited`** — don't PATCH status
  separately.
- Money fields only make sense on `sold` / `returned` (a return's refund goes
  in `sale_price`); leave null otherwise. `fees` = marketplace fee + outbound
  shipping.
- Corrections: `PATCH /exits/<id>/`.

## Recipe: bench work (repair log)

Usually Nick works this through the UI; use the API when he narrates work to
record.

1. `POST /repairs/` `{"device": 101}` — bench work started. Every new repair
   auto-creates a position-0 "Measurements" note (the bucket for readings tied
   to no specific notation).
2. Phase track: `PATCH /repairs/<id>/` with any of
   `{teardown,wash,repair,reassemble,verify}_done_at` (datetime) and
   `..._note` (deviations only — the routine isn't logged).
3. Notes: `POST /notes/` `{"repair": 7, "position": 1, "title": "...",
   "text": "..."}`; sub-notes via `parent` (one level deep max).
   `PATCH /notes/<id>/` to edit.
4. Measurements: `POST /measurements/` `{"note": 55, "what": "5V rail",
   "value": "4.98V", "comment": ""}`.
5. Done: `PATCH /repairs/<id>/` `{"completed_at": "..."}` — **manual and
   meaningful**: unchecked phases on a completed repair demonstrably did NOT
   happen. A completed repair is frozen (only `completed_at` itself stays
   writable; un-mark it to edit).
6. Device lifecycle is separate: `PATCH /inventory/<id>/`
   `{"status": "in_repair"}` when it hits the bench, `"fixed"` when done —
   repairs never carry status.

## Endpoint reference

| Method + path | Purpose |
|---|---|
| GET `/inventory/` | All devices (label, status, purchase embed, unit_cost) |
| POST `/inventory/` | Create one device (`reference`, `serial`, `location`, `purchase`, `notes`, `status`, `cost_override`) |
| POST `/inventory/bulk/` | Spawn N devices from one purchase (lines) |
| GET/PATCH `/inventory/<id>/` | Device detail (repairs, notes, exits nested) / edit device fields |
| GET `/purchases/` | Buy events, newest first |
| POST `/purchases/` | Record a purchase |
| GET/PATCH `/purchases/<id>/` | Purchase + its `devices` array / edit purchase fields |
| POST `/purchases/<id>/arrive/` | Stamp arrival, flip shipped→acquired |
| POST `/exits/` | Record a departure (flips device to exited) |
| PATCH `/exits/<id>/` | Correct an exit |
| POST `/repairs/` · PATCH `/repairs/<id>/` | Start repair · phase track/completion |
| POST `/notes/` · PATCH `/notes/<id>/` | Bench notes (one-level nesting) |
| POST `/measurements/` · PATCH `/measurements/<id>/` | Readings on a note |
| GET `/reference/` | Full price-sheet catalog (comps, issues, variants) |
| GET `/lanes/` | Category lanes |
| GET `/options/` | Lookup pools: references, sources, people, locations, statuses, recent purchases |
| GET `/cash/` | `money_out` / `money_in` / `net` + counts |

## Enums

- **Device.status**: `shipped` (inbound) → `acquired` → `in_repair` → `fixed` →
  `exited`. Manually set except the two automatic flips (arrive, exit).
- **Purchase.kind**: `device`, `parts`.
- **Exit.kind**: `sold`, `gifted`, `parted`, `scrapped`, `returned`, `lost`.
- **Repair phases** (in order): `teardown`, `wash`, `repair`, `reassemble`,
  `verify`. Each has `_done_at` + `_note` columns on the repair.
