import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";
import { cn } from "@/lib/utils";

/**
 * Small status pill in the top bar. Polls /health every 30 s.
 *
 * Three states: checking (spinner), online (green dot), offline (red).
 * The pill is read-only — there's no "reconnect" button because uvicorn
 * is bundled inside the app process and only comes back via app restart.
 */
export function BackendStatus() {
  const activeProfileSerial = useAppStore((state) => state.activeProfileSerial);
  const isExtracting = useAppStore((state) => state.isExtracting);
  const query = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    refetchInterval: 30_000,
    refetchOnMount: true,
  });

  let label: string;
  let icon: React.ReactNode;
  let tone: string;

  if (query.isPending) {
    label = t("status.checking");
    icon = <Loader2 className="size-3.5 animate-spin" />;
    tone = "text-muted-foreground bg-muted/40";
  } else if (query.isError) {
    label = t("status.offline");
    icon = <AlertCircle className="size-3.5" />;
    tone = "text-destructive bg-destructive/10";
  } else if (isExtracting) {
    label = t("status.extracting");
    icon = <Loader2 className="size-3.5 animate-spin" />;
    tone = "text-primary bg-primary/10";
  } else if (!activeProfileSerial) {
    label = t("status.no_profile");
    icon = <CheckCircle2 className="size-3.5" />;
    tone = "text-muted-foreground bg-muted/40";
  } else {
    label = t("status.ready");
    icon = <CheckCircle2 className="size-3.5" />;
    tone = "text-emerald-500 bg-emerald-500/10";
  }

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        tone,
      )}
      aria-live="polite"
    >
      {icon}
      <span>{label}</span>
      {query.data && (
        <span className="text-muted-foreground opacity-70">
          · v{query.data.version}
        </span>
      )}
    </div>
  );
}
