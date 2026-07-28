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
  post-freeze edits. (`seed_issues` / `seed_repairs` / `seed_parts` /
  `seed_revisions` / `seed_stock` are upsert-safe but still not yours to run
  casually — `seed_stock` in particular would revert live counts to the
  2026-07-23 import bases.)
- **No DELETE anywhere** — by design. Corrections are PATCHes.
- Money fields are JSON **strings** of decimals (`"37.87"`); dates are
  `"YYYY-MM-DD"`; datetimes ISO-8601 UTC. Send numbers for money if easier —
  DRF (Django REST Framework) accepts either — but you'll read strings back.
- All detail endpoints accept **PATCH with partial payloads** — send only the
  fields you're changing.
- `ledger_ref` fields are read-only CSV-import keys. Site-created rows leave
  them blank and display as `#<id>` — that's correct, don't try to continue the
  `0004`-style numbering.
- Devices carry a read-only `touched_at` — last edit anywhere in the unit's
  tree (device fields, device notes, repairs and their notes / measurements /
  parts / photos, exits, the arrival flip). Bumped server-side on every write;
  never write it yourself. Note it bumps on ANY successful PATCH, including a
  no-op — don't "verify" with a write.
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
- Optional shared `location` applies to every spawned row; optional shared
  `notes` becomes each unit's FIRST device-note chunk (see "device notes").
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
`status`, `cost_override`, `purchase`. Prose facts go through device notes
(below) — a PATCH sending `notes` 400s since 2026-07-27.

## Recipe: device notes (unit-grain facts)

Since 2026-07-27 device notes are CHUNKS, not one blob — same shape as repair
notes: entries accrete, each dated, each can carry photos. Unit-grain facts
("uses a 19V brick", colorway questions, intake condition) live here; bench
observations still belong on a Repair's notes.

- **Add a chunk**: `POST /device-notes/` `{"device": 147, "position": 1,
  "title": "", "text": "rev read: JDM-055"}`. `position` orders the page
  (ties resolve by id, so equal positions read in creation order).
- **Edit a chunk**: `PATCH /device-notes/<id>/` (partial). No DELETE, as
  everywhere.
- **Photos** attach per chunk: `POST /media/` multipart with `device_note=<id>`
  (instead of `note`/`repair`). This is the home for intake/listing shots that
  predate any repair; the completed-repair freeze never applies here.
- Device create sugar: `POST /inventory/` and `POST /inventory/bulk/` still
  accept a `notes` string — it spawns the unit's first chunk (position 0).
- Read side: the device detail payload carries `device_notes` (chunks with
  `media` arrays); the inventory LIST payload's `notes` field still exists but
  is now read-only — all chunks flattened to one string for search/display.

## Recipe: parts stock (buckets, intakes, recounts)

Stock buckets are minted SKUs at consumption grain, in two tracking tiers
(`mode`): `counted` (transactional — intakes add, bench-Part draws subtract,
recounts override; live `count` is derived server-side) and `presence`
(have/low/out by eyeball; `state` field, no arithmetic). Compatibility rides
`fits_references` / `fits_revisions` (ids) plus the free-text `note`.

- When a **parts order arrives** and Nick says which bucket(s) it fills:
  `POST /stock/intakes/` `{"purchase": <parts purchase id>, "stock_item": <id>,
  "quantity": N}` — device-kind purchases are rejected. One purchase can feed
  several buckets. Also stamp the purchase arrival (arrive endpoint or PATCH).
- **Physical recount**: `POST /stock/<id>/recount/` `{"count": N}` — sets the
  new base and stamps `counted_at` server-side. This is the ONLY way the count
  is set directly; never try to PATCH a count.
- **Presence state**: PATCH `/stock/<id>/` `{"state": "low"}` (in_stock | low |
  out) when Nick reports a bin running dry.
- New bucket: `POST /stock/` with `name`, `category`, `mode`, optional fits
  id arrays and `note`. Don't mint buckets on your own initiative — bucket
  grain and tier are Nick's design calls; ask when a new part class shows up.

## Recipe: board-revision knowledge (rev quirks, ID tells)

Revisions (JDM-040, BDM-020…) live on catalog rows and are the one writable
catalog layer — the rest of the reference sheet still edits through Django
admin. When bench work surfaces a rev-level fact (a quirk like the JDM-040
no-battery boot loop, an ID tell, an open question resolved):

- **Accrete onto an existing rev**: `GET /reference/` → find the rev's `id`
  under its catalog row → `PATCH /revisions/<id>/` `{"note": "<full updated
  text>"}`. PATCH replaces the field — send the whole note, existing content
  plus the new dated line, not just the addition.
- **New rev crossed the bench**: `POST /revisions/`
  `{"reference": <catalog row id>, "name": "JDM-060", "note": "…", "position": N}`.
- The split DS4 refs (30 v1 / 31 v2 / 149 hall-exit-class) duplicate rev sets
  by design — a quirk belongs on the repair-lane row's rev (30/31); mirror to
  149 only if it changes exit pricing/handling. No delete endpoint by design.
- Unit-grain observations ("THIS unit boot-loops") stay bench notes on the
  repair; only rev-wide knowledge goes here.

## Recipe: note templates (config, NOT ledger)

One prefill per (catalog model × phase) — what the add-note modal offers
("Hall Mod" on the DS4 hall class × Repair). Authoring lives at
`http://repairs.home.arpa/templates`; API:

- `GET /templates/` (optional `?reference=<id>`) · `POST /templates/` with
  nested `entries` (each: `position`, `title`, `text`, `measurements` of
  `{position, what, expected}`). One per (reference, phase) — a second 400s.
- `PATCH /templates/<id>/` — nested `entries` REPLACE the existing set.
- `DELETE /templates/<id>/` — the ONE delete in the API: templates are
  config; notes already spawned from one are untouched.
- Applying a template is nothing special server-side: the modal just POSTs
  plain notes (with nested measurements) — the log never references the
  template.

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
   auto-creates a position-0 "Measurements" note on the Diagnostics phase
   (the bucket for readings tied to no specific notation).
2. Phase track: `PATCH /repairs/<id>/` with any of
   `{intake,teardown,diagnostics,repair,wash,reassemble,verify}_done_at`
   (datetime). The old per-phase `..._note` text columns are GONE
   (2026-07-28) — phase prose is a step Note on that phase.
3. Notes are PER-PHASE (2026-07-28): `POST /notes/` `{"repair": 7,
   "phase": "diagnostics", "position": 1, "title": "...", "text": "..."}` —
   `phase` is REQUIRED on create; sub-notes via `parent` (one level deep max,
   they inherit the parent's phase). Optional create-only `measurements`
   array (`[{"what": "1.1V rail", "value": "1.09 V"}]`) lands rows on the new
   note in one request. `PATCH /notes/<id>/` to edit (no nested measurements
   on edit — use `/measurements/`).
4. Measurements: `POST /measurements/` `{"note": 55, "what": "5V rail",
   "value": "4.98V", "comment": ""}`.
5. Done: `PATCH /repairs/<id>/` `{"completed_at": "..."}` — **manual and
   meaningful**: unchecked phases on a completed repair demonstrably did NOT
   happen. A completed repair is frozen (only `completed_at` itself stays
   writable; un-mark it to edit).
6. Device lifecycle is separate: `PATCH /inventory/<id>/` with the bench-split
   statuses — `disassembled_diagnosing` when it's opened on the desk (then
   `_parts` / `_solder` as the diagnosis lands), `reassembled_untested` when
   the shell closes, `awaiting_exit` when bench work is over — repairs never
   carry status.

## Recipe: photos on a note (or repair)

`POST /media/` — **multipart**, not JSON: `image` (the file) + `caption`
(optional) + exactly one of `note` / `repair` / `device_note` (id). One photo
per row; loop for a batch.

```
curl -X POST <base>/media/ -F "note=55" -F "caption=lifted pad, pre-bodge" \
  -F "image=@IMG_1234.jpg"
```

- Server-side on every upload: **GPS EXIF is stripped** from the stored file
  (Nick's 2026-07-24 call — bench photos carry home coordinates); device
  make/model and datetime tags are kept. `taken_at` is extracted from EXIF
  DateTimeOriginal (UTC; bench-local America/Los_Angeles assumed when the
  camera wrote no offset) — null means the file had no EXIF timestamp, and
  `created_at` (upload stamp) is the fallback chronology.
- Phone→upload handoff must be a raw-file path (direct upload, USB, email
  attachment). Messenger pipelines re-encode and strip EXIF → every photo
  lands `taken_at: null`.
- `PATCH /media/<id>/` corrects `caption` or reparents (`note`/`repair`). The
  image file itself is immutable — a better photo is a new row. No DELETE,
  same as the rest of the log.
- Media rides the device payload: each note (and the repair) carries a `media`
  array; `image` is a relative `/media/...` URL served through the frontend's
  same-origin proxy.
- Completed repairs are frozen — uploads against them 400.

## Endpoint reference

| Method + path | Purpose |
|---|---|
| GET `/inventory/` | All devices (label, status, purchase embed, unit_cost, touched_at) |
| POST `/inventory/` | Create one device (`reference`, `serial`, `location`, `purchase`, `status`, `cost_override`; `notes` spawns the first chunk) |
| POST `/inventory/bulk/` | Spawn N devices from one purchase (lines) |
| GET/PATCH `/inventory/<id>/` | Device detail (repairs, device_notes, exits nested) / edit device fields |
| POST `/device-notes/` · PATCH `/device-notes/<id>/` | Unit-fact chunks on a device (add / edit, no delete) |
| GET `/purchases/` | Buy events, newest first |
| POST `/purchases/` | Record a purchase |
| GET/PATCH `/purchases/<id>/` | Purchase + its `devices` array / edit purchase fields |
| POST `/purchases/<id>/arrive/` | Stamp arrival, flip shipped→acquired |
| POST `/exits/` | Record a departure (flips device to exited) |
| PATCH `/exits/<id>/` | Correct an exit |
| POST `/repairs/` · PATCH `/repairs/<id>/` | Start repair · phase track/completion |
| POST `/notes/` · PATCH `/notes/<id>/` | Bench notes — per-phase, `phase` required on create (one-level nesting; create-only nested `measurements`) |
| GET/POST `/templates/` · GET/PATCH/DELETE `/templates/<id>/` | Note templates per (model × phase) — config, deletable |
| POST `/measurements/` · PATCH `/measurements/<id>/` | Readings on a note |
| POST `/media/` · PATCH `/media/<id>/` | Photo upload (multipart, parent = note/repair/device_note; GPS-stripped, EXIF taken_at) · caption/reparent |
| GET/POST `/stock/` | Buckets with live counts / mint a SKU |
| GET/PATCH `/stock/<id>/` | Bucket detail / identity + state edits (never count) |
| POST `/stock/<id>/recount/` | Physical recount: new base + stamp |
| POST `/stock/intakes/` · PATCH `/stock/intakes/<id>/` | Units entering a bucket from a parts purchase |
| GET `/reference/` | Full price-sheet catalog (comps, issues, variants, revisions) |
| POST `/revisions/` · PATCH `/revisions/<id>/` | Board revisions on a catalog row (`reference`, `name`, `note`, `position`) — the one writable catalog layer |
| GET `/lanes/` | Category lanes |
| GET `/options/` | Lookup pools: references, sources, people, locations, statuses, recent purchases |
| GET `/cash/` | `money_out` / `money_in` / `net` + counts |

## Enums

- **Device.status** (bench split 2026-07-24): `shipped` (inbound) → `acquired` →
  the **Disassembled family** `disassembled_diagnosing` / `disassembled_parts` /
  `disassembled_solder` → `reassembled_untested` → `awaiting_exit` (renamed
  from `reassembled_tested` 2026-07-28 — a pipeline position, NOT a quality
  claim: a unit awaiting a scrap exit sits here too) →
  `exited`. Disassembled = physically open on Nick's desk; the sub-state names
  what the unit is WAITING FOR (diagnosis / parts to go in / solder work), not
  whether it's blocked. Re-assembled = shell closed; `tested` is the old
  "fixed". A force-parked unit (shell closed mid-repair) leaves the
  Disassembled family and its pending work lives in notes. Manually set except
  the two automatic flips (arrive, exit).
- **Purchase.kind**: `device`, `parts`.
- **Exit.kind**: `sold`, `gifted`, `parted`, `scrapped`, `returned`, `lost`.
- **Repair phases** (in order, reworked 2026-07-28): `intake` (as-received
  function test, before the shell opens), `teardown`, `diagnostics` (fault
  isolation on the open unit), `repair`, `wash` (post-solder cleanup — after
  repair, before the shell closes), `reassemble`, `verify`. Each has a
  `_done_at` column on the repair; prose goes in per-phase step Notes.
