import type { Area, DeviceFirmwareImage } from "@/lib/types";

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
