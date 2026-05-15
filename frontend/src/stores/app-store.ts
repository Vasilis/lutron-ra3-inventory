/**
 * Top-level app state.
 *
 * Theme persists to localStorage; active profile is mirrored from the
 * backend's config.json so the source of truth stays server-side.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark" | "system";

interface AppState {
  theme: Theme;
  setTheme: (theme: Theme) => void;

  selectedAreaHref: string | null;
  setSelectedAreaHref: (href: string | null) => void;

  selectedDeviceHref: string | null;
  setSelectedDeviceHref: (href: string | null) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: "dark",
      setTheme: (theme) => set({ theme }),

      selectedAreaHref: null,
      setSelectedAreaHref: (href) =>
        set({ selectedAreaHref: href, selectedDeviceHref: null }),

      selectedDeviceHref: null,
      setSelectedDeviceHref: (href) => set({ selectedDeviceHref: href }),
    }),
    {
      name: "ra3-app-state",
      partialize: (state) => ({ theme: state.theme }),
    },
  ),
);
