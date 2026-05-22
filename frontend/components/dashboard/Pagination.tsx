"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PaginationProps {
  page:        number;
  totalPages:  number;
  total?:      number;
  onPage:      (p: number) => void;
}

export function Pagination({ page, totalPages, total, onPage }: PaginationProps) {
  if (totalPages <= 1 && !total) return null;

  return (
    <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-border/50 shrink-0">
      <span className="text-xs text-muted-foreground">
        {total != null ? (
          <>{total.toLocaleString()} total</>
        ) : null}
      </span>

      {totalPages > 1 && (
        <div className="flex items-center gap-2">
          <Button
            variant="outline" size="sm"
            disabled={page <= 1}
            onClick={() => onPage(page - 1)}
            className="h-7 w-7 p-0"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </Button>
          <span className="text-xs text-muted-foreground">
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
    </div>
  );
}
