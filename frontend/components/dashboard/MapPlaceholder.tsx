"use client";

import { Layers, Maximize2, Minus, Plus, Navigation } from "lucide-react";

const FAKE_MARKERS = [
  // Delhi cluster
  { top: 22, left: 43, type: "available",   size: "lg" },
  { top: 23, left: 44, type: "unavailable", size: "sm" },
  { top: 21, left: 42, type: "available",   size: "sm" },
  // Mumbai
  { top: 52, left: 34, type: "available",   size: "lg" },
  { top: 53, left: 33, type: "unavailable", size: "sm" },
  // Bengaluru
  { top: 65, left: 44, type: "available",   size: "md" },
  { top: 66, left: 45, type: "available",   size: "sm" },
  // Chennai
  { top: 68, left: 49, type: "unavailable", size: "md" },
  { top: 69, left: 50, type: "available",   size: "sm" },
  // Hyderabad
  { top: 60, left: 46, type: "available",   size: "md" },
  // Pune
  { top: 55, left: 37, type: "available",   size: "sm" },
  // Kolkata
  { top: 38, left: 60, type: "available",   size: "md" },
  { top: 39, left: 61, type: "unavailable", size: "sm" },
  // Ahmedabad
  { top: 40, left: 33, type: "available",   size: "sm" },
  // Jaipur
  { top: 30, left: 40, type: "available",   size: "sm" },
  // Chandigarh
  { top: 17, left: 41, type: "unavailable", size: "sm" },
  // Lucknow
  { top: 29, left: 50, type: "available",   size: "sm" },
  // Bhopal
  { top: 42, left: 43, type: "available",   size: "sm" },
  // Nagpur
  { top: 47, left: 47, type: "unavailable", size: "sm" },
  // Kochi
  { top: 73, left: 41, type: "available",   size: "md" },
] as const;

const sizeClass = { sm: "w-2 h-2", md: "w-2.5 h-2.5", lg: "w-3.5 h-3.5" };

export function MapPlaceholder() {
  return (
    <div className="relative w-full h-full min-h-[340px] bg-slate-950 overflow-hidden rounded-none">
      {/* Grid pattern */}
      <svg className="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-slate-500" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* India outline hint — simple ellipse */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div
          className="opacity-[0.04] border-2 border-slate-300"
          style={{
            width: "35%",
            height: "65%",
            borderRadius: "48% 52% 60% 40% / 40% 50% 50% 60%",
            transform: "rotate(-5deg) translateY(-5%)",
          }}
        />
      </div>

      {/* Fake markers */}
      {FAKE_MARKERS.map((m, i) => (
        <div
          key={i}
          className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group/marker"
          style={{ top: `${m.top}%`, left: `${m.left}%` }}
        >
          {/* Pulse ring on available large markers */}
          {m.type === "available" && m.size === "lg" && (
            <span className="absolute inset-0 rounded-full animate-ping bg-green-400 opacity-30" />
          )}
          <div className={`
            ${sizeClass[m.size]} rounded-full border-2 transition-transform group-hover/marker:scale-150
            ${m.type === "available"
              ? "bg-green-400 border-green-300 shadow-[0_0_6px_rgba(74,222,128,0.6)]"
              : "bg-amber-400 border-amber-300 shadow-[0_0_6px_rgba(251,191,36,0.6)]"
            }
          `} />
        </div>
      ))}

      {/* Cluster indicator */}
      <div
        className="absolute transform -translate-x-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-primary/80 border-2 border-primary text-primary-foreground text-xs font-bold flex items-center justify-center shadow-lg cursor-pointer hover:scale-110 transition-transform"
        style={{ top: "22%", left: "43.5%" }}
      >
        12
      </div>

      {/* Loading shimmer overlay */}
      <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-primary to-transparent opacity-60 animate-pulse" />

      {/* Map controls — right side */}
      <div className="absolute right-3 top-3 flex flex-col gap-1">
        {[Plus, Minus, Layers, Navigation].map((Icon, i) => (
          <button
            key={i}
            className="w-8 h-8 rounded-md bg-card/90 border border-border/50 backdrop-blur flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-card transition-colors"
            tabIndex={-1}
          >
            <Icon className="w-3.5 h-3.5" />
          </button>
        ))}
      </div>

      {/* Fullscreen button */}
      <button className="absolute right-3 bottom-3 w-8 h-8 rounded-md bg-card/90 border border-border/50 backdrop-blur flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors">
        <Maximize2 className="w-3.5 h-3.5" />
      </button>

      {/* Attribution */}
      <div className="absolute bottom-3 left-3 text-[10px] text-muted-foreground/50 select-none">
        © Statiq EV Intelligence · Map placeholder
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-card/80 backdrop-blur border border-border/50 rounded-lg px-3 py-1.5">
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-green-400" /> Available
        </span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-amber-400" /> Unavailable
        </span>
      </div>
    </div>
  );
}
