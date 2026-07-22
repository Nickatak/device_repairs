# Domain — Repair Working Log

> **RE-SCOPE 2026-07-21:** the project is now a two-surface ops system (admin: price
> sheet + ledger + repair log; guest: per-device share links) — see `README.md`. The
> repair-log nouns below (Repair/Step/Measurement/Media) remain valid. Known-stale
> parts: the "MVP scope" framing, Status living on Repair (device lifecycle moves to
> Device, matching the tracking CSVs), Order/acquisition_price (superseded by Purchase
> at transaction grain), and the deferred Owner/Customer noun (Person is now real,
> nullable). This doc gets rewritten as each area is rebuilt; price sheet first.

What this is: the **vocabulary and shape** of the repair workflow — the nouns, what each
means, how they relate, and (where decided) the fields. The model has now been
pressure-tested against a real, complete repair — see
[`vg27aq-repair.md`](vg27aq-repair.md). Where the narration contradicted the model, the
model bent. Lines below tagged _(VG27AQ)_ are validated against that job.

Structure is the focus; field *types* / Django specifics are not decided here. The
**case study** is out of scope — it's a derived view of the log, designed later.

Notation: tiers are **Settled**, **Open**, **Deferred** — read the tier before trusting a
line as final.

---

## MVP scope

Single user — **you**. **No auth**: no accounts, no login, no permission model. A
back-of-house you type into while you log (Django admin or a thin interface). The
customer-facing surface is later-business, kept out until real.

The **repair venture** is **primarily a learning vehicle** — and that's what shapes the
domain decisions below: `can't fix` is a detour-and-return rather than a dead-end, and
inventory / consumable / taxonomy concerns are deliberately deferred ("I'll get there
later"). The **software** (this repo) is a productive build on a known stack
(Django/Python/Postgres) — not a learning project. Don't bleed the venture's learning
register into the codebase's; ship the smooth path here. The actual repair work and the
venture's economics live in the separate private notebook at `~/learning/device_repair/`,
not in this repo.

---

## Nouns — Settled

### Repair

One diagnose-and-fix engagement on one Device. Aggregate root of the log. Owns an ordered
sequence of **Steps**, carries a **Status**, and is what **Orders** are attributed to.
_(VG27AQ: the recap job — acquisition through successful soak test.)_

### Device

First-class. A physical unit you can repair more than once; repeat visits attach to the
same Device.

- **identity** — a nullable `reference` FK into the **DeviceReference catalog**
  (2026-07-21: replaced the old free-text Make/DeviceModel lookups — one-fact-one-place;
  brand/name/year live on the catalog row, picked via combobox in the device form).
  Still **best-effort**: a dumpster board with an unclear model keeps reference null
  and leans on `serial` / notes. (Per-unit `model_number` REMOVED 2026-07-21 —
  label numbers live on the catalog row's `model_numbers`.)
- **`serial`** — optional / nullable.
- **`purchase`** — nullable FK → **Purchase** (2026-07-21: replaced device-local
  `source` + `acquisition_price`). The buy event owns source, order #, and money at
  order/shipping-intake grain; per-unit cost is DERIVED (total ÷ expected_units or
  linked-device count), never stored. "ebay order 13-14739-66407, $37.87, 3x
  controllers" is one Purchase; its units become Device rows as identity firms up.
  Null purchase = found/own-stock without a buy record.
- **`location`** — nullable FK → **Location** ('Shelf 1'), free-text lookup.
- **device-level notes** — facts about the unit, not any one step. _(VG27AQ: "uses an
  external 19V power brick" — belongs to the monitor, not Day 1.)_

### Source

Thin lookup of where devices come from (eBay, salvage, own stock). Free-text now, stored
as rows (FK from Device), combo-box later. Grain: reusable channel — "eBay" is one row
many devices point at; per-acquisition money lives on Device.

### Phase track (added 2026-07-21 — the layer above Steps)

Skill growth killed per-screw logging: device familiarity absorbs the routine, so the
log's grain moved up. Every Repair carries a **fixed five-phase pipeline**:

**Teardown → Wash → Repair → Re-assemble → Verify**

- Each phase = a `done_at` timestamp + an optional **deviation note** ("stripped rear
  shell screw") — the routine itself is not logged.
- **Phases are skippable** (a diagnosis-only job never washes; a parts-out dies
  mid-track). `current_phase` = the phase after the *last* completed one, so skips
  don't stall the track.
- **Verify is explicit** — function-validation evidence (pairing test, jack test,
  calibration screenshots) is load-bearing for listings and deserves its own gate.
- **The track ends at Verify.** "Ready to ship" / "listed" / "sold" are Device-
  lifecycle facts (the ledger's `fixed → listed → sold` + exits), not repair phases —
  one fact, one place.
- Freeform **Notes live inside the Repair phase** — the one phase that's genuinely
  variable. The per-screw grain belongs to the parked per-model **Teardown Guide**
  (future DeviceReference child), not to any repair log.
- **`completed` is a MANUAL mark after Verify** (2026-07-21): marking a repair
  completed never requires checking every phase — stopping before re-assembly and
  completing is a deliberate act, and the unchecked phases then read as
  **"not performed"**: a demonstrable statement that they did NOT happen, not an
  ambiguity.

### Note — the spine *of the Repair phase* (renamed from Step, 2026-07-21)

One **notation**, ordered within a Repair: title, text, measurements. "Step" was the
wrong word — these aren't procedure steps, they're log entries. The rename freed
"note" by turning the colliding commentary text fields into `comment`
(Repair.comment, Note.comment, Measurement.comment, Part.comment).

**Untyped** (2026-07-21, Nick's collapse): the old Type enum (test / observation /
repair / notation) carried no information — a test produces an observation, logging
it makes it a notation, and a corrective entry is equally a notation of work done
(the phase track already marks that repair work happened).

**Standing "Measurements" note** (2026-07-21): every repair is born with one note
titled "Measurements" at position 0 — the bucket for readings that belong to no
specific notation ("there's almost ALWAYS at least a bundle of measurements").
Created automatically on repair creation; backfilled in migration 0016.

- Symptoms, faults, setbacks, and **damage** are all just **observations within Steps**,
  not separate nouns. _(VG27AQ: presenting bootloop, the "4 swollen caps" diagnosis, "broke
  a needle", "burned the hole", and a brand-new symptom appearing *after* the recap — all
  observations, landing anywhere on the timeline.)_
- **Step → Part(s)** is **optional** (0..many). A corrective Step may consume Parts (the
  caps) or none at all. _(VG27AQ: the ribbon-cable reseat fixed a fault and consumed
  nothing — "fix" ≠ "install a part".)_
- **Step → Measurement(s)** — structured children, below.
- **Hierarchy: one level deep.** A Step may have **sub-steps** (self-FK parent), but a
  sub-step cannot itself have sub-steps. More than one level means the approach went wrong
  (no deep/circular diagnostic chains). _(VG27AQ: the blocked GND-hole sub-saga — pokey
  needles, SS-03 pump, burned hole, micro-drill, drilled-out, barrel intact — is one parent
  Step with child Steps.)_
- **Optional timing** — `started_at` / `ended_at`, both nullable, **settable not
  required**. For things like a heat-soak test. _(VG27AQ: soak 8:14→9:27 PM.)_ The Day-N
  grouping in the example is just narration, not a modeled entity.
- **step-level notes** — step-scoped commentary, distinct from repair-level notes (we want
  both).

### Measurement

Child of Step, zero-to-many. Normalized to Step only (no device FK; reach device via
`step → repair → device`). _(VG27AQ: DC-jack reading.)_

**Simplified 2026-07-21** (same grain-shift as the phase track): the original
structured shape — `what` FK lookup, decimal `value`, `unit` FK, `expected` nominal —
was pre-skill over-modeling. Now three free-text fields, optimized for typing speed
at the bench:

- **`what`** — text. "5V rail", "C701 ESR", "DC jack".
- **`value`** — text. "4.98 V", "120 mΩ", "no reading — pad lifted".
- **`note`** — optional. The "why", or a provisional conclusion.
- **Failed measurement** = the story told in `value` or `note`. No structured outcome.
- The old `MeasurementWhat` / `Unit` lookup tables are gone (were empty; dropped in
  migration 0012).

### Order

A **dumb** first-class model for rough spend visibility. The driving question: *"did this
device cost me more in parts than it's worth?"*

- **`name`**, **`quantity`**, **`link`**, **`price`**, **`date`** (ordered),
  **`arrival_date`** (nullable — null = not yet arrived; the dates *are* the state, no
  enum). _(VG27AQ: Digi-Key, $11.88, ~4 days, 10× P14413-ND.)_
- **`category`** — **`parts`** or **`tools`**. That's the whole taxonomy; no edge cases,
  no consumable management (not tracking solder-on-hand).
- **Attributed to a Repair** (FK, nullable). The link is **motivated-by**, not used-in: an
  order can attach to a repair it never touched. _(VG27AQ: the AiXun T3A station arrived
  *after* the repair was done — filed under it, never used in it.)_
- **Why the category split matters:** `parts` roll up against a device's economics;
  `tools` are **capital you keep** and are *excluded* from "what did this device cost me".
  _(VG27AQ: the SS-03 pump and AiXun station are tools — reused beyond this board.)_

### Part vs Tool

The split, kept deliberately simple:

- **Part** — consumed *into* the board; attaches to a Step; counts toward the device's
  parts cost.
- **Tool** — a durable asset you keep; enters via an `Order` with `category=tools`; tracked
  for total spend but never charged to one device.

No stocking model, no inventory, no consumable depletion yet — "I'll get there later."

### Status — DEVICE lifecycle (moved off Repair 2026-07-21)

The old Repair.Status conflated bench-state with disposition, and the write path
manufactured **phantom repairs as status carriers** (setting a status on a device
created a Repair). Both are gone. Status now lives on **Device**, mirrors the
tracking-CSV ledger's pressure-tested lifecycle, and is **manually set**:

- **Pipeline** (bought, not yet in your possession): `shipped (inbound)`. No `lead`
  state — a device row exists only once it's bought and/or shipping (Nick,
  2026-07-21); watched listings aren't inventory.
- **On-hand** (occupies space — the space-neutral slice):
  `acquired` · `diagnosed` · `in repair` · `fixed` · `listed`
- **Terminal** (no longer on-hand): `sold` · `parted` · `scrapped` · `gifted` · `lost`

Notes:

- **Bench-work state is NOT here** — that's the Repair's phase track. Two layers:
  *where the unit sits in the pipeline* (Device.status) vs *where the bench work
  stands* (phases).
- **`blocked_reason` — REMOVED 2026-07-21** (existed one day, migrations 0013→0022):
  Nick dropped the flag; "waiting on parts" reads fine from status + notes.
- **No `won't fix` / `can't fix`** — the ledger never had them; those units sit at
  `diagnosed` with the decision in notes (migration 0013 preserved old values as
  note markers).
- **Repairs are started explicitly** ("+ Start repair" when work begins) — a Repair
  exists because bench work happened, never to hold a status.

### Media

Before/after and board photos, attaching at **both** Repair and Step level. The
load-bearing case isn't pretty portfolio shots — it's **condition documentation**:
photograph an obvious pre-existing defect (cracked panel, a hole) so a future "they broke
my screen" claim is answered with "it arrived that way, here's the intake photo".
Repair-level for whole-unit intake condition; Step-level for a specific finding.

### Lookups (shared pattern)

**Source**, Measurement **`what`**, and **`unit`** are thin FK-target tables: free text
now, deduped rows, combo-box later. Same mechanism, three times.

### Querying

- Flat "all measurements for a device": `filter(step__repair__device=d)` — one query.
  Wrap as `for_device(d)`.
- Nested timeline: `prefetch_related('steps__measurements')` — constant 2 queries.

---

## Nouns — Open

### Component / Board taxonomy (deferred by skill, not design)

The internals (what "main board" means, where C701 sits) stay **unmodeled** — not because
they're unidentifiable, but because Nick hasn't done enough repairs to taxonomize them
*yet*. Location lives as free text in the step narrative and the `what` label; the lookups
accumulate raw vocabulary until patterns are visible enough to structure. _(VG27AQ: "main
board" and "probably the backlight board" — named by eye, hedged.)_ Related: "what failed"
≠ "what got replaced" (a healthy pair-mate was swapped), which this taxonomy will
eventually have to hold. **Observations are now being collected** (not modeled) in
[`monitor-taxonomy.md`](../scratch/monitor-taxonomy.md) as teardowns accrue — the catalog grows; the
data-model decision still waits.

_(Media and provisional-confidence resolved — see Settled and Resolved.)_

---

## Nouns — Deferred (named, not modeled)

- **Owner / Customer** — always you now. Future business. (Re-scoped 2026-07-21:
  becomes Person with nullable Device.owner / Device.sold_to when the ledger lands.)
- **Quote / Labor** — the money + time story beyond `acquisition_price` and Order spend.
- **Case Study** — curated public narrative derived from a Repair. Out of scope.
- **Teardown Guide** (parked 2026-07-21, Nick's explicit park) — per-*model* deep
  teardown documentation: every screw, positioning notations. Hangs off
  DeviceReference (the catalog row) when built, NOT off repairs. Do not scope until
  Nick reopens it.

---

## Relationship sketch (prose, not an ERD)

A **Repair** is opened against a **Device** (which has a **Source** and optional
acquisition price). The Repair carries a **Status** (manual) and owns an ordered sequence
of **Steps** — one level of sub-steps allowed. Each Step records an action + observation,
optionally a time window, zero-to-many **Measurements**, and zero-to-many consumed
**Parts**. **Orders** (parts | tools) are attributed to the Repair for spend visibility;
parts count against the device's economics, tools don't. **Media** and repair-level
**Notes** hang off the Repair. **Owner**, **Quote**, **Case Study**, and the
Component/Board taxonomy arrive later.

---

## Open questions

1. **Component / Board taxonomy** — deferred until enough repairs to see the patterns.
   This is the only remaining item, and it's a deliberate "later", not an unknown.

## Resolved

- Device first-class; identity best-effort; serial optional.
- Symptom / Fault / Repair Action are **not** nouns — observations within Steps.
- Measurement: structured child of Step, normalized, no `outcome`.
- **Step hierarchy** one level deep; **optional timing**.
- **Order** is a dumb model (name/qty/link/price/date/arrival_date) with a parts|tools
  category; attributed motivated-by to a Repair; drives "did this device cost more than
  it's worth".
- **Tool vs Part**: parts consumed into the board, tools are kept capital; no inventory.
- **Status** is a manual enum incl. `waiting/blocked`, decoupled from Orders.
- Notes at both Repair and Step level.
- Media attaches at **both** Repair and Step level (intake-condition documentation).
- Provisional confidence stays in the measurement `note` for now.
- Status gains holding (`won't fix` / `can't fix`) + terminal (`fixed` / `shipping (to
  buyer)` / `parted out` / `garbage`) bands; decision ≠ disposition. `can't fix` is holding
  (learning project → skill-gap detour, then return).
- Lookups (Source / `what` / `unit`) use free-text-via-FK + combo-box.
