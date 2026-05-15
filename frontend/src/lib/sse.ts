/**
 * EventSource subscription helper.
 *
 * Native ``EventSource`` doesn't support custom headers, so we pass the
 * session token via the query string (``?token=…``) — the backend's
 * ``require_session`` dependency accepts both header and query auth.
 *
 * ``subscribeSse`` returns a cleanup function. The handler receives the
 * parsed JSON for each event named in ``events`` (defaults to a small set
 * covering all phases for both pairing and extraction streams).
 */

import { getSessionToken } from "@/lib/api";

const DEFAULT_EVENT_NAMES = [
  // pairing
  "starting",
  "ready",
  "discovering",
  "success",
  "error",
  "timeout",
  // extraction
  "connecting",
  "toplevel",
  "devices",
  "zones",
  "buttongroup_expanded",
  "programming_models",
  "presets",
  "indexing",
  "done",
];

export interface SseSubscription {
  close: () => void;
}

export interface SseOptions<T> {
  url: string;
  /** Event names to listen for. Defaults to a union of pair + extract phases. */
  events?: readonly string[];
  /** Called with the JSON-parsed payload for each event. */
  onEvent: (event: T) => void;
  onError?: (err: Event) => void;
}

export function subscribeSse<T>({
  url,
  events = DEFAULT_EVENT_NAMES,
  onEvent,
  onError,
}: SseOptions<T>): SseSubscription {
  // Attach the session token to the URL.
  const sep = url.includes("?") ? "&" : "?";
  const token = getSessionToken();
  const withToken = token ? `${url}${sep}token=${encodeURIComponent(token)}` : url;

  const es = new EventSource(withToken);

  const handler = (e: MessageEvent) => {
    if (!e.data) return;
    try {
      onEvent(JSON.parse(e.data) as T);
    } catch (err) {
      console.warn("malformed SSE payload", e.data, err);
    }
  };

  for (const name of events) {
    es.addEventListener(name, handler);
  }

  es.onerror = (e) => {
    onError?.(e);
    // EventSource auto-reconnects on its own; we close it ourselves when the
    // caller is done, or on a terminal-looking event the caller filters.
  };

  return {
    close: () => es.close(),
  };
}
