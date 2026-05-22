// Filter state lives in URL (nuqs). This store holds UI-only filter panel state.
import { create } from "zustand";

interface FilterPanelStore {
  activeSection: string | null;
  setActiveSection: (s: string | null) => void;
}

export const useFilterPanelStore = create<FilterPanelStore>((set) => ({
  activeSection:    null,
  setActiveSection: (s) => set({ activeSection: s }),
}));
