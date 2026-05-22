"use client";

import { useEffect, useRef, useState } from "react";
import { Search, X, Zap, MapPin } from "lucide-react";
import { useAutocomplete } from "@/hooks/useSearch";
import { useDebounce } from "@/hooks/useDebounce";
import { ChargerTypeBadge } from "@/components/shared/ChargerTypeBadge";
import { cn } from "@/lib/utils";
import type { SearchHit } from "@/types/station";

function highlight(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-primary/30 text-primary rounded-sm">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

interface Props {
  onSelect: (hit: SearchHit) => void;
  className?: string;
}

export function MapSearchBar({ onSelect, className }: Props) {
  const [input, setInput]     = useState("");
  const [open, setOpen]       = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef     = useRef<HTMLInputElement>(null);

  const q = useDebounce(input, 250);
  const { data: hits = [], isLoading } = useAutocomplete(q);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
        setActiveIdx(-1);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function handleSelect(hit: SearchHit) {
    setInput(hit.station_name ?? "");
    setOpen(false);
    setActiveIdx(-1);
    onSelect(hit);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return;
    if (e.key === "ArrowDown")  { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, hits.length - 1)); }
    if (e.key === "ArrowUp")    { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, -1)); }
    if (e.key === "Enter" && activeIdx >= 0 && hits[activeIdx]) handleSelect(hits[activeIdx]);
    if (e.key === "Escape")     { setOpen(false); inputRef.current?.blur(); }
  }

  const showDropdown = open && (hits.length > 0 || (q.length >= 1 && isLoading));

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => { setInput(e.target.value); setOpen(true); setActiveIdx(-1); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search stations or cities…"
          autoComplete="off"
          spellCheck={false}
          className="w-full h-10 rounded-xl border border-border bg-card/95 backdrop-blur pl-9 pr-9 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 shadow-xl transition-all"
        />
        {input && (
          <button
            onClick={() => { setInput(""); setOpen(false); inputRef.current?.focus(); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute top-full left-0 right-0 mt-1.5 z-50 bg-card border border-border rounded-xl shadow-2xl overflow-hidden">
          {q.length >= 1 && isLoading && (
            <div className="flex items-center gap-2 px-3 py-3 text-xs text-muted-foreground">
              <div className="w-3 h-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              Searching…
            </div>
          )}

          {hits.length > 0 && (
            <>
              <div className="px-3 pt-2 pb-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {hits.length} station{hits.length !== 1 ? "s" : ""} found
                </span>
              </div>
              <ul className="pb-1.5 max-h-64 overflow-y-auto">
                {hits.map((hit, idx) => (
                  <li key={hit.id}>
                    <button
                      onMouseDown={(e) => { e.preventDefault(); handleSelect(hit); }}
                      onMouseEnter={() => setActiveIdx(idx)}
                      className={cn(
                        "w-full flex items-start gap-2.5 px-3 py-2.5 text-left transition-colors",
                        activeIdx === idx ? "bg-accent" : "hover:bg-accent/60"
                      )}
                    >
                      <div className="mt-0.5 w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <Zap className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {highlight(hit.station_name ?? "Unnamed Station", q)}
                        </p>
                        {(hit.city_name || hit.state_name) && (
                          <p className="flex items-center gap-0.5 text-xs text-muted-foreground mt-0.5">
                            <MapPin className="w-3 h-3 shrink-0" />
                            {[hit.city_name, hit.state_name].filter(Boolean).join(", ")}
                          </p>
                        )}
                      </div>
                      {hit.charger_type && (
                        <ChargerTypeBadge type={hit.charger_type} className="text-[10px] shrink-0 mt-0.5" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          {q.length >= 1 && !isLoading && hits.length === 0 && (
            <div className="flex items-center gap-2 px-3 py-3 text-sm text-muted-foreground">
              <Search className="w-4 h-4" />
              No results for &ldquo;{q}&rdquo;
            </div>
          )}
        </div>
      )}
    </div>
  );
}
