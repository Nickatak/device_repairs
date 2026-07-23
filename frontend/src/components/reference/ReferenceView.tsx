"use client";

import { useMemo, useState } from "react";
import type { CompPull, Issue, Lane, ReferenceItem, Variant } from "@/lib/api/reference";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SortTh, applySort, useSort } from "@/components/ui/sorting";

// Lanes with a dedicated badge color; everything else falls back to .cat-other.
const COLORED_LANES = new Set([
  "console",
  "controller",
  "monitor",
  "laptop",
  "handheld",
  "gpu",
  "cpu",
  "parts",
]);

function laneBadgeClass(lane: string): string {
  return COLORED_LANES.has(lane) ? `badge cat-${lane}` : "badge cat-other";
}

function laneLabel(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1);
}

function money(value: string | null): string {
  if (value === null || value === "") return "—";
  const n = Number(value);
  return Number.isInteger(n) ? `$${n}` : `$${n.toFixed(2)}`;
}

function latestWorking(item: ReferenceItem): CompPull | null {
  // comp_pulls arrive newest-first from the API. Base-model pulls only —
  // a variant comp doesn't stand in for the standard model's price.
  return (
    item.comp_pulls.find((p) => p.kind === "working" && p.variant === null) ?? null
  );
}

type SortKey = "model" | "lane" | "stop" | "comp" | "pulled";

function sortValue(item: ReferenceItem, key: SortKey): string | number | null {
  switch (key) {
    case "model":
      return item.brand ? `${item.brand} ${item.name}` : item.name;
    case "lane":
      return item.lane;
    case "stop":
      return item.stop_price !== null ? Number(item.stop_price) : null;
    case "comp": {
      const median = latestWorking(item)?.median ?? null;
      return median !== null ? Number(median) : null;
    }
    case "pulled":
      // ISO dates sort correctly as strings.
      return latestWorking(item)?.pulled_on ?? null;
  }
}

function matches(item: ReferenceItem, query: string): boolean {
  if (!query) return true;
  const haystack = [
    item.name,
    item.brand,
    item.lane,
    item.sku_prefix,
    item.memory_config,
    item.model_numbers,
    String(item.release_year ?? ""),
  ]
    .join(" ")
    .toLowerCase();
  // Every whitespace-separated term must appear (AND search).
  return query
    .toLowerCase()
    .split(/\s+/)
    .every((term) => haystack.includes(term));
}

// Avoid first — the money-saver when scanning listings — then caution, then buy.
const VERDICT_ORDER: Issue["verdict"][] = ["avoid", "caution", "buy"];

function IssueTable({ issues }: { issues: Issue[] }) {
  const ordered = VERDICT_ORDER.flatMap((v) =>
    issues.filter((i) => i.verdict === v),
  );
  return (
    <table className="pull-table issue-table">
      <thead>
        <tr>
          <th>Category</th>
          <th>Fault</th>
          <th>Cause</th>
          <th>Verdict</th>
          <th>Note</th>
        </tr>
      </thead>
      <tbody>
        {ordered.map((issue) => (
          <tr key={issue.id}>
            <td>{issue.category || "—"}</td>
            <td>{issue.fault}</td>
            <td>{issue.cause || "—"}</td>
            <td>
              <span className={`badge issue-${issue.verdict}`} title={issue.verdict_display}>
                {issue.verdict}
              </span>
            </td>
            <td className="pull-note">{issue.note || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Compact per-verdict tally for the collapsed row's sub-line.
function issueCounts(issues: Issue[]): string {
  return VERDICT_ORDER.map((v) => {
    const n = issues.filter((i) => i.verdict === v).length;
    return n ? `${n} ${v}` : null;
  })
    .filter(Boolean)
    .join(" · ");
}

// The lot-pile signal: this model has premium variants — pull them out before
// standard processing.
function VariantChips({ variants }: { variants: Variant[] }) {
  return (
    <p className="ref-configs">
      <strong>Variants:</strong>{" "}
      {variants.map((v, i) => (
        <span key={v.id} title={v.note || undefined}>
          {i > 0 && " · "}
          {v.name}
        </span>
      ))}
    </p>
  );
}

function PullHistory({ pulls }: { pulls: CompPull[] }) {
  if (pulls.length === 0) {
    return <p className="ref-notes">No comp pulls recorded yet — pull before first buy.</p>;
  }
  return (
    <table className="pull-table">
      <thead>
        <tr>
          <th>Pulled</th>
          <th>Variant</th>
          <th>Kind</th>
          <th className="num">Median</th>
          <th className="num">p25–p75</th>
          <th className="num">n</th>
          <th className="num">Window</th>
          <th className="num">Units/day</th>
          <th>V/E</th>
          <th>Note</th>
        </tr>
      </thead>
      <tbody>
        {pulls.map((p) => (
          <tr key={p.id}>
            <td className="ref-year">{p.pulled_on}</td>
            <td>{p.variant_name ?? "—"}</td>
            <td>{p.kind_display}</td>
            <td className="num">{money(p.median)}</td>
            <td className="num">
              {p.p25 || p.p75 ? `${money(p.p25)}–${money(p.p75)}` : "—"}
            </td>
            <td className="num">{p.n ?? "—"}</td>
            <td className="num">{p.window_days ? `${p.window_days}d` : "—"}</td>
            <td className="num">{p.velocity_per_day ? Number(p.velocity_per_day) : "—"}</td>
            <td>{p.verified}</td>
            <td className="pull-note">{p.note || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ReferenceView({
  items,
  lanes,
  error,
}: {
  items: ReferenceItem[];
  lanes: Lane[];
  error: string | null;
}) {
  const [query, setQuery] = useState("");
  const [lane, setLane] = useState("all");
  const [staleOnly, setStaleOnly] = useState(false);
  // Default view = rows with a working comp; toggling off adds the rest back.
  const [hasCompOnly, setHasCompOnly] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const { sort, toggle } = useSort<SortKey>();

  const doctrine = lanes.find((l) => l.name === "doctrine");
  const selectedLane = lanes.find((l) => l.name === lane);

  // Only show chips for lanes that actually have rows, in alphabetical order.
  const presentLanes = useMemo(
    () => [...new Set(items.map((it) => it.lane))].sort(),
    [items],
  );

  const staleCount = useMemo(() => items.filter((it) => it.stale).length, [items]);
  const gapCount = useMemo(() => items.filter((it) => it.gap).length, [items]);

  const filtered = useMemo(() => {
    const rows = items.filter(
      (it) =>
        (lane === "all" || it.lane === lane) &&
        (!staleOnly || it.stale) &&
        (!hasCompOnly || !it.gap) &&
        matches(it, query),
    );
    applySort(rows, sort, sortValue);
    return rows;
  }, [items, query, lane, staleOnly, hasCompOnly, sort]);

  const pager = usePagination(filtered);

  return (
    <main className="wide">
      <header className="page-head">
        <div>
          <h1>Price Sheet</h1>
          <p className="subtitle">
            {items.length} rows — stops, comps, and identity per model.{" "}
            {staleCount} stale (&gt;60d), {gapCount} without a working comp
            {hasCompOnly && gapCount > 0 ? " (hidden)" : ""}.
          </p>
        </div>
      </header>

      {error ? (
        <p className="error">Could not load the price sheet: {error}</p>
      ) : (
        <>
          {doctrine?.policy && (
            <details className="lane-policy">
              <summary>Sheet doctrine — the 1/3 rule, symptom-decoding, velocity regimes</summary>
              <pre>{doctrine.policy}</pre>
            </details>
          )}

          <div className="ref-controls">
            <input
              className="ref-search"
              type="search"
              placeholder="Search model, brand, SKU prefix, lane…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
            <div className="ref-filters">
              <button
                className={lane === "all" ? "ref-chip active" : "ref-chip"}
                onClick={() => setLane("all")}
              >
                All
              </button>
              {presentLanes.map((name) => (
                <button
                  key={name}
                  className={lane === name ? "ref-chip active" : "ref-chip"}
                  onClick={() => setLane(name)}
                >
                  {laneLabel(name)}
                </button>
              ))}
            </div>
            <span className="chip-divider" aria-hidden />
            <div className="ref-filters">
              <button
                className={staleOnly ? "ref-chip flag-stale active" : "ref-chip flag-stale"}
                onClick={() => setStaleOnly(!staleOnly)}
                title="Latest working comp older than 60 days — due for a re-pull"
              >
                Stale
              </button>
              <button
                className={hasCompOnly ? "ref-chip flag-good active" : "ref-chip flag-good"}
                onClick={() => setHasCompOnly(!hasCompOnly)}
                title="On (default): only rows with a working comp. Off: rows without one join the list — pull before first buy."
              >
                Has working comp
              </button>
            </div>
          </div>

          {selectedLane?.policy && (
            <details className="lane-policy">
              <summary>{laneLabel(selectedLane.name)} lane policy</summary>
              <pre>{selectedLane.policy}</pre>
            </details>
          )}

          {filtered.length === 0 ? (
            <p className="empty">No rows match.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <SortTh label="Model" k="model" sort={sort} onToggle={toggle} />
                  <SortTh label="Lane" k="lane" sort={sort} onToggle={toggle} />
                  <SortTh label="Stop" k="stop" sort={sort} onToggle={toggle} className="num" />
                  <SortTh label="Working comp" k="comp" sort={sort} onToggle={toggle} className="num" />
                  <SortTh label="Pulled" k="pulled" sort={sort} onToggle={toggle} />
                </tr>
              </thead>
              <tbody>
                {pager.paged.map((it) => {
                  const pull = latestWorking(it);
                  const expanded = expandedId === it.id;
                  return [
                    <tr
                      key={it.id}
                      className="ref-row"
                      onClick={() => setExpandedId(expanded ? null : it.id)}
                    >
                      <td>
                        <div className="ref-model">
                          {it.brand ? `${it.brand} ${it.name}` : it.name}
                        </div>
                        <div className="ref-sub">
                          {it.sku_prefix && (
                            <span className="ref-modelnum">{it.sku_prefix}</span>
                          )}
                          {it.memory_config && <> {it.memory_config}</>}
                          {it.issues.length > 0 && (
                            <span className="issue-counts"> {issueCounts(it.issues)}</span>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className={laneBadgeClass(it.lane)}>{laneLabel(it.lane)}</span>
                      </td>
                      <td className="num ref-stop">{money(it.stop_price)}</td>
                      <td className="num">
                        {pull ? (
                          <>
                            {money(pull.median)}
                            {pull.n ? <span className="ref-sub"> n={pull.n}</span> : null}
                            {pull.verified === "E" && (
                              <span className="badge flag-estimate">E</span>
                            )}
                          </>
                        ) : (
                          <span className="badge flag-gap">no comp</span>
                        )}
                      </td>
                      <td className="ref-year">
                        {pull?.pulled_on ?? "—"}
                        {it.stale && <span className="badge flag-stale">stale</span>}
                      </td>
                    </tr>,
                    expanded ? (
                      <tr key={`${it.id}-detail`} className="ref-expand">
                        <td colSpan={5}>
                          {it.variants.length > 0 && <VariantChips variants={it.variants} />}
                          {it.issues.length > 0 && <IssueTable issues={it.issues} />}
                          {it.stop_note && (
                            <p className="ref-configs">
                              <strong>Stop:</strong> {it.stop_note}
                            </p>
                          )}
                          {it.configurations && (
                            <p className="ref-configs">{it.configurations}</p>
                          )}
                          {it.notes && <p className="ref-notes">{it.notes}</p>}
                          <PullHistory pulls={it.comp_pulls} />
                        </td>
                      </tr>
                    ) : null,
                  ];
                })}
              </tbody>
            </table>
          )}
          <Pagination {...pager} />
        </>
      )}
    </main>
  );
}
