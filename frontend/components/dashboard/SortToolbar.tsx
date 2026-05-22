"use client";

import { ChevronLeft, ChevronRight, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

const SORT_OPTIONS = [
  { label: "Rating",           value: "rating" },
  { label: "Power (High)",     value: "power" },
  { label: "Price (Low)",      value: "price_asc" },
  { label: "Price (High)",     value: "price_desc" },
  { label: "Name",             value: "name" },
  { label: "Most Connectors",  value: "connector_count" },
];

interface SortToolbarProps {
  total:      number;
  sortBy:     string;
  loading?:   boolean;
  page:       number;
  totalPages: number;
  onSort:     (v: string) => void;
  onPage:     (p: number) => void;
}

export function SortToolbar({ total, sortBy, loading, page, totalPages, onSort, onPage }: SortToolbarProps) {
  const currentSort = SORT_OPTIONS.find((o) => o.value === sortBy)?.label ?? "Sort";

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-border/50 shrink-0">
      <p className="text-sm text-muted-foreground shrink-0">
        {loading ? (
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Loading…
          </span>
        ) : (
          <><span className="font-semibold text-foreground">{total.toLocaleString()}</span> stations</>
        )}
      </p>

      <div className="flex-1" />

      {/* Pagination controls */}
      {totalPages > 1 && (
        <div className="flex items-center gap-1.5">
          <Button
            variant="outline" size="sm"
            disabled={page <= 1}
            onClick={() => onPage(page - 1)}
            className="h-7 w-7 p-0"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </Button>
          <span className="text-xs text-muted-foreground tabular-nums">
            <span className="font-medium text-foreground">{page}</span>
            {" / "}
            <span className="font-medium text-foreground">{totalPages}</span>
          </span>
          <Button
            variant="outline" size="sm"
            disabled={page >= totalPages}
            onClick={() => onPage(page + 1)}
            className="h-7 w-7 p-0"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </Button>
        </div>
      )}

      {/* Sort */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1.5 h-8 text-xs">
            <SlidersHorizontal className="w-3.5 h-3.5" />
            {currentSort}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-44">
          {SORT_OPTIONS.map((o) => (
            <DropdownMenuItem
              key={o.value}
              onClick={() => onSort(o.value)}
              className={cn("text-xs cursor-pointer", sortBy === o.value && "text-primary font-medium")}
            >
              {o.label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
