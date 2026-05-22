import { SidebarFilters } from "@/components/filters/SidebarFilters";

export function Sidebar() {
  return (
    <aside className="flex w-[320px] shrink-0 flex-col border-r border-border/50 bg-card/30 overflow-hidden">
      <SidebarFilters />
    </aside>
  );
}
