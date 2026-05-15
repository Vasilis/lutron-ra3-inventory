import { ArrowUpCircle, Hash } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Area, ButtonGroup, Device, Zone } from "@/lib/types";
import {
  areaPath,
  firmwareDisplay,
  firmwareUpdate,
} from "@/features/inventory/helpers";
import { deviceCategoryIcon } from "@/features/inventory/icons";
import { t } from "@/i18n";

interface DeviceDetailProps {
  device: Device | null;
  areasByHref: Map<string, Area>;
  zones: Zone[];
  buttonGroupExpansions: Record<string, ButtonGroup[]>;
}

/**
 * Right pane — every field on the selected device, plus any expanded
 * button groups (for keypads/picos/remotes).
 */
export function DeviceDetail({
  device,
  areasByHref,
  zones,
  buttonGroupExpansions,
}: DeviceDetailProps) {
  if (!device) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center text-sm text-muted-foreground">
        <Hash className="size-4" />
        {t("inventory.select_device")}
      </div>
    );
  }

  const Icon = deviceCategoryIcon(device.DeviceType);
  const zonesByHref = new Map(zones.map((z) => [z.href, z]));
  const localZones = device.LocalZones.map((r) =>
    zonesByHref.get(r.href),
  ).filter((z): z is Zone => Boolean(z));
  const buttonGroups = buttonGroupExpansions[device.href];
  const update = firmwareUpdate(device.FirmwareImage);

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-6 p-6">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <Icon className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="flex items-center gap-2 truncate text-lg font-semibold">
              {device.Name ?? device.DeviceType}
              {update && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-500">
                  <ArrowUpCircle className="size-3" />
                  Update available
                </span>
              )}
            </h2>
            <p className="truncate text-xs text-muted-foreground">
              {device.DeviceType}
              {device.ModelNumber ? ` · ${device.ModelNumber}` : ""}
            </p>
          </div>
        </div>

        <DetailGrid
          rows={[
            [
              t("inventory.area"),
              areaPath(device.AssociatedArea?.href ?? null, areasByHref),
            ],
            [
              t("inventory.serial"),
              device.SerialNumber == null ? "—" : String(device.SerialNumber),
            ],
            [
              t("inventory.firmware"),
              firmwareDisplay(device.FirmwareImage) ?? "—",
            ],
            [t("inventory.addressed"), device.AddressedState ?? "—"],
            [t("inventory.href"), device.href],
          ]}
        />

        {update && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
            <div className="mb-1 flex items-center gap-2 font-medium text-amber-500">
              <ArrowUpCircle className="size-4" />
              Firmware update available
            </div>
            <div className="text-xs text-foreground/80">
              Installed <code className="font-mono">{update.installed}</code>
              {" → "}available <code className="font-mono">{update.available}</code>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              This app doesn't push firmware updates — initiate them from
              Lutron Designer or the official Lutron app.
            </p>
          </div>
        )}

        {localZones.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("nav.zones")}
            </h3>
            <ul className="flex flex-col gap-1 rounded-lg border border-border bg-card/40">
              {localZones.map((z) => (
                <li
                  key={z.href}
                  className="flex items-center justify-between px-3 py-2 text-sm"
                >
                  <span className="truncate">{z.Name ?? z.href}</span>
                  <span className="ml-3 text-xs text-muted-foreground">
                    {z.ControlType ?? ""}
                    {z.Category?.SubType ? ` · ${z.Category.SubType}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {buttonGroups && buttonGroups.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("inventory.buttons")}
            </h3>
            <ul className="flex flex-col gap-1 rounded-lg border border-border bg-card/40">
              {buttonGroups.flatMap((bg) =>
                (bg.Buttons ?? []).map((btn) => (
                  <li
                    key={btn.href}
                    className="grid grid-cols-[2.25rem_1fr_auto] items-center gap-2 px-3 py-2 text-sm"
                  >
                    <span className="text-xs tabular-nums text-muted-foreground">
                      #{btn.ButtonNumber ?? "?"}
                    </span>
                    <span className="truncate">
                      {btn.Engraving?.Text ??
                        btn.Name ??
                        t("inventory.unnamed")}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {btn.ButtonType ?? ""}
                    </span>
                  </li>
                )),
              )}
            </ul>
          </section>
        )}
      </div>
    </ScrollArea>
  );
}

function DetailGrid({ rows }: { rows: Array<[string, string]> }) {
  return (
    <dl className="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-2 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted-foreground">{k}</dt>
          <dd className="truncate font-medium">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
