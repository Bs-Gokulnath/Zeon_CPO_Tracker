"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, X, Clock, Zap, MapPin } from "lucide-react";
import { useAutocomplete } from "@/hooks/useSearch";
import { useDebounce } from "@/hooks/useDebounce";
import { ChargerTypeBadge } from "@/components/shared/ChargerTypeBadge";
import { cn } from "@/lib/utils";
import type { SearchHit } from "@/types/station";

const RECENT_KEY = "statiq-recent-searches";
const MAX_RECENT = 5;

function highlight(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-primary/20 text-primary rounded-sm">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

interface Props {
  className?: string;
}

export function SearchAutocomplete({ className }: Props) {
  const router = useRouter();
  const [input, setInput]         = useState("");
  const [open, setOpen]           = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [recent, setRecent]       = useState<SearchHit[]>([]);

  const inputRef     = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const q = useDebounce(input, 300);
  const { data: hits = [], isLoading } = useAutocomplete(q);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      if (raw) setRecent(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  const saveRecent = useCallback((hit: SearchHit) => {
    setRecent((prev) => {
      const next = [hit, ...prev.filter((r) => r.id !== hit.id)].slice(0, MAX_RECENT);
      try { localStorage.setItem(RECENT_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const handleSelect = useCallback((hit: SearchHit) => {
    setInput(hit.station_name ?? "");
    setOpen(false);
    setActiveIdx(-1);
    saveRecent(hit);
    router.push(`/station/${hit.id}`);
  }, [router, saveRecent]);

  const clearRecent = useCallback(() => {
    setRecent([]);
    try { localStorage.removeItem(RECENT_KEY); } catch {}
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
        setActiveIdx(-1);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const displayItems: SearchHit[] = q.length >= 1 ? hits : recent;
  const showRecentLabel = q.length === 0 && recent.length > 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) return;
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, displayItems.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, -1));
        break;
      case "Enter":
        e.preventDefault();
        if (activeIdx >= 0 && displayItems[activeIdx]) {
          handleSelect(displayItems[activeIdx]);
        }
        break;
      case "Escape":
        setOpen(false);
        setActiveIdx(-1);
        inputRef.current?.blur();
        break;
    }
  };

  const showDropdown = open && (displayItems.length > 0 || (q.length >= 1 && isLoading));

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Input */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => { setInput(e.target.value); setOpen(true); setActiveIdx(-1); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          className="w-full h-8 rounded-lg border border-border bg-muted/40 pl-8 pr-8 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-transparent transition-all"
          placeholder="Search stations, cities…"
          autoComplete="off"
          spellCheck={false}
        />
        {input && (
          <button
            onClick={() => { setInput(""); setOpen(false); inputRef.current?.focus(); }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute top-full left-0 right-0 mt-1.5 z-50 bg-popover border border-border rounded-xl shadow-xl overflow-hidden">
          {/* Loading */}
          {q.length >= 1 && isLoading && (
            <div className="flex items-center gap-2 px-3 py-2.5 text-xs text-muted-foreground">
              <div className="w-3 h-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              Searching…
            </div>
          )}

          {/* Results or recent label */}
          {displayItems.length > 0 && (
            <>
              <div className="flex items-center justify-between px-3 pt-2 pb-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {showRecentLabel ? (
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Recent</span>
                  ) : (
                    `${hits.length} result${hits.length !== 1 ? "s" : ""}`
                  )}
                </span>
                {showRecentLabel && (
                  <button
                    onClick={clearRecent}
                    className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Clear
                  </button>
                )}
              </div>

              <ul className="pb-1.5">
                {displayItems.map((hit, idx) => (
                  <li key={hit.id}>
                    <button
                      onMouseDown={(e) => { e.preventDefault(); handleSelect(hit); }}
                      onMouseEnter={() => setActiveIdx(idx)}
                      className={cn(
                        "w-full flex items-start gap-2.5 px-3 py-2 text-left transition-colors",
                        activeIdx === idx ? "bg-accent" : "hover:bg-accent/60"
                      )}
                    >
                      <div className="mt-0.5 w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
                        {showRecentLabel
                          ? <Clock className="w-3 h-3 text-muted-foreground" />
                          : <Zap className="w-3 h-3 text-primary" />
                        }
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-foreground truncate">
                          {highlight(hit.station_name ?? "Unnamed Station", q)}
                        </p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          {hit.city_name && (
                            <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground">
                              <MapPin className="w-2.5 h-2.5" />
                              {hit.city_name}
                              {hit.state_name && `, ${hit.state_name}`}
                            </span>
                          )}
                        </div>
                      </div>
                      {hit.charger_type && (
                        <ChargerTypeBadge type={hit.charger_type} className="text-[10px] px-1.5 py-0 shrink-0" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          {/* No results */}
          {q.length >= 1 && !isLoading && hits.length === 0 && (
            <div className="flex items-center gap-2 px-3 py-3 text-xs text-muted-foreground">
              <Search className="w-3.5 h-3.5" />
              No results for &ldquo;{q}&rdquo;
            </div>
          )}
        </div>
      )}
    </div>
  );
}
