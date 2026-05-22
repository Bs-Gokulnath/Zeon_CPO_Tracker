export function StationDetailSkeleton() {
  return (
    <div className="min-h-screen bg-background animate-pulse">
      <div className="h-14 border-b border-border/50 bg-background sticky top-0 z-50" />

      <div className="container max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Back link */}
        <div className="h-4 bg-muted rounded w-28" />

        {/* Hero */}
        <div className="rounded-xl overflow-hidden border border-border bg-card">
          <div className="h-40 bg-muted" />
          <div className="p-5 space-y-3">
            <div className="flex justify-between items-start">
              <div className="space-y-2 flex-1 pr-4">
                <div className="h-7 bg-muted rounded w-2/3" />
                <div className="h-4 bg-muted rounded w-1/2" />
                <div className="h-3 bg-muted rounded w-3/4" />
              </div>
              <div className="space-y-2 shrink-0">
                <div className="h-6 bg-muted rounded-full w-24" />
                <div className="h-4 bg-muted rounded w-20" />
              </div>
            </div>
            <div className="flex gap-2 pt-2 border-t border-border/50">
              <div className="h-9 bg-muted rounded-lg w-32" />
              <div className="h-9 bg-muted rounded-lg w-24" />
            </div>
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="space-y-3">
              <div className="h-4 bg-muted rounded w-36" />
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-border bg-card p-4 space-y-3">
                  <div className="flex justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-muted rounded-lg" />
                      <div className="space-y-1.5">
                        <div className="h-4 bg-muted rounded w-28" />
                        <div className="h-3 bg-muted rounded w-16" />
                      </div>
                    </div>
                    <div className="space-y-1 text-right">
                      <div className="h-4 bg-muted rounded w-16" />
                      <div className="h-3 bg-muted rounded w-14" />
                    </div>
                  </div>
                  <div className="flex gap-1.5 pt-2 border-t border-border/50">
                    {Array.from({ length: 3 }).map((_, j) => (
                      <div key={j} className="h-6 bg-muted rounded w-14" />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <div className="h-4 bg-muted rounded w-20" />
              <div className="h-[200px] bg-muted rounded-xl border border-border" />
            </div>
          </div>
        </div>

        {/* Nearby */}
        <div className="space-y-3">
          <div className="h-4 bg-muted rounded w-36" />
          <div className="flex gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="shrink-0 w-44 h-32 bg-muted rounded-xl border border-border" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
