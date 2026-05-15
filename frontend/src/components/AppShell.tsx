import { Settings } from "lucide-react";
import { BackendStatus } from "@/components/BackendStatus";
import { Button } from "@/components/ui/button";
import { t } from "@/i18n";

interface AppShellProps {
  left?: React.ReactNode;
  center?: React.ReactNode;
  right?: React.ReactNode;
  children?: React.ReactNode;
}

/**
 * Top-level three-pane layout shell.
 *
 * Layout:
 *   ┌─────────────────────────────────────────────────────┐
 *   │  RA3 Inventory          [status pill]   [⚙]         │
 *   ├──────────┬────────────────────────┬─────────────────┤
 *   │  Areas   │  Devices (selected     │  Detail (selected
 *   │  tree    │  area's contents)      │  device's fields)
 *   │          │                        │
 *   └──────────┴────────────────────────┴─────────────────┘
 *
 * When ``children`` is supplied (e.g. the welcome screen before any profile
 * exists), the three-pane area is replaced by it.
 */
export function AppShell({ left, center, right, children }: AppShellProps) {
  const hasThreePane = left !== undefined && center !== undefined;

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <header className="flex h-14 items-center justify-between border-b border-border px-6">
        <div className="flex items-center gap-3">
          <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <span className="text-[11px] font-bold">RA3</span>
          </div>
          <span className="text-sm font-semibold tracking-tight">{t("app.title")}</span>
        </div>
        <div className="flex items-center gap-3">
          <BackendStatus />
          <Button variant="ghost" size="icon" aria-label="Settings">
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
    </div>
  );
}
