/**
 * Minimal i18n shim — flat key/value catalog with ``{var}`` interpolation.
 *
 * Designed to be replaceable by react-i18next or react-intl later without
 * churning component code. All user-facing strings go through ``t()``; the
 * components never embed English literals.
 */

import enCatalog from "./en.json";

type Catalog = Record<string, string>;

let activeCatalog: Catalog = enCatalog;

export function setLocale(catalog: Catalog): void {
  activeCatalog = catalog;
}

export function t(key: string, vars?: Record<string, string | number>): string {
  let value = activeCatalog[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      value = value.replaceAll(`{${k}}`, String(v));
    }
  }
  return value;
}
