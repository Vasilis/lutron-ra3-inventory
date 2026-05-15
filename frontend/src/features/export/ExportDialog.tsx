import { useEffect, useRef, useState } from "react";
import {
  Check,
  ClipboardCopy,
  FileCode,
  FileSpreadsheet,
  FileText,
  Loader2,
  Save,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { getSessionToken } from "@/lib/api";
import { copyToClipboard, isPyWebView, saveFileNative } from "@/lib/pywebview";
import { t } from "@/i18n";

type Format = "markdown" | "json" | "csv" | "xlsx";
type ExportPreset = "recovery" | "technical" | "share" | "custom";

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface SectionDef {
  key: string;
  i18nKey: string;
}

const SECTIONS: SectionDef[] = [
  { key: "header", i18nKey: "export.section.header" },
  { key: "processor", i18nKey: "export.section.processor" },
  { key: "summary", i18nKey: "export.section.summary" },
  { key: "device_types", i18nKey: "export.section.device_types" },
  { key: "areas", i18nKey: "export.section.areas" },
  { key: "devices", i18nKey: "export.section.devices" },
  { key: "zones", i18nKey: "export.section.zones" },
  { key: "keypads", i18nKey: "export.section.keypads" },
  { key: "virtual_buttons", i18nKey: "export.section.virtual_buttons" },
  { key: "area_scenes", i18nKey: "export.section.area_scenes" },
  { key: "timeclock", i18nKey: "export.section.timeclock" },
];

const ALL_SECTION_KEYS = new Set(SECTIONS.map((s) => s.key));

/** Recovery-essentials default — includes engravings for human reconstruction. */
const RECOVERY_DEFAULT_SECTIONS = new Set([
  "header",
  "processor",
  "areas",
  "devices",
  "zones",
  "keypads",
]);

const FORMAT_META: Record<
  Format,
  {
    label: string;
    icon: typeof FileText;
    path: string;
    filename: string;
    supportsSections: boolean;
    isText: boolean;
  }
> = {
  markdown: {
    label: "Markdown",
    icon: FileText,
    path: "/export/markdown",
    filename: "inventory.md",
    supportsSections: true,
    isText: true,
  },
  json: {
    label: "JSON",
    icon: FileCode,
    path: "/export/json",
    filename: "inventory.json",
    supportsSections: false,
    isText: true,
  },
  csv: {
    label: "CSV (zip)",
    icon: FileSpreadsheet,
    path: "/export/csv",
    filename: "inventory.zip",
    supportsSections: false,
    isText: false,
  },
  xlsx: {
    label: "Excel",
    icon: FileSpreadsheet,
    path: "/export/xlsx",
    filename: "inventory.xlsx",
    supportsSections: false,
    isText: false,
  },
};

type Status =
  | { kind: "idle" }
  | { kind: "generating" }
  | { kind: "saving" }
  | { kind: "copied" }
  | { kind: "saved"; path: string }
  | { kind: "error"; message: string };

/**
 * Export dialog with inline preview.
 *
 * Two-step flow:
 *   1. Configure: format, section checkboxes (Markdown only), Verbose toggle
 *   2. Click "Generate" → the dialog stays open and either shows the
 *      rendered content in an inline ``<textarea>`` (text formats), or
 *      flips straight to a Save button (binary formats).
 *
 * The "Save to file…" action calls into the PyWebView ``save_file`` JS
 * bridge — which opens a native macOS Cocoa save panel and writes the
 * content from Python — and falls back to a Blob-URL download in plain
 * browsers. The previous synthetic ``<a download>`` against the backend
 * URL navigated the webview to a content page with no back button; this
 * keeps everything in the dialog.
 *
 * "Copy" tries the PyWebView ``copy_text`` bridge first (NSPasteboard),
 * then ``navigator.clipboard.writeText``, then a hidden-textarea +
 * ``document.execCommand('copy')`` fallback. One of those always works
 * in WebKit even with no permissions.
 */
export function ExportDialog({ open, onOpenChange }: ExportDialogProps) {
  const [format, setFormat] = useState<Format>("markdown");
  const [preset, setPreset] = useState<ExportPreset>("recovery");
  const [selectedSections, setSelectedSections] = useState<Set<string>>(
    new Set(RECOVERY_DEFAULT_SECTIONS),
  );
  const [verbose, setVerbose] = useState(false);
  const [sanitized, setSanitized] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  /** Generated content: text for Markdown/JSON, Blob for CSV/XLSX. */
  const [textPreview, setTextPreview] = useState<string | null>(null);
  const [binaryBlob, setBinaryBlob] = useState<Blob | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const meta = FORMAT_META[format];
  const allSelected = selectedSections.size === SECTIONS.length;
  const noneSelected = selectedSections.size === 0;
  const inPyWebView = isPyWebView();

  // Reset content + status when the dialog closes or the configuration
  // changes — stale preview after the user re-ticks sections is worse
  // than no preview.
  useEffect(() => {
    if (!open) {
      setTextPreview(null);
      setBinaryBlob(null);
      setStatus({ kind: "idle" });
    }
  }, [open]);

  useEffect(() => {
    setTextPreview(null);
    setBinaryBlob(null);
    if (status.kind !== "idle" && status.kind !== "error") {
      setStatus({ kind: "idle" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [format, selectedSections, verbose, sanitized]);

  const applyPreset = (next: ExportPreset) => {
    setPreset(next);
    setFormat("markdown");
    if (next === "technical") {
      setSelectedSections(new Set(ALL_SECTION_KEYS));
      setVerbose(true);
      setSanitized(false);
      return;
    }
    setSelectedSections(new Set(RECOVERY_DEFAULT_SECTIONS));
    setVerbose(false);
    setSanitized(next === "share");
  };

  const toggle = (key: string) => {
    setPreset("custom");
    setSelectedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const setAll = (on: boolean) => {
    setPreset("custom");
    setSelectedSections(on ? new Set(ALL_SECTION_KEYS) : new Set());
  };

  const buildUrl = (): string => {
    const token = getSessionToken();
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    if (sanitized) params.set("sanitized", "true");
    if (meta.supportsSections && !allSelected) {
      params.set("sections", Array.from(selectedSections).join(","));
    }
    if (meta.supportsSections && verbose) {
      params.set("verbose", "true");
    }
    return `${meta.path}?${params.toString()}`;
  };

  const filename = sanitized
    ? meta.filename.replace("inventory", "inventory-sanitized")
    : meta.filename;

  /** Fetch the configured export. Text formats land in textPreview;
   *  binary formats land in binaryBlob. */
  const generate = async () => {
    setStatus({ kind: "generating" });
    setTextPreview(null);
    setBinaryBlob(null);
    try {
      const resp = await fetch(buildUrl());
      if (!resp.ok) {
        throw new Error(`${resp.status} ${resp.statusText}`);
      }
      if (meta.isText) {
        const text = await resp.text();
        setTextPreview(text);
      } else {
        setBinaryBlob(await resp.blob());
      }
      setStatus({ kind: "idle" });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const save = async () => {
    if (meta.isText && textPreview === null) return;
    if (!meta.isText && binaryBlob === null) return;
    setStatus({ kind: "saving" });
    try {
      const payload: string | Blob = meta.isText ? textPreview! : binaryBlob!;
      // Try native first.
      const native = await saveFileNative(filename, payload);
      if (native) {
        if (native.ok && native.path) {
          setStatus({ kind: "saved", path: native.path });
        } else if (native.error === "cancelled") {
          setStatus({ kind: "idle" });
        } else {
          throw new Error(native.error ?? "save failed");
        }
        return;
      }
      // Plain-browser fallback: blob URL download.
      const blob =
        typeof payload === "string"
          ? new Blob([payload], { type: "text/plain;charset=utf-8" })
          : payload;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.setTimeout(() => URL.revokeObjectURL(url), 5_000);
      setStatus({ kind: "idle" });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const copy = async () => {
    if (textPreview === null) return;
    const ok = await copyToClipboard(textPreview);
    if (ok) {
      setStatus({ kind: "copied" });
      window.setTimeout(
        () =>
          setStatus((cur) => (cur.kind === "copied" ? { kind: "idle" } : cur)),
        2_000,
      );
    } else {
      // Couldn't copy programmatically. Select the textarea so the user
      // can hit Cmd+C.
      textareaRef.current?.focus();
      textareaRef.current?.select();
      setStatus({
        kind: "error",
        message:
          "Couldn't access the clipboard. Press Cmd+C with the text selected.",
      });
    }
  };

  const hasContent = textPreview !== null || binaryBlob !== null;
  const busy = status.kind === "generating" || status.kind === "saving";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col gap-4 overflow-hidden">
        <DialogHeader className="shrink-0">
          <DialogTitle>{t("export.title")}</DialogTitle>
          <DialogDescription>{t("export.description")}</DialogDescription>
        </DialogHeader>

        <div className="-mr-3 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-3">
          <section className="flex flex-col gap-2">
            <Label>{t("export.preset")}</Label>
            <div className="grid grid-cols-3 gap-2">
              {(["recovery", "technical", "share"] as const).map((value) => (
                <Button
                  key={value}
                  type="button"
                  variant={preset === value ? "default" : "outline"}
                  onClick={() => applyPreset(value)}
                  className="h-auto flex-col items-start gap-0.5 px-3 py-2 text-left"
                  disabled={busy}
                >
                  <span className="text-sm">{t(`export.preset.${value}`)}</span>
                  <span className="text-xs font-normal opacity-75">
                    {t(`export.preset.${value}_help`)}
                  </span>
                </Button>
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-2">
            <Label>{t("export.format")}</Label>
            <div className="grid grid-cols-4 gap-2">
              {(Object.keys(FORMAT_META) as Format[]).map((f) => {
                const F = FORMAT_META[f];
                const Icon = F.icon;
                return (
                  <Button
                    key={f}
                    type="button"
                    variant={f === format ? "default" : "outline"}
                    onClick={() => {
                      setPreset("custom");
                      setFormat(f);
                    }}
                    className="h-14 flex-col gap-1"
                    disabled={busy}
                  >
                    <Icon className="size-4" />
                    <span className="text-xs">{F.label}</span>
                  </Button>
                );
              })}
            </div>
          </section>

          {meta.supportsSections && (
            <section className="flex flex-col gap-3 border-t border-border pt-4">
              <div className="flex items-center justify-between">
                <Label>{t("export.sections")}</Label>
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    type="button"
                    onClick={() => setAll(true)}
                    disabled={allSelected || busy}
                  >
                    All
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    type="button"
                    onClick={() => setAll(false)}
                    disabled={noneSelected || busy}
                  >
                    None
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
                {SECTIONS.map((s) => (
                  <Checkbox
                    key={s.key}
                    checked={selectedSections.has(s.key)}
                    onChange={() => toggle(s.key)}
                    label={t(s.i18nKey)}
                    disabled={busy}
                  />
                ))}
              </div>
              <div className="mt-1 flex flex-col gap-1 rounded-md bg-muted/40 p-3">
                <Checkbox
                  checked={verbose}
                  onChange={() => {
                    setPreset("custom");
                    setVerbose((v) => !v);
                  }}
                  disabled={busy}
                  label={
                    <span className="flex flex-col">
                      <span className="font-medium">{t("export.verbose")}</span>
                      <span className="text-xs text-muted-foreground">
                        {t("export.verbose_help")}
                      </span>
                    </span>
                  }
                />
              </div>
            </section>
          )}

          <section className="rounded-md border border-border bg-muted/30 p-3">
            <Checkbox
              checked={sanitized}
              onChange={() => {
                setPreset("custom");
                setSanitized((value) => !value);
              }}
              disabled={busy}
              label={
                <span className="flex flex-col">
                  <span className="font-medium">{t("export.sanitized")}</span>
                  <span className="text-xs text-muted-foreground">
                    {t("export.sanitized_help")}
                  </span>
                </span>
              }
            />
          </section>

          {hasContent && (
            <section className="flex flex-col gap-2 border-t border-border pt-4">
              <Label>
                {meta.isText ? t("export.preview") : t("export.binary_ready")}
              </Label>
              {meta.isText && textPreview !== null ? (
                <textarea
                  ref={textareaRef}
                  readOnly
                  value={textPreview}
                  className="h-[24rem] resize-none rounded-md border border-border bg-background p-3 font-mono text-xs leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  spellCheck={false}
                />
              ) : (
                <div className="rounded-md border border-border bg-card/40 p-4 text-sm text-muted-foreground">
                  {meta.label} bundle generated (
                  {Math.round((binaryBlob?.size ?? 0) / 1024)} KB). Click{" "}
                  <span className="font-medium">Save to file…</span> to write it
                  to disk.
                </div>
              )}
            </section>
          )}

          {status.kind === "error" && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm">
              <span className="font-medium text-destructive">
                Export failed:
              </span>{" "}
              <span className="text-foreground/80">{status.message}</span>
            </div>
          )}
          {status.kind === "saved" && (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-foreground/80">
              <span className="font-medium text-emerald-500">Saved to</span>{" "}
              <code className="font-mono">{status.path}</code>
            </div>
          )}
        </div>

        <DialogFooter className="shrink-0">
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={busy}
          >
            {t("common.close")}
          </Button>
          {!hasContent ? (
            <Button
              onClick={generate}
              disabled={busy || (meta.supportsSections && noneSelected)}
            >
              {status.kind === "generating" ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  {t("export.generating")}
                </>
              ) : (
                <>
                  <Sparkles className="size-4" />
                  {t("export.generate")}
                </>
              )}
            </Button>
          ) : (
            <>
              {meta.isText && (
                <Button variant="outline" onClick={copy} disabled={busy}>
                  {status.kind === "copied" ? (
                    <>
                      <Check className="size-4" />
                      {t("export.copied")}
                    </>
                  ) : (
                    <>
                      <ClipboardCopy className="size-4" />
                      {t("export.copy")}
                    </>
                  )}
                </Button>
              )}
              <Button onClick={save} disabled={busy}>
                {status.kind === "saving" ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    {t("export.saving")}
                  </>
                ) : (
                  <>
                    <Save className="size-4" />
                    {inPyWebView
                      ? t("export.save_to_file")
                      : t("export.download")}
                  </>
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
