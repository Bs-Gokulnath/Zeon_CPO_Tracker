import { create } from "zustand";

interface CompareStore {
  ids:    number[];
  add:    (id: number) => void;
  remove: (id: number) => void;
  clear:  () => void;
}

export const useCompareStore = create<CompareStore>((set) => ({
  ids:    [],
  add:    (id) => set((s) => ({ ids: s.ids.includes(id) ? s.ids : [...s.ids.slice(-2), id] })),
  remove: (id) => set((s) => ({ ids: s.ids.filter((i) => i !== id) })),
  clear:  () => set({ ids: [] }),
}));
