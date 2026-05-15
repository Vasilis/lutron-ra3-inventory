import { describe, expect, it } from "vitest";
import type { Area, Device, Zone } from "@/lib/types";
import {
  deviceDisplayName,
  deviceGroupKey,
  groupAdjacentDevices,
} from "@/features/inventory/helpers";

const area: Area = {
  href: "/area/1",
  Name: "Kitchen",
  Parent: null,
};
const zone: Zone = {
  href: "/zone/1",
  Name: "Island Pendants",
  ControlType: "Dimmed",
  Category: null,
  Device: null,
  AssociatedArea: { href: area.href },
};

function device(overrides: Partial<Device> = {}): Device {
  return {
    href: "/device/1",
    Name: "Position 1",
    DeviceType: "SunnataDimmer",
    ModelNumber: null,
    SerialNumber: null,
    FirmwareImage: null,
    AssociatedArea: { href: area.href },
    AssociatedControlStation: null,
    LocalZones: [],
    ButtonGroups: [],
    AddressedState: null,
    ...overrides,
  };
}

describe("inventory helpers", () => {
  it("prefers the controlled zone name over Position N placeholders", () => {
    const title = deviceDisplayName(
      device({ LocalZones: [{ href: zone.href }] }),
      new Map([[area.href, area]]),
      new Map([[zone.href, zone]]),
    );

    expect(title).toBe("Island Pendants");
  });

  it("groups physical gang members by control station rather than display name", () => {
    const first = device({
      href: "/device/1",
      AssociatedControlStation: { href: "/controlstation/1" },
      LocalZones: [{ href: zone.href }],
    });
    const second = device({
      href: "/device/2",
      Name: "Position 2",
      AssociatedControlStation: { href: "/controlstation/1" },
    });

    expect(deviceGroupKey(first)).toBe(deviceGroupKey(second));
    expect(
      groupAdjacentDevices(
        [first, second],
        new Map([[area.href, area]]),
        new Map([[zone.href, zone]]),
      ),
    ).toHaveLength(1);
  });
});
