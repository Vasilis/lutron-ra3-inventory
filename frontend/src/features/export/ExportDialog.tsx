import { useState } from "react";
import {
  Check,
  ClipboardCopy,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Loader2,
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
import { t } from "@/i18n";
import { cn } from "@/lib/utils";

type Format = "markdown" | "json" | "csv" | "xlsx";

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface SectionDef {
  key: string;
  i18nKey: string;
}

/** Section keys must match the backend's ``MarkdownSection`` enum names. */
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

/**
 * Default Markdown selection: the sections you'd want if you were
 * recovering from a factory reset. Skips the summary tables (counts,
 * device-type rollups) and the timeclock / virtual-button / area-scene
 * blocks that aren't reachable on RA3 firmware 26.x anyway.
 */
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
  { label: string; icon: typeof FileText; path: string; filename: string; supportsSections: boolean }
> = {
  markdown: {
    label: "Markdown",
    icon: FileText,
    path: "/export/markdown",
    filename: "inventory.md",
    supportsSections: true,
  },
  json: {
    label: "JSON",
    icon: FileCode,
    path: "/export/json",
    filename: "inventory.json",
    supportsSections: false,
  },
  csv: {
    label: "CSV (zip)",
    icon: FileSpreadsheet,
    path: "/export/csv",
    filename: "inventory.zip",
    supportsSections: false,
  },
  xlsx: {
    label: "Excel",
    icon: FileSpreadsheet,
    path: "/export/xlsx",
    filename: "inventory.xlsx",
    supportsSections: false,
  },
};

/**
 * Export-options dialog.
 *
 *  - Format picker on top (Markdown / JSON / CSV / Excel)
 *  - For Markdown only: section checkboxes (all on by default)
 *  - "Download" triggers a same-origin GET, which the FastAPI route
 *    returns with Content-Disposition: attachment
 */
type Status =
  | { kind: "idle" }
  | { kind: "downloading" }
  | { kind: "copying" }
  | { kind: "copied" }
  | { kind: "error"; message: string };

export function ExportDialog({ open, onOpenChange }: ExportDialogProps) {
  const [format, setFormat] = useState<Format>("markdown");
  const [selectedSections, setSelectedSections] = useState<Set<string>>(
    new Set(RECOVERY_DEFAULT_SECTIONS),
  );
  const [verbose, setVerbose] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const meta = FORMAT_META[format];
  const allSelected = selectedSections.size === SECTIONS.length;
  const noneSelected = selectedSections.size === 0;

  const toggle = (key: string) => {
    setSelectedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const setAll = (on: boolean) => {
    setSelectedSections(on ? new Set(ALL_SECTION_KEYS) : new Set());
  };

  /** Build the export URL with the current options applied. */
  const buildUrl = (): string => {
    const token = getSessionToken();
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    if (meta.supportsSections && !allSelected) {
      params.set("sections", Array.from(selectedSections).join(","));
    }
    if (meta.supportsSections && verbose) {
      params.set("verbose", "true");
    }
    return `${meta.path}?${params.toString()}`;
  };

  /**
   * Fetch the export body and trigger a download via a Blob URL.
   *
   * The previous "create an <a download>" approach pointed the anchor at
   * the backend URL directly. PyWebView's WKWebView treated that as a
   * navigation, opening a content-only window with no back button. Going
   * through fetch → blob → blob: URL keeps everything in the React app:
   * the response is consumed in JS, the synthetic click then triggers a
   * save against a local Blob URL which doesn't navigate the webview.
   */
  const download = async () => {
    setStatus({ kind: "downloading" });
    try {
      const resp = await fetch(buildUrl());
      if (!resp.ok) {
        throw new Error(`${resp.status} ${resp.statusText}`);
      }
      const blob = await resp.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = meta.filename;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      // Give the browser a moment to start the save before releasing the
      // URL — some webviews need the URL alive until the dialog appears.
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 5_000);
      setStatus({ kind: "idle" });
      onOpenChange(false);
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  /**
   * "Copy to clipboard" — only meaningful for text formats (Markdown,
   * JSON). Hidden for CSV-zip and XLSX which are binary.
   */
  const copyToClipboard = async () => {
    setStatus({ kind: "copying" });
    try {
      const resp = await fetch(buildUrl());
      if (!resp.ok) {
        throw new Error(`${resp.status} ${resp.statusText}`);
      }
      const text = await resp.text();
      await navigator.clipboard.writeText(text);
      setStatus({ kind: "copied" });
      window.setTimeout(() => {
        setStatus((cur) => (cur.kind === "copied" ? { kind: "idle" } : cur));
      }, 2_000);
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const isTextFormat = format === "markdown" || format === "json";
  const busy = status.kind === "downloading" || status.kind === "copying";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{t("export.title")}</DialogTitle>
          <DialogDescription>{t("export.description")}</DialogDescription>
        </DialogHeader>

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
                  onClick={() => setFormat(f)}
                  className="h-14 flex-col gap-1"
                >
                  <Icon className="size-4" />
                  <span className="text-xs">{F.label}</span>
                </Button>
              );
            })}
          </div>
        </section>

        {meta.supportsSections && (
          <section
            className={cn(
              "flex flex-col gap-3 border-t border-border pt-4",
              "transition-opacity",
            )}
          >
            <div className="flex items-center justify-between">
              <Label>{t("export.sections")}</Label>
              <div className="flex gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  type="button"
                  onClick={() => setAll(true)}
                  disabled={allSelected}
                >
                  All
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  type="button"
                  onClick={() => setAll(false)}
                  disabled={noneSelected}
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
                />
              ))}
            </div>
            <div className="mt-2 flex flex-col gap-1 rounded-md bg-muted/40 p-3">
              <Checkbox
                checked={verbose}
                onChange={() => setVerbose((v) => !v)}
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

        {status.kind === "error" && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm">
            <span className="font-medium text-destructive">Export failed:</span>{" "}
            <span className="text-foreground/80">{status.message}</span>
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={busy}>
            {t("common.cancel")}
          </Button>
          {isTextFormat && (
            <Button
              variant="outline"
              onClick={copyToClipboard}
              disabled={busy || (meta.supportsSections && noneSelected)}
            >
              {status.kind === "copied" ? (
                <>
                  <Check className="size-4" />
                  {t("export.copied")}
                </>
              ) : status.kind === "copying" ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  {t("export.copying")}
                </>
              ) : (
                <>
                  <ClipboardCopy className="size-4" />
                  {t("export.copy")}
                </>
              )}
            </Button>
          )}
          <Button
            onClick={download}
            disabled={busy || (meta.supportsSections && noneSelected)}
          >
            {status.kind === "downloading" ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                {t("export.downloading")}
              </>
            ) : (
              <>
                <Download className="size-4" />
                {t("export.download")}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
