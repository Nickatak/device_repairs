# Price sheet — design record

The website's copy of `~/learning/device_repair/references/prices.md`, built 2026-07-21.
This is **build-order step 1** of the re-scope (see `README.md`): the reference/price
layer lands first because the ledger and guest surfaces both hang off the catalog.

prices.md stays canonical until the **updating pipelines** exist and Nick is
comfortable with them (his call, 2026-07-21) — a sheet you can't conveniently update is
a museum, not a tool. Until then, new comp pulls land in prices.md as before; the site
re-syncs via the seed JSON. After the flip, the website is the single source of truth
and prices.md retires (a breadcrumb pointing here replaces it).

## Model

Three pieces, extending the existing `DeviceReference` catalog rather than replacing it:

### Lane (new lookup)

The price sheet's category grain — `monitor`, `console`, `controller`, `handheld`,
`laptop`, `gpu`, `cpu`, `psu`, `keyboard`, `networking`, `ecu`, `test-equipment`,
`phone`, … Replaces `DeviceReference.Category` (a 4-value enum) with the same
free-text-lookup pattern Make/Source/DeviceModel use: adding a lane is a row, not a
migration.

- `name` — the identity, lowercase slug style.
- `policy` — text. The sheet's between-table prose lives here: buy policies
  (monitor ≥1440p filter), lane-wide doctrine (hall-mod default), service-lane comps,
  FVF notes, lane conclusions (MacBook broken-market verdict). Narrative, not modeled.

### DeviceReference (grown)

One row per thing-with-its-own-money. Where prices.md compressed two variants into one
line ("PS4 Slim 500GB / 1TB — $83 / $115 — stop $28 / $38"), the DB splits them into
two rows (Nick approved 2026-07-21). Class-grade rows ("27\" 1440p premium class",
"Mid-tier brands") are legitimate catalog rows with a blank brand.

New fields, all optional:

- `sku_prefix` — "CUH-20xx / 21xx / 22xx", "JDM-040/050/055", "A1466". Identity aid.
- `memory_config` — "8GB GDDR5 unified, 256-bit, 16× 4Gb (clamshell)". A decision
  string for harvest/donor calls, deliberately not structured further.
- `stop_price` — the max-buy ceiling. **Hand-set, never computed.** The 1/3 rule is
  policy that informs the number; mothballs, second-stops, and tuned stops override it.
- `stop_note` — the reasoning + revision history ("$60→$50 2026-07-13; mothballed
  2026-07-16").

### CompPull (new, append-only)

One market observation per row, child of a catalog row. Current comp = latest pull;
history comes free. Never edited into a different observation — a new pull is a new row.

- `kind` — `working` | `parts` | `service` | `other`.
- `median`, `p25`, `p75` — dollars, nullable.
- `n` — sample size, nullable.
- `window_days` — the sold-window span the pull covered, nullable.
- `velocity_per_day` — units/day where cleanly known, nullable. Best-match floors and
  messy velocity reads stay in `note` (the sheet's "bm"/"floor" annotations don't
  reduce to a clean number).
- `verified` — `V` (verified sold/transaction data) | `E` (estimate/cross-referenced).
- `pulled_on` — date of the pull.
- `note` — everything the structured fields can't hold, verbatim from the sheet.
  Zero-information-loss rule: when a sheet cell is compound, the full text lands here.

### Derived, not stored

- **Stale** — latest `working` pull older than 60 days (the sheet's refresh rule).
- **Gap** — catalog row with no pull at all (the sheet's "Comp gaps" section).

Both are queryset annotations surfaced as filters on the reference page.

## Seeding

`manage.py seed_pricesheet` loads `repairs/data/price_sheet_seed.json` — same pattern
as `seed_reference`. Idempotent: lanes keyed on `name`, references on `(brand, name)`,
pulls on `(reference, kind, pulled_on)`. The JSON was transcribed by hand from
prices.md 2026-07-21 (variant rows split, compound cells → notes verbatim); it is the
one-off migration artifact, kept in-tree for auditability.

`seed_reference` (the older 136-row identity catalog) still runs; the two seeds merge
on `(brand, name)` where they name the same model. Price-sheet rows that match an
existing catalog row update it in place; the rest create new rows.

## Out of scope (this pass)

- Automating eBay comp pulls into CompPull rows (passthrough parsing) — later piece.
- The ledger side (Purchase/units/exits) — build-order step 2.
- Frontend CRUD for the sheet — writes go through Django admin for v1.
