/**
 * Optional bridge to the Python side of PyWebView.
 *
 * When the app is running inside PyWebView the Python entry point binds a
 * ``JsApi`` instance to ``window.pywebview.api`` that exposes:
 *
 *   - ``save_file(filename: string, content_b64: string) -> {ok, path?, error?}``
 *   - ``copy_text(text: string) -> {ok, error?}``
 *
 * These exist because WKWebView in the bundled webview doesn't honor
 * ``<a download>`` and blocks ``navigator.clipboard.writeText`` by
 * default. When we run in a regular browser (or if the bridge isn't
 * ready yet) every helper here returns ``null`` so callers can fall
 * back to web-standard alternatives.
 *
 * ``pywebview.api`` is attached late (after PyWebView's bootstrap), so
 * we re-check ``window.pywebview`` on every call rather than caching.
 */

interface PyWebViewApi {
  save_file: (
    filename: string,
    content_b64: string,
  ) => Promise<{ ok: boolean; path?: string; error?: string }>;
  copy_text: (text: string) => Promise<{ ok: boolean; error?: string }>;
}

declare global {
  interface Window {
    pywebview?: { api?: PyWebViewApi };
  }
}

function api(): PyWebViewApi | null {
  return window.pywebview?.api ?? null;
}

export function isPyWebView(): boolean {
  return api() !== null;
}

/** Base64-encode a UTF-8 string. ``btoa`` only handles Latin-1. */
function toBase64Utf8(s: string): string {
  const bytes = new TextEncoder().encode(s);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

/** Base64-encode raw bytes (e.g. for binary export formats). */
async function blobToBase64(blob: Blob): Promise<string> {
  const buf = await blob.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let bin = "";
  // Chunk to avoid stack overflow on large blobs.
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(bin);
}

export interface SaveResult {
  ok: boolean;
  /** Absolute path the file was written to, when ok=true. */
  path?: string;
  /** Reason text — "cancelled" if the user dismissed the save dialog. */
  error?: string;
}

/**
 * Open a native save dialog and write ``payload`` to disk.
 *
 * ``payload`` may be a string or a Blob; binary blobs are base64-encoded
 * before being shuttled over the bridge. Returns ``null`` if the bridge
 * isn't available — caller should fall back to the standard Web API
 * download path.
 */
export async function saveFileNative(
  filename: string,
  payload: string | Blob,
): Promise<SaveResult | null> {
  const bridge = api();
  if (!bridge?.save_file) return null;
  const content_b64 =
    typeof payload === "string" ? toBase64Utf8(payload) : await blobToBase64(payload);
  return bridge.save_file(filename, content_b64);
}

/** Put ``text`` on the native clipboard via NSPasteboard. */
export async function copyTextNative(text: string): Promise<boolean> {
  const bridge = api();
  if (!bridge?.copy_text) return false;
  const result = await bridge.copy_text(text);
  return Boolean(result?.ok);
}

/**
 * Copy text to the clipboard, trying the native bridge first, then
 * ``navigator.clipboard``, finally a hidden-textarea + execCommand
 * fallback. Returns true if any path succeeded.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (await copyTextNative(text)) return true;
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // fall through to execCommand path
    }
  }
  // Last-ditch fallback — works in WebKit even without permissions.
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.top = "-9999px";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  document.body.removeChild(ta);
  return ok;
}
