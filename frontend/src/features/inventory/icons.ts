import type { LucideIcon } from "lucide-react";
import {
  Box,
  Fan,
  Lightbulb,
  Plug,
  Power,
  Sun,
  Thermometer,
  Wifi,
} from "lucide-react";
import {
  FourGroupRemoteIcon,
  PicoIcon,
  ProcessorIcon,
  ShadeIcon,
  SunnataDimmerIcon,
  SunnataHybridKeypadIcon,
  SunnataKeypadIcon,
  TunableLightIcon,
} from "@/components/lutron-icons";

type IconComponent =
  | LucideIcon
  | ((props: { className?: string }) => JSX.Element);

const SHADE_TYPES = [
  "PalladiomShade",
  "PalladiomWireFreeShade",
  "SivoiaQsTriathlonRollerShade",
  "SivoiaQsTriathlonHoneycombShade",
  "SivoiaQsTriathlonVenetianBlind",
  "TriathlonRollerShade",
  "TriathlonEssentialsRollerShade",
  "TriathlonHoneycombShade",
  "TriathlonTiltOnlyWoodBlind",
  "SerenaCellularShade",
  "SerenaRollerShade",
  "SerenaTiltOnlyWoodBlind",
  "SerenaEssentialsRollerShade",
  "QsWirelessShade",
  "QsWiredShade",
  "QsWirelessHorizontalSheerBlind",
  "QsWirelessWoodBlind",
  "RightDrawDrape",
  "Shade",
  "Tilt",
] as const;

const KEYPAD_TYPES = [
  "SunnataKeypad",
  "SunnataHybridKeypad",
  "SeeTouchKeypad",
  "SeeTouchHybridKeypad",
  "PalladiomKeypad",
  "AlisseKeypad",
  "PhantomKeypad",
  "HomeownerKeypad",
  "GrafikTHybridKeypad",
] as const;

const PICO_TYPES = [
  "Pico1Button",
  "Pico2Button",
  "Pico2ButtonRaiseLower",
  "Pico3Button",
  "Pico3ButtonRaiseLower",
  "Pico4Button",
  "Pico4ButtonScene",
  "Pico4ButtonZone",
  "Pico4Button2Group",
  "PaddleSwitchPico",
  "FourGroupRemote",
] as const;

const DIMMER_TYPES = [
  "WallDimmer",
  "PlugInDimmer",
  "InLineDimmer",
  "SunnataDimmer",
  "DivaSmartDimmer",
  "WallDimmerWithPreset",
] as const;

const SWITCH_TYPES = [
  "WallSwitch",
  "PlugInSwitch",
  "InLineSwitch",
  "SunnataSwitch",
  "DivaSmartSwitch",
] as const;

const FAN_TYPES = [
  "CasetaFanSpeedController",
  "MaestroFanSpeedController",
] as const;

const SENSOR_TYPES = [
  "RPSOccupancySensor",
  "RPSCeilingMountedOccupancySensor",
  "RPSWallMountedOccupancySensor",
] as const;

const LAMP_TYPES = [
  "KetraD3",
  "SpectrumTune",
  "WhiteTune",
  "ColorTune",
  "Lumaris",
] as const;

export function deviceCategoryIcon(deviceType: string): IconComponent {
  if (deviceType === "RadioRa3Processor" || deviceType === "JanusProcRA3")
    return ProcessorIcon;
  if (
    deviceType === "FourGroupRemote" ||
    deviceType === "CasetaFourGroupRemote"
  )
    return FourGroupRemoteIcon;
  if (deviceType === "SunnataHybridKeypad") return SunnataHybridKeypadIcon;
  if (deviceType === "SunnataKeypad") return SunnataKeypadIcon;
  if (deviceType === "SunnataDimmer") return SunnataDimmerIcon;
  if ((KEYPAD_TYPES as readonly string[]).includes(deviceType))
    return SunnataKeypadIcon;
  if ((PICO_TYPES as readonly string[]).includes(deviceType)) return PicoIcon;
  if ((SHADE_TYPES as readonly string[]).includes(deviceType)) return ShadeIcon;
  if (deviceType === "Lumaris") return TunableLightIcon;
  if ((LAMP_TYPES as readonly string[]).includes(deviceType)) return Sun;
  if ((DIMMER_TYPES as readonly string[]).includes(deviceType))
    return Lightbulb;
  if ((SWITCH_TYPES as readonly string[]).includes(deviceType)) return Power;
  if ((FAN_TYPES as readonly string[]).includes(deviceType)) return Fan;
  if ((SENSOR_TYPES as readonly string[]).includes(deviceType))
    return Thermometer;
  if (deviceType === "KeypadLED") return Wifi;
  if (deviceType.endsWith("Plug")) return Plug;
  return Box;
}
