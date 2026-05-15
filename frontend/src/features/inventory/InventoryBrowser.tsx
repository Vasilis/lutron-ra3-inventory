import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/stores/app-store";
import type { Area, Device } from "@/lib/types";
import { t } from "@/i18n";
import { ApiError } from "@/lib/api";
import { AreaTree } from "./AreaTree";
import { DeviceList } from "./DeviceList";
import { DeviceDetail } from "./DeviceDetail";
import { deviceDisplayName, devicePositionNumber } from "./helpers";

interface InventoryBrowserProps {
  onExtract: () => void;
  isExtracting: boolean;
}

/**
 * Three-pane inventory browser.
 *
 *  - Loads ``GET /inventory`` (the active profile's latest snapshot).
 *  - 404 here means the user has paired but never extracted yet → show
 *    an "Extract now" prompt.
 *  - Anything else → render the tree / list / detail.
 */
export function InventoryBrowser({
  onExtract,
  isExtracting,
}: InventoryBrowserProps) {
  const selectedAreaHref = useAppStore((s) => s.selectedAreaHref);
  const selectedDeviceHref = useAppStore((s) => s.selectedDeviceHref);

  const inventory = useQuery({
    queryKey: ["inventory"],
    queryFn: () => api.getInventory(),
    retry: (count, err) => {
      if (err instanceof ApiError && err.status === 404) return false;
      return count < 1;
    },
  });

  // Index areas by href for parent-path lookups; index devices by area.
  const { areasByHref, devicesByArea } = useMemo(() => {
    const areasByHref = new Map<string, Area>();
    const devicesByArea = new Map<string | null, Device[]>();
    if (inventory.data) {
      for (const a of inventory.data.areas) areasByHref.set(a.href, a);
      for (const d of inventory.data.devices) {
        const k = d.AssociatedArea?.href ?? null;
        const bucket = devicesByArea.get(k) ?? [];
        bucket.push(d);
        devicesByArea.set(k, bucket);
      }
    }
    return { areasByHref, devicesByArea };
  }, [inventory.data]);

  if (inventory.isPending) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
        {t("inventory.loading")}
      </div>
    );
  }

  if (inventory.isError) {
    const err = inventory.error;
    const is404 = err instanceof ApiError && err.status === 404;
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-12 text-center">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-muted">
          {is404 ? (
            <RefreshCw className="size-5" />
          ) : (
            <AlertCircle className="size-5 text-destructive" />
          )}
        </div>
        <h2 className="text-lg font-semibold">
          {is404 ? t("inventory.no_snapshot_title") : t("inventory.load_error")}
        </h2>
        <p className="max-w-md text-sm text-muted-foreground">
          {is404
            ? t("inventory.no_snapshot_body")
            : err instanceof Error
              ? err.message
              : t("inventory.unknown_error")}
        </p>
        <Button onClick={onExtract} disabled={isExtracting} className="mt-2">
          {isExtracting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              {t("extract.running")}
            </>
          ) : (
            <>
              <RefreshCw className="size-4" />
              {t("extract.start")}
            </>
          )}
        </Button>
      </div>
    );
  }

  const inv = inventory.data;
  const visibleDevices = (
    selectedAreaHref ? (devicesByArea.get(selectedAreaHref) ?? []) : inv.devices
  )
    .slice()
    .sort((a, b) => {
      // 1. Group by display name (area name for "Position N" devices,
      //    real name otherwise).
      const nameCmp = deviceDisplayName(a, areasByHref).localeCompare(
        deviceDisplayName(b, areasByHref),
        undefined,
        { sensitivity: "base", numeric: true },
      );
      if (nameCmp !== 0) return nameCmp;
      // 2. Cluster by device type within the same display name —
      //    keypads next to keypads, dimmers next to dimmers, shades
      //    next to shades, all in the same area's block.
      const typeCmp = a.DeviceType.localeCompare(b.DeviceType);
      if (typeCmp !== 0) return typeCmp;
      // 3. Order by numeric position within a gang so "Position 2"
      //    comes before "Position 10", not after "Position 1".
      return devicePositionNumber(a) - devicePositionNumber(b);
    });
  const selectedDevice = selectedDeviceHref
    ? (inv.devices.find((d) => d.href === selectedDeviceHref) ??
      (inv.processor.href === selectedDeviceHref ? inv.processor : null))
    : null;

  return (
    <div className="grid h-full min-h-0 grid-cols-[18rem_1fr_24rem] divide-x divide-border overflow-hidden">
      <div className="min-h-0 overflow-hidden">
        <AreaTree
          areas={inv.areas}
          areasByHref={areasByHref}
          devicesByArea={devicesByArea}
        />
      </div>
      <div className="min-h-0 overflow-hidden">
        <DeviceList
          devices={visibleDevices}
          areasByHref={areasByHref}
          onExtract={onExtract}
          isExtracting={isExtracting}
          extractedAt={inv.extracted_at}
          deviceCount={inv.devices.length}
          zoneCount={inv.zones.length}
        />
      </div>
      <div className="min-h-0 overflow-hidden">
        <DeviceDetail
          device={selectedDevice}
          areasByHref={areasByHref}
          zones={inv.zones}
          buttonGroupExpansions={inv.button_group_expansions}
        />
      </div>
    </div>
  );
}
