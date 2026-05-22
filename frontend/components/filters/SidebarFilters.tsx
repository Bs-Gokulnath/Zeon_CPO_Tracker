"use client";

import { X } from "lucide-react";
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

export function SidebarFilters() {
  const { data: filterData, isLoading: filtersLoading } = useFilters();
  const { params, setFilter, activeFilterCount, clearFilters } = useFiltersParams();

  const priceMin = filterData?.price_range?.min ?? 0;
  const priceMax = filterData?.price_range?.max ?? 35;

  // Derived city list filtered by selected state
  const visibleCities = filterData?.cities.filter(
    (c) => !params.state_id || c.state_id === params.state_id
  ) ?? [];

  const currentKwRange = [params.min_kw ?? 0, params.max_kw ?? 350];
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
                <Select
                  value={params.state_id ? String(params.state_id) : "_all"}
                  onValueChange={(v) => setFilter({ state_id: v === "_all" ? null : parseInt(v), city_id: null })}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select state" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_all" className="text-xs text-muted-foreground">All states</SelectItem>
                    {filterData?.states.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)} className="text-xs">{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select
                  value={params.city_id ? String(params.city_id) : "_all"}
                  onValueChange={(v) => setFilter({ city_id: v === "_all" ? null : parseInt(v) })}
                  disabled={!params.state_id}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder={params.state_id ? "Select city" : "Select state first"} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_all" className="text-xs text-muted-foreground">All cities</SelectItem>
                    {visibleCities.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)} className="text-xs">{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </AccordionContent>
            </AccordionItem>

            {/* Charger Type */}
            <AccordionItem value="charger" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Charger Type
              </AccordionTrigger>
              <AccordionContent className="pb-3 space-y-3">
                <div className="flex gap-2">
                  {CHARGER_TYPES.map((t) => (
                    <button
                      key={t.value}
                      data-active={params.charger_type === t.value}
                      onClick={() => setFilter({ charger_type: params.charger_type === t.value ? null : t.value })}
                      className={cn(
                        "flex-1 py-1.5 rounded-lg border text-xs font-medium transition-all",
                        t.color
                      )}
                    >
                      {t.value}
                    </button>
                  ))}
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
                <AccordionContent className="pb-3 space-y-1.5">
                  <Select
                    value={params.operator_id ? String(params.operator_id) : "_all"}
                    onValueChange={(v) => setFilter({ operator_id: v === "_all" ? null : parseInt(v) })}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Any operator" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_all" className="text-xs text-muted-foreground">Any operator</SelectItem>
                      {filterData.operators.map((op) => (
                        <SelectItem key={op.id} value={String(op.id)} className="text-xs">{op.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </AccordionContent>
              </AccordionItem>
            )}

            {/* Access Type */}
            <AccordionItem value="access" className="border-none">
              <AccordionTrigger className="text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground hover:no-underline py-3 px-1">
                Access Type
              </AccordionTrigger>
              <AccordionContent className="pb-3 flex gap-2">
                {(filterData?.access_types ?? ["public", "captive"]).map((a) => (
                  <button
                    key={a}
                    onClick={() => setFilter({ access_type: params.access_type === a ? null : a })}
                    className={cn(
                      "flex-1 h-7 rounded-md border text-xs capitalize transition-colors",
                      params.access_type === a
                        ? "bg-primary text-primary-foreground border-primary"
                        : "border-border bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    {a}
                  </button>
                ))}
              </AccordionContent>
            </AccordionItem>

          </Accordion>
          </>
        )}
      </ScrollArea>
    </div>
  );
}
