import type { Area, Device, DeviceFirmwareImage, Zone } from "@/lib/types";

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
export function firmwareUpdate(
  fw: DeviceFirmwareImage | null,
): FirmwareUpdate | null {
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
 * Best-effort meaningful label for a device.
 *
 * Priority:
 *   1. A real ``device.Name`` (anything that isn't Lutron's default
 *      ``Position N`` placeholder).
 *   2. The name of the single zone this device controls, when it has
 *      exactly one ``LocalZones`` entry. Zone names are integrator-set
 *      and tend to be the most meaningful label in the whole database
 *      ("Kitchen Island Pendants", "Living Room Sconces"), so this is
 *      what dimmers / switches / shades / fans get.
 *   3. The parent area's name — used for keypads, picos, remotes, and
 *      sensors (no LocalZones), and for multi-zone devices where
 *      picking one zone would be misleading.
 *   4. Falls all the way back to the raw name / DeviceType when even
 *      the area lookup fails.
 *
 * ``zonesByHref`` is optional so callers that don't have a zones index
 * can still resolve labels — they just skip step 2.
 */
export function deviceDisplayName(
  device: Device,
  areasByHref: Map<string, Area>,
  zonesByHref?: Map<string, Zone>,
): string {
  const raw = device.Name ?? device.DeviceType;
  if (raw && !POSITION_PATTERN.test(raw)) return raw;

  // One zone — use its name.
  if (zonesByHref && device.LocalZones.length === 1) {
    const z = zonesByHref.get(device.LocalZones[0]!.href);
    if (z?.Name) return z.Name;
  }

  // Fall through to area name.
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

export interface DeviceGroup {
  /** Stable React key for the group. */
  key: string;
  /** All devices in the group, in their already-sorted order. */
  devices: Device[];
  /** Display name of the group (zone/area name of the first device). */
  displayName: string;
  /** Shared DeviceType. */
  deviceType: string;
}

/**
 * Stable key for "which gang does this device belong to."
 *
 *  - When ``AssociatedControlStation`` is set, that href + DeviceType
 *    becomes the key. A multi-gang Sunnata keypad set all sharing one
 *    control station collapses into a single group even if each
 *    position resolves to a different zone-name label.
 *  - Wireless devices (Picos, sensors, the processor) have no control
 *    station — they get a unique ``solo:<href>`` key so they never
 *    group with anyone else.
 *
 * Splitting on DeviceType means a gang that mixes a dimmer and a
 * keypad renders as two adjacent boxes rather than one mixed box.
 */
export function deviceGroupKey(d: Device): string {
  const cs = d.AssociatedControlStation?.href;
  return cs ? `gang:${cs}:${d.DeviceType}` : `solo:${d.href}`;
}

/**
 * Cluster adjacent devices that share their ``deviceGroupKey`` into a
 * single group. Used by the device list so the visual treatment of a
 * multi-gang set of dimmers/keypads/shades is a thin border around the
 * run rather than a bare succession of similar-looking rows.
 *
 * Expects ``devices`` to be already sorted by their group key — see
 * InventoryBrowser's sort. Devices with the same key but separated by
 * an unrelated device in between will form *two* groups, not one.
 */
export function groupAdjacentDevices(
  devices: Device[],
  areasByHref: Map<string, Area>,
  zonesByHref?: Map<string, Zone>,
): DeviceGroup[] {
  const out: DeviceGroup[] = [];
  for (const d of devices) {
    const key = deviceGroupKey(d);
    const displayName = deviceDisplayName(d, areasByHref, zonesByHref);
    const last = out[out.length - 1];
    if (last && last.key === key) {
      last.devices.push(d);
    } else {
      out.push({
        key,
        devices: [d],
        displayName,
        deviceType: d.DeviceType,
      });
    }
  }
  return out;
}
