import { StationCard } from "./StationCard";
import { StationCardSkeleton } from "./StationCardSkeleton";
import { EmptyState } from "./EmptyState";
import type { StationSummary } from "@/types/station";

interface StationGridProps {
  stations: StationSummary[];
  loading?: boolean;
  onClear?: () => void;
}

export function StationGrid({ stations, loading, onClear }: StationGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <StationCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (stations.length === 0) {
    return <EmptyState onClear={onClear} />;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
      {stations.map((s) => (
        <StationCard key={s.id} station={s} />
      ))}
    </div>
  );
}
