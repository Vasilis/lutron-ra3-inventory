import { Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAppStore } from "@/stores/app-store";
import { cn } from "@/lib/utils";
import type { Area, Device } from "@/lib/types";
import { areaPath } from "@/features/inventory/helpers";
import { deviceCategoryIcon } from "@/features/inventory/icons";
import { t } from "@/i18n";

interface DeviceListProps {
  devices: Device[];
  areasByHref: Map<string, Area>;
  onExtract: () => void;
  isExtracting: boolean;
  extractedAt: string;
  deviceCount: number;
  zoneCount: number;
}

/**
 * Middle pane — the list of devices for the selected area (or all if no
 * area is selected). One device per row with its name, type, model, and
 * a category icon. Selecting a device fills the right detail pane.
 */
export function DeviceList({
  devices,
  areasByHref,
  onExtract,
  isExtracting,
  extractedAt,
  deviceCount,
  zoneCount,
}: DeviceListProps) {
  const selected = useAppStore((s) => s.selectedDeviceHref);
  const setSelected = useAppStore((s) => s.setSelectedDeviceHref);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <div className="flex flex-col gap-0.5">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            {t("nav.devices")}
          </div>
          <div className="text-sm">
            {t("inventory.visible_counts", {
              visible: devices.length,
              devices: deviceCount,
              zones: zoneCount,
            })}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            {t("inventory.snapshot_at", {
              timestamp: new Date(extractedAt).toLocaleString(),
            })}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={onExtract}
            disabled={isExtracting}
          >
            {isExtracting ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                {t("extract.running")}
              </>
            ) : (
              <>
                <RefreshCw className="size-3.5" />
                {t("inventory.refresh")}
              </>
            )}
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <ul className="flex flex-col divide-y divide-border/60">
          {devices.length === 0 ? (
            <li className="p-12 text-center text-sm text-muted-foreground">
              {t("inventory.empty_area")}
            </li>
          ) : (
            devices.map((d) => {
              const active = selected === d.href;
              const Icon = deviceCategoryIcon(d.DeviceType);
              return (
                <li key={d.href}>
                  <button
                    type="button"
                    onClick={() => setSelected(d.href)}
                    className={cn(
                      "flex w-full items-center gap-3 px-5 py-3 text-left transition-colors",
                      active ? "bg-accent" : "hover:bg-accent/40",
                    )}
                  >
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="size-4" />
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-sm font-medium">
                        {d.Name ?? d.DeviceType}
                      </span>
                      <span className="truncate text-xs text-muted-foreground">
                        {d.DeviceType}
                        {d.ModelNumber ? ` · ${d.ModelNumber}` : ""}
                      </span>
                    </div>
                    <span className="hidden text-xs text-muted-foreground md:block">
                      {areaPath(d.AssociatedArea?.href ?? null, areasByHref)}
                    </span>
                  </button>
                </li>
              );
            })
          )}
        </ul>
      </ScrollArea>
    </div>
  );
}
