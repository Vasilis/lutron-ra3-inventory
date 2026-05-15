import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";
import { cn } from "@/lib/utils";
import { t } from "@/i18n";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const THEMES = ["light", "dark", "system"] as const;

/**
 * Cog → simple settings panel.
 *
 * For M1: theme switcher and a small "About" block. Snapshot/log dir
 * paths are platform-specific; we show the macOS canonical paths since
 * that's what we ship today.
 */
export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const version = useQuery({
    queryKey: ["version"],
    queryFn: () => api.version(),
    enabled: open,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("settings.title")}</DialogTitle>
          <DialogDescription>
            App-level preferences and version info.
          </DialogDescription>
        </DialogHeader>

        <section className="flex flex-col gap-2">
          <Label>{t("settings.theme")}</Label>
          <div className="flex gap-2">
            {THEMES.map((th) => (
              <Button
                key={th}
                size="sm"
                variant={theme === th ? "default" : "outline"}
                onClick={() => setTheme(th)}
                className={cn("flex-1")}
              >
                {t(`settings.theme.${th}`)}
              </Button>
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-3 border-t border-border pt-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">
              {t("settings.version")}
            </span>
            <span className="font-mono">
              {version.data ? `v${version.data.app_version}` : "…"}
            </span>
          </div>
          <div className="flex items-start justify-between gap-3">
            <span className="text-muted-foreground">
              {t("settings.snapshots_dir")}
            </span>
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
              ~/Library/Application Support/RA3Inventory/
            </code>
          </div>
        </section>

        <p className="rounded-md bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">
          {t("settings.firmware_note")}
        </p>
      </DialogContent>
    </Dialog>
  );
}
