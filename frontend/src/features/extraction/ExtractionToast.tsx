import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { api, extractEventsUrl } from "@/lib/api";
import { subscribeSse, type SseSubscription } from "@/lib/sse";
import type { ExtractEvent } from "@/lib/types";
import { t } from "@/i18n";
import { cn } from "@/lib/utils";

/**
 * Small floating progress card pinned to the bottom-right while an
 * extraction is in flight.
 *
 * Triggered imperatively: parent passes a ``trigger`` value (incremented
 * each click) and a ``profileSerial``. We POST /extract on every new
 * trigger, then stream phases until success / error.
 */
interface ExtractionToastProps {
  trigger: number;
  profileSerial: string | null;
  onComplete?: () => void;
  onRunningChange?: (running: boolean) => void;
}

interface PhaseState {
  label: string;
  progress: number | null;
}

export function ExtractionToast({
  trigger,
  profileSerial,
  onComplete,
  onRunningChange,
}: ExtractionToastProps) {
  const qc = useQueryClient();
  const [phase, setPhase] = useState<PhaseState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const subRef = useRef<SseSubscription | null>(null);

  // Kick a new extraction whenever ``trigger`` increments.
  useEffect(() => {
    if (trigger === 0 || !profileSerial) return;
    let cancelled = false;
    setPhase({ label: t("extract.starting"), progress: null });
    setError(null);
    setSuccess(null);
    onRunningChange?.(true);

    (async () => {
      try {
        const { extract_id } = await api.startExtraction(profileSerial);
        if (cancelled) return;

        subRef.current = subscribeSse<ExtractEvent>({
          url: extractEventsUrl(extract_id),
          onEvent: (event) => {
            if (event.phase === "success" || event.phase === "done") {
              setPhase(null);
              setSuccess(event.detail ?? t("extract.success"));
              subRef.current?.close();
              subRef.current = null;
              qc.invalidateQueries({ queryKey: ["inventory"] });
              onComplete?.();
              onRunningChange?.(false);
              window.setTimeout(() => setSuccess(null), 4000);
            } else if (event.phase === "error") {
              setPhase(null);
              const msg =
                event.kind === "already_connected"
                  ? t("extract.already_connected")
                  : (event.error ?? t("extract.error"));
              setError(msg);
              subRef.current?.close();
              subRef.current = null;
              onRunningChange?.(false);
            } else {
              setPhase({
                label: event.detail ?? event.phase,
                progress: event.progress ?? null,
              });
            }
          },
          onError: () => {
            // EventSource transient drop — only surface if we still expect
            // events.
            if (subRef.current && !success) {
              // Let it try to reconnect silently.
            }
          },
        });
      } catch (err) {
        if (!cancelled) {
          setPhase(null);
          setError(err instanceof Error ? err.message : String(err));
          onRunningChange?.(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger, profileSerial]);

  // Clean up on unmount
  useEffect(() => () => subRef.current?.close(), []);

  if (!phase && !error && !success) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80">
      <div
        className={cn(
          "overflow-hidden rounded-xl border bg-card shadow-2xl shadow-black/40",
          error
            ? "border-destructive/40"
            : success
              ? "border-emerald-500/40"
              : "border-border",
        )}
      >
        <div className="p-4">
          {phase && (
            <>
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                <Loader2 className="size-4 animate-spin text-primary" />
                {t("extract.running")}
              </div>
              <div className="text-xs text-muted-foreground">{phase.label}</div>
            </>
          )}
          {error && (
            <>
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-destructive">
                <AlertCircle className="size-4" />
                {t("extract.error")}
              </div>
              <div className="text-xs leading-snug text-muted-foreground">
                {error}
              </div>
            </>
          )}
          {success && (
            <>
              <div className="mb-1 flex items-center gap-2 text-sm font-medium text-emerald-500">
                <CheckCircle2 className="size-4" />
                {success}
              </div>
            </>
          )}
        </div>
        {phase?.progress != null && (
          <div className="h-1 bg-muted">
            <div
              className="h-full bg-primary transition-all"
              style={{
                width: `${Math.max(2, Math.round(phase.progress * 100))}%`,
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
