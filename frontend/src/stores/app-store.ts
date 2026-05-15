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

  /** Mirror of ``config.active_profile_serial`` on the backend. */
  activeProfileSerial: string | null;
  setActiveProfileSerial: (serial: string | null) => void;

  /** True while an extraction's progress toast is on-screen. */
  isExtracting: boolean;
  setIsExtracting: (running: boolean) => void;

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

      activeProfileSerial: null,
      setActiveProfileSerial: (serial) => set({ activeProfileSerial: serial }),

      isExtracting: false,
      setIsExtracting: (running) => set({ isExtracting: running }),

      selectedAreaHref: null,
      setSelectedAreaHref: (href) =>
        set({ selectedAreaHref: href, selectedDeviceHref: null }),

      selectedDeviceHref: null,
      setSelectedDeviceHref: (href) => set({ selectedDeviceHref: href }),
    }),
    {
      name: "ra3-app-state",
      // Only theme persists; pairing state lives on the backend and the
      // extracting flag is transient.
      partialize: (state) => ({ theme: state.theme }),
    },
  ),
);
