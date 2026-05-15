/**
 * TypeScript mirrors of the backend's Pydantic models.
 *
 * Hand-written for M1; will be generated from the FastAPI OpenAPI schema
 * via openapi-typescript once we wire that into the build.
 */

export interface HrefRef {
  href: string;
}

export interface FirmwareInfo {
  DisplayName: string | null;
}

export interface InstalledDate {
  Year: number | null;
  Month: number | null;
  Day: number | null;
}

export interface DeviceFirmwareImage {
  Firmware: FirmwareInfo | null;
  Installed: InstalledDate | null;
  // Newer firmware shape (26.x+) lives under model_extra:
  Contents?: Array<{ OS?: { Firmware?: FirmwareInfo } }>;
}

export interface NetworkInterface {
  InterfaceType: string | null;
  MACAddress: string | null;
  IPv4Address: string | null;
  IsPrimary: boolean | null;
}

export interface Area {
  href: string;
  Name: string | null;
  Parent: HrefRef | null;
}

export interface ZoneCategory {
  Type: string | null;
  SubType: string | null;
  IsLight: boolean | null;
}

export interface Zone {
  href: string;
  Name: string | null;
  ControlType: string | null;
  Category: ZoneCategory | null;
  Device: HrefRef | null;
  AssociatedArea: HrefRef | null;
}

export interface Device {
  href: string;
  Name: string | null;
  DeviceType: string;
  ModelNumber: string | null;
  SerialNumber: number | string | null;
  FirmwareImage: DeviceFirmwareImage | null;
  AssociatedArea: HrefRef | null;
  AssociatedControlStation: HrefRef | null;
  LocalZones: HrefRef[];
  ButtonGroups: HrefRef[];
  AddressedState: string | null;
  // Processor-only:
  NetworkInterfaces?: NetworkInterface[];
}

export interface ButtonEngraving {
  Text: string | null;
}

export interface Button {
  href: string;
  Name: string | null;
  ButtonNumber: number | null;
  ButtonType: string | null;
  Engraving: ButtonEngraving | null;
  ProgrammingModel: HrefRef | null;
  AssociatedLED: HrefRef | null;
}

export interface ButtonGroup {
  href: string;
  Name: string | null;
  ProgrammingType: string | null;
  Buttons: Button[] | null;
}

export interface Project {
  href: string;
  Name: string | null;
  ProductType: string | null;
  ProjectModifiedTimestamp: string | Record<string, unknown> | null;
}

export interface ProcessorInventory {
  schema_version: 1;
  extracted_at: string;
  source: "live" | "fixture" | "import";
  host: string;
  duration_seconds: number;
  partial: boolean;
  processor: Device;
  project: Project;
  areas: Area[];
  devices: Device[];
  zones: Zone[];
  buttons: Button[];
  button_groups: ButtonGroup[];
  control_stations: unknown[];
  area_scenes: unknown[];
  virtual_buttons: unknown[];
  timeclock_event_rules: unknown[];
  button_group_expansions: Record<string, ButtonGroup[]>;
  programming_models: Record<string, unknown>;
  presets: Record<string, unknown>;
}

export interface ProfileSummary {
  serial: string;
  name: string;
  host: string;
  last_seen: string | null;
  firmware: string | null;
  has_certs: boolean;
}

export type PairPhase =
  | "starting"
  | "ready"
  | "discovering"
  | "success"
  | "error"
  | "timeout";

export interface PairEvent {
  phase: PairPhase;
  detail?: string;
  serial?: string;
  name?: string;
  host?: string;
  firmware?: string;
  error?: string;
}

export type ExtractPhase =
  | "connecting"
  | "toplevel"
  | "devices"
  | "zones"
  | "buttongroup_expanded"
  | "programming_models"
  | "presets"
  | "indexing"
  | "done"
  | "success"
  | "error";

export interface ExtractEvent {
  phase: ExtractPhase;
  detail?: string;
  progress?: number;
  error?: string;
  kind?: "already_connected";
}
