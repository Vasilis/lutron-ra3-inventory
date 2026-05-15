import { useState } from "react";
import { Download, Settings } from "lucide-react";
import { BackendStatus } from "@/components/BackendStatus";
import { Button } from "@/components/ui/button";
import { ExportDialog } from "@/features/export/ExportDialog";
import { SettingsDialog } from "@/features/settings/SettingsDialog";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";

interface AppShellProps {
  left?: React.ReactNode;
  center?: React.ReactNode;
  right?: React.ReactNode;
  children?: React.ReactNode;
}

/**
 * Top-level shell — header with status pill + Export + Settings, then
 * either a three-pane main (left/center/right) or a single-column
 * children area for the welcome / startup states.
 *
 * Export and Settings dialogs are owned here so the rest of the app
 * doesn't have to plumb their open state through.
 */
export function AppShell({ left, center, right, children }: AppShellProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const activeProfileSerial = useAppStore((s) => s.activeProfileSerial);
  const hasThreePane = left !== undefined && center !== undefined;

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <header className="flex h-14 items-center justify-between border-b border-border px-6">
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
          <Button
            variant="ghost"
            size="icon"
            aria-label={t("settings.label")}
            onClick={() => setSettingsOpen(true)}
          >
            <Settings className="size-4" />
          </Button>
        </div>
      </header>

      {hasThreePane ? (
        <main className="grid flex-1 grid-cols-[18rem_1fr_24rem] overflow-hidden">
          <aside className="overflow-y-auto border-r border-border bg-card/30">
            {left}
          </aside>
          <section className="overflow-y-auto">{center}</section>
          <aside className="overflow-y-auto border-l border-border bg-card/30">
            {right}
          </aside>
        </main>
      ) : (
        <main className="flex-1 overflow-y-auto">{children}</main>
      )}

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      <ExportDialog open={exportOpen} onOpenChange={setExportOpen} />
    </div>
  );
}
