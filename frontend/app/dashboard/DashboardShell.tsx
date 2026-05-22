"use client";

import { useCallback } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Navbar }           from "@/components/layout/Navbar";
import { Sidebar }          from "@/components/layout/Sidebar";
import { KPIRow }           from "@/components/dashboard/KPIRow";
import { StationGrid }      from "@/components/dashboard/StationGrid";
import { SortToolbar }      from "@/components/dashboard/SortToolbar";
import { Button }           from "@/components/ui/button";
import { useStations }      from "@/hooks/useStations";
import { useFiltersParams } from "@/hooks/useFiltersParams";

export function DashboardShell() {
  const {
    filters,
    params,
    setPage,
    setSortBy,
    clearFilters,
    activeFilterCount,
  } = useFiltersParams();

  const {
    data:       stationsData,
    isLoading:  stationsLoading,
    isFetching: stationsFetching,
    error:      stationsError,
    refetch:    refetchStations,
  } = useStations(filters);

  const stations   = stationsData?.data ?? [];
  const pageInfo   = stationsData?.page;
  const totalPages = pageInfo?.total_pages ?? 1;
  const total      = pageInfo?.total ?? 0;

  const handleClearFilters = useCallback(() => clearFilters(), [clearFilters]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <KPIRow stats={stationsData?.stats ?? null} loading={stationsLoading} />

          <SortToolbar
            total={total}
            sortBy={params.sort_by ?? "rating"}
            loading={stationsFetching && !stationsLoading}
            page={params.page ?? 1}
            totalPages={totalPages}
            onSort={setSortBy}
            onPage={setPage}
          />

          <div className="flex-1 overflow-y-auto">
            {stationsError ? (
              <ErrorPanel
                message={(stationsError as Error).message}
                onRetry={refetchStations}
              />
            ) : (
              <StationGrid
                stations={stations}
                loading={stationsLoading}
                onClear={activeFilterCount > 0 ? handleClearFilters : undefined}
              />
            )}
          </div>

        </div>
      </div>
    </div>
  );
}

function ErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <div className="text-center space-y-3 max-w-xs">
        <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center mx-auto">
          <AlertCircle className="w-5 h-5 text-destructive" />
        </div>
        <p className="text-sm font-medium">Failed to load stations</p>
        <p className="text-xs text-muted-foreground line-clamp-2">{message}</p>
        <Button size="sm" variant="outline" onClick={onRetry} className="gap-1.5">
          <RefreshCw className="w-3.5 h-3.5" />
          Try again
        </Button>
      </div>
    </div>
  );
}
