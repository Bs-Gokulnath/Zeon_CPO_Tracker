"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap } from "lucide-react";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { ScrapeButton } from "@/components/layout/ScrapeButton";
import { SearchAutocomplete } from "@/components/search/SearchAutocomplete";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard",  label: "Dashboard" },
  { href: "/analytics",  label: "Analytics" },
  { href: "/maps",       label: "Maps"      },
  { href: "/compare",    label: "Compare"   },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 h-14 border-b border-border/50 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/75 flex items-center px-4 gap-3">
      {/* Logo */}
      <Link href="/dashboard" className="flex items-center gap-2 shrink-0">
        <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Zap className="w-3.5 h-3.5 text-primary" />
        </div>
        <span className="font-semibold text-sm hidden sm:inline">Zeon CPO Tracker</span>
      </Link>

      {/* Nav links — desktop */}
      <nav className="hidden lg:flex items-center gap-0.5 ml-3">
        {NAV_ITEMS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "px-3 py-1.5 rounded-md text-sm transition-colors",
              pathname.startsWith(href)
                ? "bg-accent text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            {label}
          </Link>
        ))}
      </nav>

      {/* Search with autocomplete */}
      <div className="flex-1 max-w-xs mx-auto">
        <SearchAutocomplete />
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        <ScrapeButton />
        <ThemeToggle />
      </div>
    </header>
  );
}
