"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight, TrendingUp, TrendingDown, Minus, Plus, X as XIcon, Edit3,
  Loader2, History as HistoryIcon, ChevronRight,
} from "lucide-react";
import { Navbar }  from "@/components/layout/Navbar";
import { apiFetch } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface RunSummary {
  run_id:           string;
  started_at:       string;
  completed_at:     string | null;
  duration_secs:    number;
  stations_in_run:  number;
  available_in_run: number;
}

interface DiffStation {
  id:           number;
  station_name: string | null;
  city_name:    string | null;
  state_name:   string | null;
  operator_name: string | null;
  charger_type: string | null;
  availability?: string | null;
  avg_rating?:   string | number | null;
  review_count?: number | null;
  available_connector_count?: number | null;
  last_availability?: string | null;
  last_rating?:       string | number | null;
  old_availability?:  string | null;
  new_availability?:  string | null;
  old_avg_rating?:    string | number | null;
  new_avg_rating?:    string | number | null;
  old_review_count?:  number | null;
  new_review_count?:  number | null;
  old_available_connectors?: number | null;
  new_available_connectors?: number | null;
}

interface Diff {
  this_run:     { run_id: string; started_at: string | null; completed_at: string | null };
  previous_run: { run_id: string; started_at: string | null; completed_at: string | null } | null;
  summary: {
    before_total: number; after_total: number;
    added: number; removed: number; changed: number; unchanged: number;
    list_capped_at?: number;
  };
  added:   DiffStation[];
  removed: DiffStation[];
  changed: DiffStation[];
  note?:   string;
}

function fmt(n: number) { return n.toLocaleString(); }
function fmtDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}
function fmtDur(s: number) {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}
function Delta({ v }: { v: number }) {
  if (v === 0) return <span className="inline-flex items-center gap-0.5 text-muted-foreground"><Minus className="w-3 h-3" />0</span>;
  if (v > 0)   return <span className="inline-flex items-center gap-0.5 text-green-400"><TrendingUp className="w-3 h-3" />+{fmt(v)}</span>;
  return <span className="inline-flex items-center gap-0.5 text-red-400"><TrendingDown className="w-3 h-3" />{fmt(v)}</span>;
}

export function ScrapeHistoryShell() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: runs = [], isLoading: runsLoading } = useQuery<RunSummary[]>({
    queryKey: ["scrape-runs"],
    queryFn:  () => apiFetch<RunSummary[]>("/admin/scrape/runs"),
  });

  // Auto-pick the most recent run on first load
  const activeId = selectedId ?? runs[0]?.run_id ?? null;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        {/* Left: runs list */}
        <aside className="w-[320px] shrink-0 border-r border-border/50 bg-card/30 overflow-y-auto">
          <div className="sticky top-0 px-4 py-3 border-b border-border/40 bg-card/60 backdrop-blur z-10 flex items-center gap-2">
            <HistoryIcon className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Scrape Runs</h2>
            <span className="ml-auto text-xs text-muted-foreground">{runs.length}</span>
          </div>
          {runsLoading ? (
            <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading…
            </div>
          ) : runs.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No runs yet.</p>
          ) : (
            <ul className="divide-y divide-border/30">
              {runs.map((r) => (
                <li key={r.run_id}>
                  <button
                    onClick={() => setSelectedId(r.run_id)}
                    className={cn(
                      "w-full text-left px-4 py-3 hover:bg-accent/40 transition-colors",
                      r.run_id === activeId && "bg-accent/60",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium truncate">{fmtDate(r.started_at)}</p>
                      <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5 font-mono">{r.run_id}</p>
                    <div className="flex gap-3 text-xs text-muted-foreground mt-1">
                      <span>{fmt(r.stations_in_run)} stations</span>
                      <span className="text-green-400">{fmt(r.available_in_run)} avail</span>
                      <span>{fmtDur(r.duration_secs)}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        {/* Right: diff detail */}
        <main className="flex-1 overflow-y-auto">
          {activeId ? <DiffPanel runId={activeId} /> : (
            <div className="p-8 text-center text-muted-foreground">Select a run on the left to inspect changes.</div>
          )}
        </main>
      </div>
    </div>
  );
}

function DiffPanel({ runId }: { runId: string }) {
  const [tab, setTab] = useState<"summary" | "added" | "removed" | "changed">("summary");
  const { data, isLoading, error } = useQuery<Diff>({
    queryKey: ["scrape-diff", runId],
    queryFn:  () => apiFetch<Diff>(`/admin/scrape/runs/${runId}/diff`),
  });

  if (isLoading) return <div className="p-8 flex items-center gap-2 text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> Computing diff…</div>;
  if (error)     return <div className="p-8 text-red-400">Failed to load diff: {(error as Error).message}</div>;
  if (!data)     return null;

  const s = data.summary;
  const delta = s.after_total - s.before_total;

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Run details</h1>
        <p className="text-sm text-muted-foreground font-mono">{data.this_run.run_id}</p>
        <p className="text-sm text-muted-foreground">
          {fmtDate(data.this_run.started_at)} → {fmtDate(data.this_run.completed_at)}
        </p>
        {data.previous_run && (
          <p className="text-xs text-muted-foreground">
            Compared against previous run <span className="font-mono">{data.previous_run.run_id}</span> ({fmtDate(data.previous_run.started_at)})
          </p>
        )}
        {data.note && <p className="text-xs text-yellow-400/80 mt-2">{data.note}</p>}
      </div>

      {/* Top-line counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card label="Before" value={fmt(s.before_total)} />
        <Card label="After"  value={fmt(s.after_total)} suffix={<Delta v={delta} />} />
        <Card label="Added"   value={fmt(s.added)}   tint="green" icon={<Plus className="w-4 h-4" />} />
        <Card label="Removed" value={fmt(s.removed)} tint="red"   icon={<XIcon className="w-4 h-4" />} />
        <Card label="Changed (status/rating/conn.)" value={fmt(s.changed)} tint="amber" icon={<Edit3 className="w-4 h-4" />} />
        <Card label="Unchanged" value={fmt(s.unchanged)} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border/50 text-sm">
        {[
          { k: "summary" as const, label: "Summary" },
          { k: "added"   as const, label: `Added (${fmt(s.added)})` },
          { k: "removed" as const, label: `Removed (${fmt(s.removed)})` },
          { k: "changed" as const, label: `Changed (${fmt(s.changed)})` },
        ].map((t) => (
          <button
            key={t.k}
            onClick={() => setTab(t.k)}
            className={cn(
              "px-4 py-2 -mb-px border-b-2 transition-colors",
              tab === t.k ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "summary" && <SummaryView diff={data} />}
      {tab === "added"   && <AddedTable   rows={data.added} />}
      {tab === "removed" && <RemovedTable rows={data.removed} />}
      {tab === "changed" && <ChangedTable rows={data.changed} />}

      {s.list_capped_at != null && (s.added > s.list_capped_at || s.removed > s.list_capped_at || s.changed > s.list_capped_at) && (
        <p className="text-xs text-muted-foreground">
          Lists are capped at {s.list_capped_at} rows for display. Totals above show the full count.
        </p>
      )}
    </div>
  );
}

function Card({ label, value, tint, icon, suffix }: {
  label: string; value: string;
  tint?: "green" | "red" | "amber";
  icon?: React.ReactNode; suffix?: React.ReactNode;
}) {
  const color =
    tint === "green" ? "text-green-400 border-green-500/30 bg-green-500/5" :
    tint === "red"   ? "text-red-400 border-red-500/30 bg-red-500/5" :
    tint === "amber" ? "text-amber-300 border-amber-500/30 bg-amber-500/5" :
    "border-border/60 bg-card/40";
  return (
    <div className={cn("rounded-lg border px-4 py-3", color)}>
      <div className="flex items-center justify-between gap-2 text-xs uppercase tracking-wider opacity-80">
        <span>{label}</span>{icon}
      </div>
      <div className="text-2xl font-bold mt-1 flex items-center gap-2">
        {value}{suffix}
      </div>
    </div>
  );
}

function SummaryView({ diff }: { diff: Diff }) {
  return (
    <div className="text-sm space-y-2 text-muted-foreground">
      <p>
        Compared {diff.previous_run ? <>run <span className="font-mono text-foreground">{diff.previous_run.run_id}</span></> : "the initial baseline"} to{" "}
        run <span className="font-mono text-foreground">{diff.this_run.run_id}</span>.
      </p>
      <p>
        <span className="text-green-400 font-medium">{fmt(diff.summary.added)}</span> stations newly scraped,{" "}
        <span className="text-red-400 font-medium">{fmt(diff.summary.removed)}</span> disappeared, and{" "}
        <span className="text-amber-300 font-medium">{fmt(diff.summary.changed)}</span> had status / rating / review-count / connector-availability changes.
      </p>
      <p className="text-xs">
        Switch tabs above to see the individual stations behind each number.
      </p>
    </div>
  );
}

function StationLink({ s }: { s: DiffStation }) {
  return (
    <a href={`/station/${s.id}`} className="font-medium text-foreground hover:text-primary underline-offset-4 hover:underline">
      {s.station_name || `Station ${s.id}`}
    </a>
  );
}

function MetaCell({ s }: { s: DiffStation }) {
  return (
    <span className="text-xs text-muted-foreground">
      {[s.city_name, s.state_name].filter(Boolean).join(", ")}
      {s.operator_name ? ` · ${s.operator_name}` : ""}
    </span>
  );
}

function AddedTable({ rows }: { rows: DiffStation[] }) {
  if (rows.length === 0) return <p className="text-sm text-muted-foreground py-8 text-center">No stations were added.</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border/50">
      <table className="w-full text-sm">
        <thead className="bg-card/40 text-xs uppercase tracking-wider text-muted-foreground">
          <tr><th className="px-3 py-2 text-left">Station</th><th className="px-3 py-2 text-left">Location / operator</th><th className="px-3 py-2 text-left">Type</th><th className="px-3 py-2 text-left">Availability</th><th className="px-3 py-2 text-right">Rating</th></tr>
        </thead>
        <tbody className="divide-y divide-border/30">
          {rows.map((s) => (
            <tr key={s.id} className="hover:bg-accent/30">
              <td className="px-3 py-2"><StationLink s={s} /></td>
              <td className="px-3 py-2"><MetaCell s={s} /></td>
              <td className="px-3 py-2 text-xs">{s.charger_type ?? "—"}</td>
              <td className="px-3 py-2 text-xs">{s.availability ?? "—"}</td>
              <td className="px-3 py-2 text-right text-xs">{s.avg_rating ?? "—"} {s.review_count != null && <span className="text-muted-foreground">({s.review_count})</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RemovedTable({ rows }: { rows: DiffStation[] }) {
  if (rows.length === 0) return <p className="text-sm text-muted-foreground py-8 text-center">No stations were removed.</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border/50">
      <table className="w-full text-sm">
        <thead className="bg-card/40 text-xs uppercase tracking-wider text-muted-foreground">
          <tr><th className="px-3 py-2 text-left">Station</th><th className="px-3 py-2 text-left">Location / operator</th><th className="px-3 py-2 text-left">Type</th><th className="px-3 py-2 text-left">Last availability</th><th className="px-3 py-2 text-right">Last rating</th></tr>
        </thead>
        <tbody className="divide-y divide-border/30">
          {rows.map((s) => (
            <tr key={s.id} className="hover:bg-accent/30">
              <td className="px-3 py-2"><StationLink s={s} /></td>
              <td className="px-3 py-2"><MetaCell s={s} /></td>
              <td className="px-3 py-2 text-xs">{s.charger_type ?? "—"}</td>
              <td className="px-3 py-2 text-xs">{s.last_availability ?? "—"}</td>
              <td className="px-3 py-2 text-right text-xs">{s.last_rating ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function diffField(oldV: unknown, newV: unknown) {
  if (oldV === newV || (oldV == null && newV == null)) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <span className="text-muted-foreground line-through">{String(oldV ?? "—")}</span>
      <ArrowRight className="w-3 h-3" />
      <span className="text-foreground">{String(newV ?? "—")}</span>
    </span>
  );
}

function ChangedTable({ rows }: { rows: DiffStation[] }) {
  if (rows.length === 0) return <p className="text-sm text-muted-foreground py-8 text-center">No tracked field changed since the previous run.</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border/50">
      <table className="w-full text-sm">
        <thead className="bg-card/40 text-xs uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Station</th>
            <th className="px-3 py-2 text-left">Location</th>
            <th className="px-3 py-2 text-left">Availability</th>
            <th className="px-3 py-2 text-left">Rating</th>
            <th className="px-3 py-2 text-left">Reviews</th>
            <th className="px-3 py-2 text-left">Available conn.</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/30">
          {rows.map((s) => (
            <tr key={s.id} className="hover:bg-accent/30 align-top">
              <td className="px-3 py-2"><StationLink s={s} /></td>
              <td className="px-3 py-2"><MetaCell s={s} /></td>
              <td className="px-3 py-2">{diffField(s.old_availability, s.new_availability) ?? <span className="text-xs text-muted-foreground">—</span>}</td>
              <td className="px-3 py-2">{diffField(s.old_avg_rating, s.new_avg_rating) ?? <span className="text-xs text-muted-foreground">—</span>}</td>
              <td className="px-3 py-2">{diffField(s.old_review_count, s.new_review_count) ?? <span className="text-xs text-muted-foreground">—</span>}</td>
              <td className="px-3 py-2">{diffField(s.old_available_connectors, s.new_available_connectors) ?? <span className="text-xs text-muted-foreground">—</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
