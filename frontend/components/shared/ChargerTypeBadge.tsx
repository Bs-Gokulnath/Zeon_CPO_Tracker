import { cn } from "@/lib/utils";

interface ChargerTypeBadgeProps {
  type: string | null;
  className?: string;
}

export function ChargerTypeBadge({ type, className }: ChargerTypeBadgeProps) {
  const styles: Record<string, string> = {
    AC:    "bg-blue-500/10 text-blue-400 border-blue-500/20",
    DC:    "bg-orange-500/10 text-orange-400 border-orange-500/20",
    Mixed: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  };
  return (
    <span className={cn(
      "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border",
      styles[type ?? ""] ?? "bg-muted text-muted-foreground border-border",
      className
    )}>
      {type ?? "—"}
    </span>
  );
}
