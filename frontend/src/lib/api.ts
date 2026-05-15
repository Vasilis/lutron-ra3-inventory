/**
 * Tiny token-aware fetch wrapper for the FastAPI backend.
 *
 * The session token is set once on page load by reading ``?token=…`` from
 * the URL (the PyWebView entry point passes it there) and is then sent on
 * every subsequent request via ``X-RA3-Token``. The token is held in
 * sessionStorage so a webview reload doesn't lose it.
 */

const TOKEN_STORAGE_KEY = "ra3-session-token";

function captureTokenFromUrl(): string | null {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token) {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    // Clean it off the URL so it doesn't sit in the history.
    const url = new URL(window.location.href);
    url.searchParams.delete("token");
    window.history.replaceState({}, "", url.toString());
    return token;
  }
  return null;
}

function getToken(): string | null {
  return captureTokenFromUrl() ?? sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail?: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("X-RA3-Token", token);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const resp = await fetch(path, { ...init, headers });
  if (!resp.ok) {
    let detail: unknown;
    try {
      detail = await resp.json();
    } catch {
      detail = await resp.text().catch(() => undefined);
    }
    const message =
      (detail as { detail?: string } | undefined)?.detail ??
      `${resp.status} ${resp.statusText}`;
    throw new ApiError(resp.status, message, detail);
  }
  if (resp.status === 204) return undefined as T;
  const contentType = resp.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await resp.json()) as T;
  }
  return (await resp.text()) as unknown as T;
}

import type { ProcessorInventory, ProfileSummary } from "@/lib/types";

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),
  version: () =>
    request<{ app_version: string; schema_version: number }>("/version"),
  listProfiles: () => request<ProfileSummary[]>("/profiles"),
  activateProfile: (serial: string) =>
    request<void>(`/profiles/${encodeURIComponent(serial)}/activate`, {
      method: "POST",
    }),
  deleteProfile: (serial: string) =>
    request<void>(`/profiles/${encodeURIComponent(serial)}`, {
      method: "DELETE",
    }),
  startPairing: (host: string, name: string, disk_passphrase?: string) =>
    request<{ pair_id: string }>("/pair/start", {
      method: "POST",
      body: JSON.stringify({ host, name, disk_passphrase }),
    }),
  startExtraction: (
    profile_serial: string,
    capture_raw = false,
    disk_passphrase?: string,
  ) =>
    request<{ extract_id: string }>("/extract", {
      method: "POST",
      body: JSON.stringify({ profile_serial, capture_raw, disk_passphrase }),
    }),
  getInventory: () => request<ProcessorInventory>("/inventory"),
};

/** Build an SSE URL that subscribeSse() can consume. */
export function pairEventsUrl(pairId: string): string {
  return `/pair/events?pair_id=${encodeURIComponent(pairId)}`;
}

export function extractEventsUrl(extractId: string): string {
  return `/extract/events?extract_id=${encodeURIComponent(extractId)}`;
}

export function getSessionToken(): string | null {
  return getToken();
}
