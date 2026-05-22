"use client";

import { useEffect, useRef, useState } from "react";
import {
  RefreshCw, CheckCircle2, XCircle, Loader2, ChevronDown,
  History, ArrowRight, TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { apiFetch, apiClient } from "@/lib/api-client";

type Phase = "idle" | "scraping" | "loading" | "done" | "error";

interface JobStatus {
  phase:            Phase;
  message:          string;
  elapsed_secs:     number;
  stations_scraped: number;
  stations_loaded:  number;
  error:            string | null;
}

interface RunStats {
  total_stations:     number;
  available_stations: number;
  total_chargers:     number;
  total_connectors:   number;
  cities_covered:     number;
  operators_count:    number;
}

interface HistoryRun {
  triggered_at:     string;
  completed_at:     string;
  duration_secs:    number;
  stations_scraped: number;
  stations_loaded:  number;
  before:           RunStats;
  after:            RunStats;
  delta:            Record<string, number>;
}

const STAT_LABELS: Array<{ key: keyof RunStats; label: string }> = [
  { key: "total_stations",     label: "Total Stations"     },
  { key: "available_stations", label: "Available"          },
  { key: "total_chargers",     label: "Chargers"           },
  { key: "total_connectors",   label: "Connectors"         },
  { key: "cities_covered",     label: "Cities"             },
  { key: "operators_count",    label: "Operators"          },
];

function fmtElapsed(secs: number) {
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function Delta({ value }: { value: number }) {
  if (value === 0) return <span className="flex items-center gap-0.5 text-muted-foreground"><Minus className="w-3 h-3" />0</span>;
  if (value > 0)  return <span className="flex items-center gap-0.5 text-green-400"><TrendingUp className="w-3 h-3" />+{value.toLocaleString()}</span>;
  return <span className="flex items-center gap-0.5 text-red-400"><TrendingDown className="w-3 h-3" />{value.toLocaleString()}</span>;
}

// ── History panel ─────────────────────────────────────────────────────────────
function HistoryPanel({ onClose }: { onClose: () => void }) {
  const [runs, setRuns] = useState<HistoryRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(0);

  useEffect(() => {
    apiFetch<HistoryRun[]>("/admin/scrape/history")
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="absolute right-0 top-full mt-1.5 w-[480px] max-h-[80vh] rounded-xl border border-border bg-popover shadow-2xl z-50 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 shrink-0">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-muted-foreground" />
          <p className="text-sm font-semibold">Scrape History</p>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-xs px-2 py-1 rounded hover:bg-muted transition-colors">
          Close
        </button>
      </div>

      <div className="overflow-y-auto flex-1">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        )}
        {!loading && runs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <History className="w-8 h-8 text-muted-foreground mb-3 opacity-40" />
            <p className="text-sm text-muted-foreground">No scrape history yet.</p>
            <p className="text-xs text-muted-foreground mt-1">Run your first scrape to see before/after data here.</p>
          </div>
        )}
        {!loading && runs.map((run, idx) => (
          <div key={idx} className="border-b border-border/40 last:border-0">
            {/* Run header */}
            <button
              onClick={() => setExpanded(expanded === idx ? null : idx)}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors text-left"
            >
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate">{fmtDate(run.triggered_at)}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {fmtElapsed(run.duration_secs)} · {run.stations_scraped.toLocaleString()} scraped · {run.stations_loaded.toLocaleString()} loaded
                </p>
              </div>
              {/* Quick delta badge */}
              <div className={cn(
                "text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0",
                (run.delta?.total_stations ?? 0) > 0 ? "bg-green-500/15 text-green-400" :
                (run.delta?.total_stations ?? 0) < 0 ? "bg-red-500/15 text-red-400"   :
                "bg-muted text-muted-foreground"
              )}>
                {(run.delta?.total_stations ?? 0) > 0 ? "+" : ""}{run.delta?.total_stations ?? 0} stations
              </div>
              <ArrowRight className={cn("w-3.5 h-3.5 text-muted-foreground shrink-0 transition-transform", expanded === idx && "rotate-90")} />
            </button>

            {/* Expanded diff table */}
            {expanded === idx && (
              <div className="px-4 pb-4">
                <div className="rounded-lg border border-border overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border bg-muted/30">
                        <th className="text-left px-3 py-2 text-muted-foreground font-medium">Metric</th>
                        <th className="text-right px-3 py-2 text-muted-foreground font-medium">Before</th>
                        <th className="text-right px-3 py-2 text-muted-foreground font-medium">After</th>
                        <th className="text-right px-3 py-2 text-muted-foreground font-medium">Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {STAT_LABELS.map(({ key, label }) => (
                        <tr key={key} className="border-b border-border/40 last:border-0 hover:bg-muted/20">
                          <td className="px-3 py-2 text-muted-foreground">{label}</td>
                          <td className="px-3 py-2 text-right tabular-nums">{(run.before?.[key] ?? 0).toLocaleString()}</td>
                          <td className="px-3 py-2 text-right tabular-nums font-semibold">{(run.after?.[key] ?? 0).toLocaleString()}</td>
                          <td className="px-3 py-2 text-right tabular-nums">
                            <Delta value={run.delta?.[key] ?? 0} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-[10px] text-muted-foreground mt-2 text-right">
                  Completed {fmtDate(run.completed_at)} · took {fmtElapsed(run.duration_secs)}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main button ───────────────────────────────────────────────────────────────
const PHASE_LABEL: Record<Phase, string> = {
  idle:     "Idle",
  scraping: "Scraping…",
  loading:  "Loading into DB…",
  done:     "Complete",
  error:    "Error",
};

export function ScrapeButton() {
  const qc = useQueryClient();
  const [status, setStatus]     = useState<JobStatus | null>(null);
  const [open, setOpen]         = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [triggering, setTriggering]   = useState(false);
  const panelRef  = useRef<HTMLDivElement>(null);
  const pollRef   = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    apiFetch<JobStatus>("/admin/scrape/status").then(setStatus).catch(() => null);
  }, []);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowHistory(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    const running = status?.phase === "scraping" || status?.phase === "loading";
    if (running && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const s = await apiFetch<JobStatus>("/admin/scrape/status");
          setStatus(s);
          if (s.phase === "done") await qc.invalidateQueries();
          if (s.phase === "done" || s.phase === "error") {
            clearInterval(pollRef.current!);
            pollRef.current = null;
          }
        } catch {}
      }, 3000);
    }
    if (!running && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, [status?.phase, qc]);

  async function trigger() {
    if (triggering || status?.phase === "scraping" || status?.phase === "loading") return;
    setTriggering(true);
    try {
      await apiClient.post("/admin/scrape/trigger");
      const s = await apiFetch<JobStatus>("/admin/scrape/status");
      setStatus(s);
      setOpen(true);
      setShowHistory(false);
    } catch {}
    finally { setTriggering(false); }
  }

  const running = status?.phase === "scraping" || status?.phase === "loading";
  const phase   = status?.phase ?? "idle";
  const isDone  = phase === "done";
  const isError = phase === "error";

  return (
    <div ref={panelRef} className="relative">
      {/* Trigger button */}
      <button
        onClick={() => { setOpen((v) => !v); setShowHistory(false); }}
        title="Scrape live data"
        className={cn(
          "flex items-center gap-1.5 h-8 px-2.5 rounded-md border text-xs font-medium transition-colors",
          running  ? "border-primary/40 bg-primary/10 text-primary" :
          isDone   ? "border-green-500/40 bg-green-500/10 text-green-400" :
          isError  ? "border-destructive/40 bg-destructive/10 text-destructive" :
                     "border-border bg-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
        )}
      >
        {running || triggering ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> :
         isDone  ? <CheckCircle2 className="w-3.5 h-3.5" /> :
         isError ? <XCircle className="w-3.5 h-3.5" /> :
                   <RefreshCw className="w-3.5 h-3.5" />}
        <span className="hidden sm:inline">Scrape</span>
        <ChevronDown className="w-3 h-3 opacity-50" />
      </button>

      {/* History panel */}
      {showHistory && <HistoryPanel onClose={() => setShowHistory(false)} />}

      {/* Status panel */}
      {open && !showHistory && (
        <div className="absolute right-0 top-full mt-1.5 w-72 rounded-xl border border-border bg-popover shadow-xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50">
            <p className="text-xs font-semibold">Live Scrape</p>
            <div className="flex items-center gap-1.5">
              {status && (
                <span className={cn(
                  "text-[10px] font-medium px-1.5 py-0.5 rounded-full",
                  running  ? "bg-primary/15 text-primary" :
                  isDone   ? "bg-green-500/15 text-green-400" :
                  isError  ? "bg-destructive/15 text-destructive" :
                             "bg-muted text-muted-foreground"
                )}>
                  {PHASE_LABEL[phase]}
                </span>
              )}
              {/* History button */}
              <button
                onClick={() => { setShowHistory(true); setOpen(false); }}
                title="View scrape history"
                className="flex items-center gap-1 h-6 px-2 rounded-md border border-border text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <History className="w-3 h-3" />
                History
              </button>
            </div>
          </div>

          <div className="px-4 py-3 space-y-3">
            <p className="text-xs text-muted-foreground leading-snug min-h-[2.5rem]">
              {status?.message || "Click 'Start Scrape' to fetch live data from Statiq.in and reload the database."}
            </p>

            {status && phase !== "idle" && (
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Elapsed"  value={fmtElapsed(status.elapsed_secs)} />
                <Stat label="Scraped"  value={status.stations_scraped > 0 ? status.stations_scraped.toLocaleString() : "—"} />
                <Stat label="Loaded"   value={status.stations_loaded  > 0 ? status.stations_loaded.toLocaleString()  : "—"} />
              </div>
            )}

            {isError && status?.error && (
              <p className="text-[10px] text-destructive bg-destructive/10 rounded-md px-2 py-1.5">{status.error}</p>
            )}

            {running && (
              <div className="h-1 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary rounded-full animate-progress" />
              </div>
            )}

            <button
              onClick={trigger}
              disabled={running || triggering}
              className={cn(
                "w-full h-8 rounded-lg text-xs font-medium transition-colors",
                running || triggering
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              )}
            >
              {triggering ? "Starting…" : running ? PHASE_LABEL[phase] : isDone ? "Scrape Again" : "Start Scrape"}
            </button>

            <p className="text-[10px] text-muted-foreground text-center">
              Fetches all stations from Statiq.in — may take 20–60 min.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/50 px-2 py-1.5 text-center">
      <p className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="text-xs font-semibold tabular-nums">{value}</p>
    </div>
  );
}
