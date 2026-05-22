import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  availability: string | null;
  className?: string;
}

export function StatusBadge({ availability, className }: StatusBadgeProps) {
  const available = availability === "Available";
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border",
      available
        ? "bg-green-500/10 text-green-400 border-green-500/20"
        : "bg-amber-500/10 text-amber-400 border-amber-500/20",
      className
    )}>
      <span className={cn("w-1.5 h-1.5 rounded-full", available ? "bg-green-400" : "bg-amber-400")} />
      {available ? "Available" : "Unavailable"}
    </span>
  );
}
