/**
 * Lutron-product-shaped icons.
 *
 * These are stylized silhouettes drawn from scratch in the same line-art
 * style as Lucide — not copies of Lutron's copyrighted artwork. They give
 * the inventory list a more product-recognizable feel than generic Lucide
 * substitutes (ToggleLeft for a keypad, Radio for a pico, etc.).
 *
 * All icons take a ``className`` prop sized like Lucide (defaults to 24×24
 * via ``size-4``/``size-5`` etc.). Stroke + fill use ``currentColor`` so
 * Tailwind's text-color classes still drive them.
 */

import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement>;

function base(extraProps: Props) {
  const { className, ...rest } = extraProps;
  return {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    ...rest,
  };
}

/** Sunnata-style hybrid keypad: tall faceplate, four square buttons stacked,
 *  a small LED dot to the side of each one. */
export function SunnataKeypadIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="5" y="2" width="14" height="20" rx="2" />
      {/* Four buttons */}
      <rect x="8" y="5" width="9" height="3" rx="0.6" />
      <rect x="8" y="9" width="9" height="3" rx="0.6" />
      <rect x="8" y="13" width="9" height="3" rx="0.6" />
      <rect x="8" y="17" width="9" height="3" rx="0.6" />
      {/* LED indicator dots on the left edge of each button */}
      <circle cx="7" cy="6.5" r="0.4" fill="currentColor" />
      <circle cx="7" cy="10.5" r="0.4" fill="currentColor" />
      <circle cx="7" cy="14.5" r="0.4" fill="currentColor" />
      <circle cx="7" cy="18.5" r="0.4" fill="currentColor" />
    </svg>
  );
}

/** Sunnata-style 3-button keypad with raise/lower. */
export function SunnataHybridKeypadIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="5" y="2" width="14" height="20" rx="2" />
      {/* Three scene buttons */}
      <rect x="8" y="4.5" width="9" height="3" rx="0.6" />
      <rect x="8" y="8.5" width="9" height="3" rx="0.6" />
      <rect x="8" y="12.5" width="9" height="3" rx="0.6" />
      {/* Raise / lower row */}
      <path d="M9 18l3-2 3 2" />
      <path d="M9 20.5l3 -2 3 2" transform="rotate(180 12 19.5)" />
      {/* LEDs */}
      <circle cx="7" cy="6" r="0.4" fill="currentColor" />
      <circle cx="7" cy="10" r="0.4" fill="currentColor" />
      <circle cx="7" cy="14" r="0.4" fill="currentColor" />
    </svg>
  );
}

/** Sunnata-style single-paddle dimmer: large rocker + small LED bar. */
export function SunnataDimmerIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="5" y="2" width="14" height="20" rx="2" />
      {/* Large paddle rocker */}
      <rect x="8" y="5" width="9" height="11" rx="1.2" />
      <line x1="8" y1="10.5" x2="17" y2="10.5" />
      {/* LED bar at bottom */}
      <line x1="9" y1="19" x2="15" y2="19" strokeWidth="2" />
    </svg>
  );
}

/** Pico remote: small handheld, 3 round buttons + raise/lower bar in middle. */
export function PicoIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="6.5" y="2.5" width="11" height="19" rx="2.5" />
      {/* Top scene button */}
      <circle cx="12" cy="6" r="1.4" />
      {/* Middle raise/lower */}
      <rect x="9" y="9.5" width="6" height="5" rx="0.6" />
      <path d="M10 11.5l2 -1.5 2 1.5" />
      <path d="M10 12.5l2 1.5 2 -1.5" />
      {/* Bottom scene button */}
      <circle cx="12" cy="18" r="1.4" />
    </svg>
  );
}

/** Caseta 4-group scene remote (CS-YJ-4GC). Rectangular, four labeled
 *  buttons in a 2×2 grid. */
export function FourGroupRemoteIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="4" y="3" width="16" height="18" rx="2.5" />
      {/* 4 scene buttons in a 2x2 grid */}
      <rect x="6.5" y="6" width="4.5" height="4.5" rx="0.6" />
      <rect x="13" y="6" width="4.5" height="4.5" rx="0.6" />
      <rect x="6.5" y="12" width="4.5" height="4.5" rx="0.6" />
      <rect x="13" y="12" width="4.5" height="4.5" rx="0.6" />
      {/* Small off button at bottom */}
      <rect x="9" y="18" width="6" height="1.8" rx="0.4" />
    </svg>
  );
}

/** RA 3 processor: tall rack-like box with status LEDs along the front. */
export function ProcessorIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="3" y="4" width="18" height="16" rx="1.5" />
      {/* Status LED strip across the top */}
      <circle cx="6" cy="8" r="0.5" fill="currentColor" />
      <circle cx="8.5" cy="8" r="0.5" fill="currentColor" />
      <circle cx="11" cy="8" r="0.5" fill="currentColor" />
      <circle cx="13.5" cy="8" r="0.5" fill="currentColor" />
      <circle cx="16" cy="8" r="0.5" fill="currentColor" />
      {/* Two vent / port slots */}
      <line x1="6" y1="13" x2="18" y2="13" />
      <line x1="6" y1="16" x2="18" y2="16" />
    </svg>
  );
}

/** Palladiom-style shade: window frame with a roller pulled partway down. */
export function ShadeIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="3" y="3" width="18" height="18" rx="1" />
      {/* Roller bar at top */}
      <line x1="4" y1="6" x2="20" y2="6" strokeWidth="2.25" />
      {/* Hem bar partway down */}
      <line x1="6" y1="14" x2="18" y2="14" strokeWidth="2" />
      {/* Shade fabric lines */}
      <line x1="6" y1="8" x2="18" y2="8" opacity="0.6" />
      <line x1="6" y1="10" x2="18" y2="10" opacity="0.6" />
      <line x1="6" y1="12" x2="18" y2="12" opacity="0.6" />
    </svg>
  );
}

/** Lumaris-style tunable-white LED tape: horizontal strip with dots. */
export function TunableLightIcon(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="2.5" y="9" width="19" height="6" rx="1" />
      <circle cx="6" cy="12" r="0.7" fill="currentColor" />
      <circle cx="10" cy="12" r="0.7" fill="currentColor" />
      <circle cx="14" cy="12" r="0.7" fill="currentColor" />
      <circle cx="18" cy="12" r="0.7" fill="currentColor" />
    </svg>
  );
}
