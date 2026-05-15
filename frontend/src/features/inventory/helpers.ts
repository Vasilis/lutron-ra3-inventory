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

const POSITION_PATTERN = /^Position\s+\d+$/i;

/**
 * Lutron defaults the ``Name`` field on ganged devices to ``Position 1``,
 * ``Position 2``, etc. — fine for the integrator (it matches the physical
 * slot in the gang) but useless at a glance. When we detect the fallback
 * we substitute the parent area's name so the row reads "Den" instead of
 * "Position 1". The position is still surfaced as a small grey tag next
 * to the title so the disambiguation isn't lost.
 */
export function deviceDisplayName(
  device: Device,
  areasByHref: Map<string, Area>,
): string {
  const raw = device.Name ?? device.DeviceType;
  if (!POSITION_PATTERN.test(raw)) return raw;
  const area = device.AssociatedArea?.href
    ? areasByHref.get(device.AssociatedArea.href)
    : null;
  if (area?.Name) return area.Name;
  return raw;
}

/** True when ``device.Name`` is Lutron's default ganged-position placeholder. */
export function hasPositionName(device: Device): boolean {
  return device.Name ? POSITION_PATTERN.test(device.Name) : false;
}

/**
 * Extract the numeric position from a Lutron ``Position N`` name. Used as
 * the tertiary sort key so multiple dimmers/keypads in the same gang sort
 * 1 → 2 → 3 → 10 rather than the lexicographic 1 → 10 → 2.
 *
 * Returns ``Number.MAX_SAFE_INTEGER`` for devices with no position name —
 * keeps named devices sorted after their numbered siblings.
 */
export function devicePositionNumber(device: Device): number {
  if (!device.Name) return Number.MAX_SAFE_INTEGER;
  const m = device.Name.match(/^Position\s+(\d+)$/i);
  return m ? Number.parseInt(m[1], 10) : Number.MAX_SAFE_INTEGER;
}
