export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { DashboardShell } from "./DashboardShell";
import { Skeleton }       from "@/components/ui/skeleton";

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardFallback />}>
      <DashboardShell />
    </Suspense>
  );
}

function DashboardFallback() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="h-14 border-b border-border/50 bg-background/80" />
      <div className="flex flex-1 overflow-hidden">
        <div className="hidden lg:flex w-[272px] shrink-0 border-r border-border/50">
          <div className="flex flex-col h-full p-4 gap-3 w-full">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full rounded-lg" />
            ))}
          </div>
        </div>
        <div className="flex flex-col flex-1 min-w-0 p-4 gap-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-[96px] rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-10 w-full rounded-lg" />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-[200px] rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
