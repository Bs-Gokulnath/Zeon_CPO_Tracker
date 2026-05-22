"use client";

import { useEffect, useRef, useState } from "react";
import { RefreshCw, CheckCircle2, XCircle, Loader2, ChevronDown } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { apiFetch, apiClient } from "@/lib/api-client";

type Phase = "idle" | "scraping" | "loading" | "done" | "error";

interface JobStatus {
  phase: Phase;
  message: string;
  elapsed_secs: number;
  stations_scraped: number;
  stations_loaded: number;
  error: string | null;
}

function fmtElapsed(secs: number) {
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

const PHASE_LABEL: Record<Phase, string> = {
  idle:     "Idle",
  scraping: "Scraping…",
  loading:  "Loading into DB…",
  done:     "Complete",
  error:    "Error",
};

export function ScrapeButton() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const pollRef  = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch status once on mount to sync with ongoing job
  useEffect(() => {
    apiFetch<JobStatus>("/admin/scrape/status").then(setStatus).catch(() => null);
  }, []);

  // Close panel on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Polling while job is running
  useEffect(() => {
    const running = status?.phase === "scraping" || status?.phase === "loading";
    if (running && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const s = await apiFetch<JobStatus>("/admin/scrape/status");
          setStatus(s);
          if (s.phase === "done") {
            // Refresh all cached data
            await qc.invalidateQueries();
          }
          if (s.phase === "done" || s.phase === "error") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
          }
        } catch {}
      }, 3000);
    }
    if (!running && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {};
  }, [status?.phase, qc]);

  async function trigger() {
    if (triggering || status?.phase === "scraping" || status?.phase === "loading") return;
    setTriggering(true);
    try {
      await apiClient.post("/admin/scrape/trigger");
      const s = await apiFetch<JobStatus>("/admin/scrape/status");
      setStatus(s);
      setOpen(true);
    } catch (e) {
      console.error(e);
    } finally {
      setTriggering(false);
    }
  }

  const running  = status?.phase === "scraping" || status?.phase === "loading";
  const phase    = status?.phase ?? "idle";
  const isDone   = phase === "done";
  const isError  = phase === "error";

  return (
    <div ref={panelRef} className="relative">
      {/* Trigger button */}
      <button
        onClick={() => { trigger(); setOpen((v) => !v); }}
        title="Scrape live data"
        className={cn(
          "flex items-center gap-1.5 h-8 px-2.5 rounded-md border text-xs font-medium transition-colors",
          running
            ? "border-primary/40 bg-primary/10 text-primary"
            : isDone
            ? "border-green-500/40 bg-green-500/10 text-green-400"
            : isError
            ? "border-destructive/40 bg-destructive/10 text-destructive"
            : "border-border bg-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
        )}
      >
        {running || triggering ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : isDone ? (
          <CheckCircle2 className="w-3.5 h-3.5" />
        ) : isError ? (
          <XCircle className="w-3.5 h-3.5" />
        ) : (
          <RefreshCw className="w-3.5 h-3.5" />
        )}
        <span className="hidden sm:inline">Scrape</span>
        <ChevronDown className="w-3 h-3 opacity-50" />
      </button>

      {/* Status panel */}
      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-72 rounded-xl border border-border bg-popover shadow-xl z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50">
            <p className="text-xs font-semibold">Live Scrape</p>
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
          </div>

          <div className="px-4 py-3 space-y-3">
            {/* Message */}
            <p className="text-xs text-muted-foreground leading-snug min-h-[2.5rem]">
              {status?.message || "Click 'Start Scrape' to fetch live data from Statiq.in and reload the database."}
            </p>

            {/* Stats row */}
            {status && phase !== "idle" && (
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Elapsed"   value={fmtElapsed(status.elapsed_secs)} />
                <Stat label="Scraped"   value={status.stations_scraped > 0 ? status.stations_scraped.toLocaleString() : "—"} />
                <Stat label="Loaded"    value={status.stations_loaded  > 0 ? status.stations_loaded.toLocaleString()  : "—"} />
              </div>
            )}

            {/* Error */}
            {isError && status?.error && (
              <p className="text-[10px] text-destructive bg-destructive/10 rounded-md px-2 py-1.5">
                {status.error}
              </p>
            )}

            {/* Progress bar */}
            {running && (
              <div className="h-1 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary rounded-full animate-progress" />
              </div>
            )}

            {/* Action button */}
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
              {triggering ? "Starting…" : running ? `${PHASE_LABEL[phase]}` : isDone ? "Scrape Again" : "Start Scrape"}
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
