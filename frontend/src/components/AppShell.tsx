import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Settings } from "lucide-react";
import { BackendStatus } from "@/components/BackendStatus";
import { Button } from "@/components/ui/button";
import { ExportDialog } from "@/features/export/ExportDialog";
import { SettingsDialog } from "@/features/settings/SettingsDialog";
import { countDevicesWithFirmwareUpdates } from "@/features/inventory/helpers";
import { ApiError, api } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";
import { cn } from "@/lib/utils";
import { t } from "@/i18n";

interface AppShellProps {
  left?: React.ReactNode;
  center?: React.ReactNode;
  right?: React.ReactNode;
  children?: React.ReactNode;
}

/**
 * Top-level shell — header with status pill + Export + Settings, then
 * either a three-pane main (left/center/right) or a single-column area
 * for welcome / startup states.
 *
 * Scroll handling: the main element is ``overflow-hidden`` so children
 * own their own scroll containers. The InventoryBrowser uses internal
 * ScrollAreas per pane; the welcome/startup screens wrap themselves in
 * ``overflow-y-auto`` if they ever grow taller than the viewport.
 */
export function AppShell({ left, center, right, children }: AppShellProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const activeProfileSerial = useAppStore((s) => s.activeProfileSerial);
  const hasThreePane = left !== undefined && center !== undefined;

  // Count of devices with firmware updates available — drives the small
  // amber badge on the gear icon (iMessage-style unread count). The query
  // shares the same cache key as InventoryBrowser, so we don't fetch
  // twice; if no profile is active or no snapshot exists, the badge is
  // hidden.
  const inventoryQuery = useQuery({
    queryKey: ["inventory"],
    queryFn: () => api.getInventory(),
    enabled: Boolean(activeProfileSerial),
    retry: (count, err) => {
      if (err instanceof ApiError && err.status === 404) return false;
      return count < 1;
    },
  });
  const firmwareUpdateCount = inventoryQuery.data
    ? countDevicesWithFirmwareUpdates(inventoryQuery.data.devices)
    : 0;

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6">
        <div className="flex items-center gap-3">
          <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <span className="text-[11px] font-bold">RA3</span>
          </div>
          <span className="text-sm font-semibold tracking-tight">
            {t("app.title")}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <BackendStatus />
          {activeProfileSerial && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExportOpen(true)}
              className="gap-1.5"
            >
              <Download className="size-4" />
              {t("export.label")}
            </Button>
          )}
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              aria-label={t("settings.label")}
              onClick={() => setSettingsOpen(true)}
            >
              <Settings className="size-4" />
            </Button>
            {firmwareUpdateCount > 0 && (
              <span
                className={cn(
                  "pointer-events-none absolute -right-0.5 -top-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-semibold leading-none text-background ring-2 ring-background",
                )}
                title={`${firmwareUpdateCount} device${firmwareUpdateCount === 1 ? "" : "s"} with firmware updates`}
                aria-label={`${firmwareUpdateCount} firmware updates available`}
              >
                {firmwareUpdateCount > 9 ? "9+" : firmwareUpdateCount}
              </span>
            )}
          </div>
        </div>
      </header>

      {hasThreePane ? (
        <main className="grid min-h-0 flex-1 grid-cols-[18rem_1fr_24rem] overflow-hidden">
          <aside className="min-h-0 overflow-hidden border-r border-border bg-card/30">
            {left}
          </aside>
          <section className="min-h-0 overflow-hidden">{center}</section>
          <aside className="min-h-0 overflow-hidden border-l border-border bg-card/30">
            {right}
          </aside>
        </main>
      ) : (
        <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
      )}

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      <ExportDialog open={exportOpen} onOpenChange={setExportOpen} />
    </div>
  );
}
