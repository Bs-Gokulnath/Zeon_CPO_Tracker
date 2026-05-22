"use client";

import { useEffect, useRef, useState } from "react";
import { type LucideIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function useCountUp(target: number, duration = 1000): number {
  const [count, setCount] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (!target || target === prevTarget.current) return;
    prevTarget.current = target;

    const start = performance.now();
    let rafId: number;

    const step = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      setCount(Math.round(eased * target));
      if (progress < 1) rafId = requestAnimationFrame(step);
      else setCount(target);
    };

    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [target, duration]);

  return count;
}

interface KPICardProps {
  label:     string;
  value:     number;
  icon:      LucideIcon;
  iconColor: string;
  subtext?:  string;
  loading?:  boolean;
}

export const KPICard = function KPICard({
  label, value, icon: Icon, iconColor, subtext, loading,
}: KPICardProps) {
  const animated = useCountUp(loading ? 0 : value);

  if (loading) {
    return (
      <div className="bg-card border border-border rounded-xl p-4 space-y-3">
        <Skeleton className="h-8 w-8 rounded-lg" />
        <Skeleton className="h-7 w-20" />
        <Skeleton className="h-4 w-24" />
      </div>
    );
  }

  return (
    <div className="group bg-card border border-border rounded-xl p-4 hover:border-primary/30 hover:shadow-md hover:shadow-primary/5 transition-all duration-200 space-y-3">
      <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center", iconColor)}>
        <Icon className="w-4 h-4" strokeWidth={2} />
      </div>
      <div>
        <p className="text-2xl font-bold tracking-tight tabular-nums">
          {animated.toLocaleString()}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
        {subtext && <p className="text-xs text-primary mt-1">{subtext}</p>}
      </div>
    </div>
  );
};
