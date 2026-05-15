import { useEffect } from "react";
import { useAppStore } from "@/stores/app-store";

/**
 * Applies the active theme to ``<html>`` (adds/removes the .dark class).
 * Honors "system" by listening to ``prefers-color-scheme``.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useAppStore((s) => s.theme);

  useEffect(() => {
    const root = window.document.documentElement;

    const applyResolved = (resolved: "light" | "dark") => {
      root.classList.remove("light", "dark");
      root.classList.add(resolved);
    };

    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      applyResolved(mq.matches ? "dark" : "light");
      const onChange = (e: MediaQueryListEvent) =>
        applyResolved(e.matches ? "dark" : "light");
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    }
    applyResolved(theme);
  }, [theme]);

  return <>{children}</>;
}
