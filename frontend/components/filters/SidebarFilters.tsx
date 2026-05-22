"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X, Check, ChevronDown, Search } from "lucide-react";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useFilters } from "@/hooks/useFilters";
import { useFiltersParams } from "@/hooks/useFiltersParams";

const CHARGER_TYPES = [
  { value: "AC",    color: "text-blue-400 border-blue-500/40 data-[active=true]:bg-blue-500/20 data-[active=true]:border-blue-500/60" },
  { value: "DC",    color: "text-orange-400 border-orange-500/40 data-[active=true]:bg-orange-500/20 data-[active=true]:border-orange-500/60" },
  { value: "Mixed", color: "text-purple-400 border-purple-500/40 data-[active=true]:bg-purple-500/20 data-[active=true]:border-purple-500/60" },
];

const RATING_OPTS = [
  { label: "4+", value: 4 },
  { label: "3+", value: 3 },
  { label: "Any", value: null },
];

// ── Multi-select dropdown (portal — escapes ScrollArea overflow) ───────────────
interface MSOption { id: number | string; label: string }

function MultiSelectDropdown({
  options,
  selected,
  onToggle,
  onClear,
  placeholder,
  searchPlaceholder = "Search…",
  disabled = false,
}: {
  options:            MSOption[];
  selected:           (number | string)[];
  onToggle:           (id: number | string) => void;
  onClear:            () => void;
  placeholder:        string;
  searchPlaceholder?: string;
  disabled?:          boolean;
}) {
  const [open, setOpen]   = useState(false);
  const [query, setQuery] = useState("");
  const [rect, setRect]   = useState<DOMRect | null>(null);

  const triggerRef  = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef    = useRef<HTMLInputElement>(null);

  function computeRect() {
    if (triggerRef.current) setRect(triggerRef.current.getBoundingClientRect());
  }

  function handleToggle() {
    if (disabled) return;
    if (!open) computeRect();
    setOpen((v) => !v);
  }

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onMouseDown(e: MouseEvent) {
      const t = e.target as Node;
      if (
        triggerRef.current?.contains(t) ||
        dropdownRef.current?.contains(t)
      ) return;
      setOpen(false);
      setQuery("");
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [open]);

  // Recompute position on scroll / resize
  useEffect(() => {
    if (!open) return;
    const update = () => computeRect();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  // Auto-focus search
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 30);
  }, [open]);

  const filtered = options.filter((o) =>
    o.label.toLowerCase().includes(query.toLowerCase())
  );

  const triggerLabel =
    selected.length === 0
      ? placeholder
      : selected.length === 1
        ? (options.find((o) => o.id === selected[0])?.label ?? placeholder)
        : `${selected.length} selected`;

  const dropdown =
    open && rect
      ? createPortal(
          <div
            ref={dropdownRef}
            style={{
              position: "fixed",
              top:   rect.bottom + 4,
              left:  rect.left,
              width: rect.width,
              zIndex: 9999,
            }}
            className="rounded-md border border-border bg-popover shadow-2xl overflow-hidden"
          >
            {/* Search bar */}
            <div className="flex items-center gap-2 px-2.5 py-2 border-b border-border/60">
              <Search className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground min-w-0"
              />
              {query && (
                <button onClick={() => setQuery("")} className="text-muted-foreground hover:text-foreground shrink-0">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Options */}
            <div className="max-h-48 overflow-y-auto">
              {filtered.length === 0 ? (
                <p className="text-xs text-muted-foreground px-3 py-3 text-center">No results</p>
              ) : (
                filtered.map((opt) => {
                  const isSel = selected.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      onClick={() => onToggle(opt.id)}
                      className={cn(
                        "w-full flex items-center gap-2.5 h-8 px-3 text-xs transition-colors text-left",
                        isSel
                          ? "bg-primary/10 text-primary"
                          : "text-foreground hover:bg-muted/60"
                      )}
                    >
                      <div className={cn(
                        "w-3.5 h-3.5 rounded-sm border flex items-center justify-center shrink-0 transition-colors",
                        isSel ? "bg-primary border-primary" : "border-muted-foreground/40"
                      )}>
                        {isSel && <Check className="w-2.5 h-2.5 text-primary-foreground" />}
                      </div>
                      <span className="truncate">{opt.label}</span>
                    </button>
                  );
                })
              )}
            </div>

            {/* Footer */}
            {selected.length > 0 && (
              <div className="border-t border-border/60 px-3 py-1.5 flex items-center justify-between bg-muted/20">
                <span className="text-[10px] text-muted-foreground">{selected.length} selected</span>
                <button
                  onClick={() => { onClear(); setOpen(false); setQuery(""); }}
                  className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  Clear
                </button>
              </div>
            )}
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <button
        ref={triggerRef}
        onClick={handleToggle}
        disabled={disabled}
        className={cn(
          "w-full flex items-center justify-between h-8 px-3 rounded-md border text-xs transition-colors",
          disabled && "opacity-50 cursor-not-allowed",
          open
            ? "border-ring ring-1 ring-ring/30 bg-muted/40"
            : "border-input bg-transparent hover:bg-muted/40",
          selected.length > 0 ? "text-foreground" : "text-muted-foreground"
        )}
      >
        <span className="truncate mr-1">{triggerLabel}</span>
        <div className="flex items-center gap-1 shrink-0">
          {selected.length > 0 && (
            <span className="text-[9px] font-bold bg-primary text-primary-foreground rounded-full w-4 h-4 flex items-center justify-center">
              {selected.length}
            </span>
          )}
          <ChevronDown className={cn("w-3.5 h-3.5 transition-transform text-muted-foreground", open && "rotate-180")} />
        </div>
      </button>
      {dropdown}
    </>
  );
}

function toggleInArray<T>(arr: T[], value: T): T[] | null {
  const next = arr.includes(value) ? arr.filter((x) => x !== value) : [...arr, value];
  return next.length > 0 ? next : null;
}

// ── Main component ─────────────────────────────────────────────────────────────
export function SidebarFilters() {
  const { data: filterData, isLoading: filtersLoading } = useFilters();
  const { params, setFilter, activeFilterCount, clearFilters } = useFiltersParams();

  const priceMin = filterData?.price_range?.min ?? 0;
  const priceMax = filterData?.price_range?.max ?? 35;

  const selectedStates   = (params.state_id    ?? []) as number[];
  const selectedCities   = (params.city_id     ?? []) as number[];
  const selectedOps      = (params.operator_id ?? []) as number[];
  const selectedChargers = (params.charger_type ?? []) as string[];
  const selectedAccess   = (params.access_type  ?? []) as string[];

  const visibleCities = filterData?.cities.filter(
    (c) => selectedStates.length === 0 || selectedStates.includes(c.state_id)
  ) ?? [];

  const currentKwRange    = [params.min_kw ?? 0, params.max_kw ?? 350];
  const currentPriceRange = [params.min_price ?? priceMin, params.max_price ?? priceMax];

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1">
        {filtersLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full rounded-lg" />
            ))}
          </div>
        ) : (
          <>
          {activeFilterCount > 0 && (
            <div className="flex justify-end px-3 pt-2">
              <Button
                variant="ghost" size="sm"
                onClick={clearFilters}
                className="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
              >
                <X className="w-3 h-3" /> Clear {activeFilterCount}
              </Button>
            </div>
          )}
          <Accordion
            type="multiple"
            defaultValue={["location", "charger", "availability"]}
            className="px-3 py-2"
          >

            {/* Location */}
            <AccordionItem value="location" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Location
              </AccordionTrigger>
              <AccordionContent className="pb-3 space-y-2">
                <MultiSelectDropdown
                  options={filterData?.states.map((s) => ({ id: s.id, label: s.name })) ?? []}
                  selected={selectedStates}
                  onToggle={(id) =>
                    setFilter({ state_id: toggleInArray(selectedStates, id as number), city_id: null })
                  }
                  onClear={() => setFilter({ state_id: null, city_id: null })}
                  placeholder="All states"
                  searchPlaceholder="Search states…"
                />
                <MultiSelectDropdown
                  options={visibleCities.map((c) => ({ id: c.id, label: c.name }))}
                  selected={selectedCities}
                  onToggle={(id) =>
                    setFilter({ city_id: toggleInArray(selectedCities, id as number) })
                  }
                  onClear={() => setFilter({ city_id: null })}
                  placeholder={selectedStates.length ? "All cities" : "Select state first"}
                  searchPlaceholder="Search cities…"
                />
              </AccordionContent>
            </AccordionItem>

            {/* Charger Type */}
            <AccordionItem value="charger" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Charger Type
              </AccordionTrigger>
              <AccordionContent className="pb-3 space-y-3">
                <div className="flex gap-2">
                  {CHARGER_TYPES.map((t) => {
                    const isActive = selectedChargers.includes(t.value);
                    return (
                      <button
                        key={t.value}
                        data-active={isActive}
                        onClick={() =>
                          setFilter({ charger_type: toggleInArray(selectedChargers, t.value) })
                        }
                        className={cn(
                          "flex-1 py-1.5 rounded-lg border text-xs font-medium transition-all",
                          t.color
                        )}
                      >
                        {t.value}
                      </button>
                    );
                  })}
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <Label className="text-xs text-muted-foreground">Power Range</Label>
                    <span className="text-xs font-medium">{currentKwRange[0]}–{currentKwRange[1]} kW</span>
                  </div>
                  <Slider
                    min={0} max={350} step={10}
                    value={currentKwRange}
                    onValueChange={([min, max]) => setFilter({ min_kw: min || null, max_kw: max < 350 ? max : null })}
                    className="w-full"
                  />
                </div>

                {filterData && filterData.connector_types.length > 0 && (
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Connector Type</Label>
                    <Select
                      value={params.connector_type_id ? String(params.connector_type_id) : "_all"}
                      onValueChange={(v) => setFilter({ connector_type_id: v === "_all" ? null : parseInt(v) })}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Any connector" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_all" className="text-xs text-muted-foreground">Any connector</SelectItem>
                        {filterData.connector_types.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)} className="text-xs">
                            {c.name ?? `Type ${c.id}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Pricing */}
            <AccordionItem value="pricing" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Pricing
              </AccordionTrigger>
              <AccordionContent className="pb-3 space-y-1.5">
                <div className="flex justify-between items-center">
                  <Label className="text-xs text-muted-foreground">Price per kWh</Label>
                  <span className="text-xs font-medium">
                    ₹{currentPriceRange[0]}–₹{currentPriceRange[1]}
                  </span>
                </div>
                <Slider
                  min={priceMin} max={priceMax} step={1}
                  value={currentPriceRange}
                  onValueChange={([min, max]) => setFilter({
                    min_price: min > priceMin ? min : null,
                    max_price: max < priceMax ? max : null,
                  })}
                  className="w-full"
                />
              </AccordionContent>
            </AccordionItem>

            {/* Quality */}
            <AccordionItem value="quality" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Quality
              </AccordionTrigger>
              <AccordionContent className="pb-3 space-y-1.5">
                <Label className="text-xs text-muted-foreground">Minimum Rating</Label>
                <div className="flex gap-1.5">
                  {RATING_OPTS.map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => setFilter({ min_rating: opt.value })}
                      className={cn(
                        "flex-1 h-7 rounded-md border text-xs transition-colors",
                        params.min_rating === opt.value
                          ? "bg-primary text-primary-foreground border-primary"
                          : "border-border bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Availability */}
            <AccordionItem value="availability" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Availability
              </AccordionTrigger>
              <AccordionContent className="pb-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="avail-switch" className="text-xs cursor-pointer">Available only</Label>
                  <Switch
                    id="avail-switch"
                    checked={params.availability === "Available"}
                    onCheckedChange={(v) => setFilter({ availability: v ? "Available" : null })}
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Operator */}
            {filterData && filterData.operators.length > 0 && (
              <AccordionItem value="operator" className="border-none">
                <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                  Operator
                </AccordionTrigger>
                <AccordionContent className="pb-3">
                  <MultiSelectDropdown
                    options={filterData.operators.map((op) => ({ id: op.id, label: op.name }))}
                    selected={selectedOps}
                    onToggle={(id) =>
                      setFilter({ operator_id: toggleInArray(selectedOps, id as number) })
                    }
                    onClear={() => setFilter({ operator_id: null })}
                    placeholder="Any operator"
                    searchPlaceholder="Search operators…"
                  />
                </AccordionContent>
              </AccordionItem>
            )}

            {/* Access Type */}
            <AccordionItem value="access" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Access Type
              </AccordionTrigger>
              <AccordionContent className="pb-3 flex gap-2">
                {(filterData?.access_types ?? ["public", "captive"]).map((a) => {
                  const isActive = selectedAccess.includes(a);
                  return (
                    <button
                      key={a}
                      onClick={() =>
                        setFilter({ access_type: toggleInArray(selectedAccess, a) })
                      }
                      className={cn(
                        "flex-1 h-7 rounded-md border text-xs capitalize transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground border-primary"
                          : "border-border bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      {a}
                    </button>
                  );
                })}
              </AccordionContent>
            </AccordionItem>

          </Accordion>
          </>
        )}
      </ScrollArea>
    </div>
  );
}
