import { useMemo } from "react";
import { ArrowUpCircle, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAppStore } from "@/stores/app-store";
import { cn } from "@/lib/utils";
import type { Area, Device, Zone } from "@/lib/types";
import {
  areaPath,
  deviceDisplayName,
  firmwareUpdate,
  groupAdjacentDevices,
  hasPositionName,
} from "@/features/inventory/helpers";
import { deviceCategoryIcon } from "@/features/inventory/icons";
import { t } from "@/i18n";

interface DeviceListProps {
  devices: Device[];
  areasByHref: Map<string, Area>;
  zonesByHref: Map<string, Zone>;
  onExtract: () => void;
  isExtracting: boolean;
  extractedAt: string;
  deviceCount: number;
  zoneCount: number;
}

/**
 * Middle pane — list of devices for the selected area (or every device
 * when "All areas" is selected). Adjacent devices that share both their
 * display name and DeviceType — typically a multi-gang of Sunnata
 * dimmers in one room — are wrapped in a thin bordered card so the
 * cluster reads as one unit rather than three identical-looking rows.
 */
export function DeviceList({
  devices,
  areasByHref,
  zonesByHref,
  onExtract,
  isExtracting,
  extractedAt,
  deviceCount,
  zoneCount,
}: DeviceListProps) {
  const selected = useAppStore((s) => s.selectedDeviceHref);
  const setSelected = useAppStore((s) => s.setSelectedDeviceHref);

  const groups = useMemo(
    () => groupAdjacentDevices(devices, areasByHref, zonesByHref),
    [devices, areasByHref, zonesByHref],
  );

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
        {devices.length === 0 ? (
          <div className="p-12 text-center text-sm text-muted-foreground">
            {t("inventory.empty_area")}
          </div>
        ) : (
          <div className="flex flex-col gap-1.5 px-3 py-3">
            {groups.map((g) =>
              g.devices.length === 1 ? (
                <DeviceRow
                  key={g.devices[0]!.href}
                  device={g.devices[0]!}
                  areasByHref={areasByHref}
                  zonesByHref={zonesByHref}
                  active={selected === g.devices[0]!.href}
                  onSelect={() => setSelected(g.devices[0]!.href)}
                />
              ) : (
                <div
                  key={g.key}
                  className="overflow-hidden rounded-lg border-2 border-border bg-card/30"
                >
                  {g.devices.map((d, i) => (
                    <div
                      key={d.href}
                      className={cn(
                        i > 0 && "border-t border-border/60",
                      )}
                    >
                      <DeviceRow
                        device={d}
                        areasByHref={areasByHref}
                        zonesByHref={zonesByHref}
                        active={selected === d.href}
                        onSelect={() => setSelected(d.href)}
                        inGroup
                      />
                    </div>
                  ))}
                </div>
              ),
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

interface DeviceRowProps {
  device: Device;
  areasByHref: Map<string, Area>;
  zonesByHref: Map<string, Zone>;
  active: boolean;
  onSelect: () => void;
  /** True when this row is inside a multi-device group card. Compact spacing. */
  inGroup?: boolean;
}

function DeviceRow({
  device: d,
  areasByHref,
  zonesByHref,
  active,
  onSelect,
  inGroup,
}: DeviceRowProps) {
  const Icon = deviceCategoryIcon(d.DeviceType);
  const update = firmwareUpdate(d.FirmwareImage);
  const title = deviceDisplayName(d, areasByHref, zonesByHref);
  const positionTag = hasPositionName(d) ? d.Name : null;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-3 px-4 text-left transition-colors",
        inGroup ? "py-2" : "py-3",
        !inGroup && "rounded-lg",
        active ? "bg-accent" : "hover:bg-accent/40",
      )}
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-4" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="flex items-center gap-2 truncate text-sm font-medium">
          {title}
          {positionTag && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-normal uppercase tracking-wide text-muted-foreground">
              {positionTag}
            </span>
          )}
          {update && (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-500"
              title={`Update available: ${update.installed} → ${update.available}`}
            >
              <ArrowUpCircle className="size-3" />
              Update
            </span>
          )}
        </span>
        <span className="truncate text-xs text-muted-foreground">
          {d.DeviceType}
          {d.ModelNumber ? ` · ${d.ModelNumber}` : ""}
        </span>
      </div>
      {!inGroup && (
        <span className="hidden text-xs text-muted-foreground md:block">
          {areaPath(d.AssociatedArea?.href ?? null, areasByHref)}
        </span>
      )}
    </button>
  );
}
