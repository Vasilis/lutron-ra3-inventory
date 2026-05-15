import { useState } from "react";
import { Download, FileCode, FileSpreadsheet, FileText } from "lucide-react";
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
export function ExportDialog({ open, onOpenChange }: ExportDialogProps) {
  const [format, setFormat] = useState<Format>("markdown");
  const [selectedSections, setSelectedSections] = useState<Set<string>>(
    new Set(ALL_SECTION_KEYS),
  );

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

  const download = () => {
    const token = getSessionToken();
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    if (meta.supportsSections && !allSelected) {
      // Backend honors ?sections=a,b,c — only set when we're filtering.
      params.set("sections", Array.from(selectedSections).join(","));
    }
    const url = `${meta.path}?${params.toString()}`;
    // Trigger a hidden anchor download — browsers honor Content-Disposition.
    const a = document.createElement("a");
    a.href = url;
    a.download = meta.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    onOpenChange(false);
  };

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
          </section>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={download}
            disabled={meta.supportsSections && noneSelected}
          >
            <Download className="size-4" />
            {t("export.download")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
