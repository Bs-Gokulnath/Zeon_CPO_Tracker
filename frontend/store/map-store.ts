import { create } from "zustand";

interface MapStore {
  center:           [number, number];
  zoom:             number;
  selectedId:       number | null;
  setCenter:        (c: [number, number], z?: number) => void;
  selectStation:    (id: number | null) => void;
}

export const useMapStore = create<MapStore>((set) => ({
  center:        [20.5937, 78.9629],  // India center
  zoom:          5,
  selectedId:    null,
  setCenter:     (c, z) => set({ center: c, ...(z != null && { zoom: z }) }),
  selectStation: (id) => set({ selectedId: id }),
}));
