import { Star } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ReviewSummaryOut } from "@/types/station";

interface Props { summary: ReviewSummaryOut | null }

export function ReviewSummary({ summary }: Props) {
  if (!summary || summary.review_count === 0) return null;

  const avg   = summary.avg_rating ? parseFloat(summary.avg_rating) : 0;
  const total = summary.review_count;

  const bars = [
    { stars: 5, count: summary.rating_5_count },
    { stars: 4, count: summary.rating_4_count },
    { stars: 3, count: summary.rating_3_count },
    { stars: 2, count: summary.rating_2_count },
    { stars: 1, count: summary.rating_1_count },
  ];

  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
        Reviews
      </h2>
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center gap-8">
          {/* Aggregate score */}
          <div className="text-center shrink-0">
            <div className="text-5xl font-bold tabular-nums leading-none">
              {avg.toFixed(1)}
            </div>
            <div className="flex items-center justify-center gap-0.5 mt-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star
                  key={i}
                  className={cn(
                    "w-3.5 h-3.5",
                    i < Math.round(avg)
                      ? "fill-amber-400 text-amber-400"
                      : "text-muted-foreground/40"
                  )}
                />
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {total.toLocaleString()} review{total !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Distribution bars */}
          <div className="flex-1 space-y-2">
            {bars.map(({ stars, count }) => {
              const pct = total > 0 ? (count / total) * 100 : 0;
              return (
                <div key={stars} className="flex items-center gap-2 text-xs">
                  <span className="w-2 text-right text-muted-foreground shrink-0">{stars}</span>
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400 shrink-0" />
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-400 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-5 text-right text-muted-foreground shrink-0">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
