import { create } from "zustand";

interface UIStore {
  // kept minimal — sidebar is always visible, no drawer
}

export const useUIStore = create<UIStore>(() => ({}));
