import type { Area, Device, DeviceFirmwareImage } from "@/lib/types";

export interface FirmwareUpdate {
  installed: string;
  available: string;
}

/** Resolve an area href to its " > "-joined parent chain. Cycle-safe. */
export function areaPath(
  href: string | null,
  areasByHref: Map<string, Area>,
): string {
  if (!href) return "(unassigned)";
  const parts: string[] = [];
  const seen = new Set<string>();
  let cur: string | null | undefined = href;
  while (cur && areasByHref.has(cur) && !seen.has(cur)) {
    seen.add(cur);
    const area: Area = areasByHref.get(cur)!;
    parts.push(area.Name ?? "?");
    cur = area.Parent?.href ?? null;
  }
  return parts.length ? parts.reverse().join(" > ") : "(unassigned)";
}

/**
 * Get the firmware display name across both known shapes.
 *
 *  - Older firmware: ``FirmwareImage.Firmware.DisplayName``
 *  - RA 3 26.x+:     ``FirmwareImage.Contents[0].OS.Firmware.DisplayName``
 */
export function firmwareDisplay(fw: DeviceFirmwareImage | null): string | null {
  if (!fw) return null;
  if (fw.Firmware?.DisplayName) return fw.Firmware.DisplayName;
  const contents = fw.Contents ?? [];
  for (const item of contents) {
    const name = item?.OS?.Firmware?.DisplayName;
    if (name) return name;
  }
  return null;
}

/**
 * Detect a pending firmware update by comparing the installed firmware
 * version to ``AvailableForUpload`` across every FirmwareImage.Contents
 * slot (OS + Boot). Returns the first slot whose installed and available
 * versions differ, or ``null`` if every slot is up to date.
 *
 * Firmware version display strings are opaque to us (Lutron's own
 * "DisplayName"); we only compare for inequality.
 */
export function firmwareUpdate(fw: DeviceFirmwareImage | null): FirmwareUpdate | null {
  if (!fw?.Contents) return null;
  for (const item of fw.Contents) {
    for (const slot of [item.OS, item.Boot]) {
      const installed = slot?.Firmware?.DisplayName;
      const available = slot?.AvailableForUpload?.DisplayName;
      if (installed && available && installed !== available) {
        return { installed, available };
      }
    }
  }
  return null;
}

export function countDevicesWithFirmwareUpdates(devices: Device[]): number {
  let n = 0;
  for (const d of devices) {
    if (firmwareUpdate(d.FirmwareImage)) n += 1;
  }
  return n;
}
