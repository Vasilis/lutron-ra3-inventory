import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, pairEventsUrl } from "@/lib/api";
import { subscribeSse, type SseSubscription } from "@/lib/sse";
import type { PairEvent } from "@/lib/types";
import { t } from "@/i18n";
import { cn } from "@/lib/utils";

interface PairingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPaired?: (serial: string) => void;
}

type Status =
  | { kind: "form" }
  | { kind: "starting" }
  | { kind: "ready" }
  | { kind: "discovering"; detail?: string }
  | { kind: "success"; serial: string; name?: string }
  | { kind: "error"; message: string };

/**
 * End-to-end pairing flow.
 *
 *   form    → enter host + name
 *   POST /pair/start → server emits SSE phases on /pair/events
 *   ready    → "Press the pairing button now" (the 30 s window)
 *   discovering → reading processor metadata
 *   success → close, invalidate /profiles, fire onPaired
 *   error / timeout → surface the message; user can retry
 */
export function PairingDialog({ open, onOpenChange, onPaired }: PairingDialogProps) {
  const qc = useQueryClient();
  const [host, setHost] = useState("192.168.1.184");
  const [name, setName] = useState("Home");
  const [status, setStatus] = useState<Status>({ kind: "form" });
  const subscriptionRef = useRef<SseSubscription | null>(null);

  // Reset when the dialog is closed so the next open is fresh.
  useEffect(() => {
    if (!open) {
      subscriptionRef.current?.close();
      subscriptionRef.current = null;
      setStatus({ kind: "form" });
    }
  }, [open]);

  // Clean up on unmount.
  useEffect(
    () => () => {
      subscriptionRef.current?.close();
    },
    [],
  );

  const startPairing = async () => {
    setStatus({ kind: "starting" });
    try {
      const { pair_id } = await api.startPairing(host, name);
      subscriptionRef.current = subscribeSse<PairEvent>({
        url: pairEventsUrl(pair_id),
        onEvent: (event) => {
          if (event.phase === "ready") setStatus({ kind: "ready" });
          else if (event.phase === "discovering")
            setStatus({ kind: "discovering", detail: event.detail });
          else if (event.phase === "success" && event.serial) {
            setStatus({ kind: "success", serial: event.serial, name: event.name });
            subscriptionRef.current?.close();
            subscriptionRef.current = null;
            qc.invalidateQueries({ queryKey: ["profiles"] });
            onPaired?.(event.serial);
          } else if (event.phase === "error" || event.phase === "timeout") {
            setStatus({
              kind: "error",
              message: event.error ?? event.detail ?? t("pair.error"),
            });
            subscriptionRef.current?.close();
            subscriptionRef.current = null;
          }
        },
        onError: () => {
          if (subscriptionRef.current) {
            setStatus({
              kind: "error",
              message: "Lost connection to the pairing stream.",
            });
            subscriptionRef.current?.close();
            subscriptionRef.current = null;
          }
        },
      });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const inProgress =
    status.kind === "starting" || status.kind === "ready" || status.kind === "discovering";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="size-4 text-primary" />
            {t("welcome.pair")}
          </DialogTitle>
          <DialogDescription>
            Connect to your RadioRA 3 processor. You'll be prompted to press
            the small pairing button on the processor during this flow.
          </DialogDescription>
        </DialogHeader>

        {(status.kind === "form" || status.kind === "error") && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pair-host">{t("pair.host_label")}</Label>
              <Input
                id="pair-host"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder={t("pair.host_placeholder")}
                spellCheck={false}
                autoComplete="off"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pair-name">{t("pair.name_label")}</Label>
              <Input
                id="pair-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("pair.name_placeholder")}
              />
            </div>
            {status.kind === "error" && (
              <ErrorBanner message={status.message} />
            )}
          </div>
        )}

        {inProgress && <ProgressView status={status} />}
        {status.kind === "success" && (
          <SuccessView serial={status.serial} name={status.name} />
        )}

        <DialogFooter>
          {status.kind === "success" ? (
            <Button onClick={() => onOpenChange(false)}>{t("common.close")}</Button>
          ) : (
            <>
              <Button variant="ghost" onClick={() => onOpenChange(false)}>
                {t("common.cancel")}
              </Button>
              <Button
                onClick={startPairing}
                disabled={inProgress || !host.trim() || !name.trim()}
              >
                {inProgress ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    {status.kind === "ready"
                      ? "Waiting for button press…"
                      : "Pairing…"}
                  </>
                ) : status.kind === "error" ? (
                  t("common.retry")
                ) : (
                  t("pair.start")
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ProgressView({ status }: { status: Status }) {
  if (status.kind === "starting") {
    return <InfoLine icon={<Loader2 className="size-4 animate-spin" />}>Reaching the processor…</InfoLine>;
  }
  if (status.kind === "ready") {
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-primary/40 bg-primary/10 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-primary">
          <Zap className="size-4" />
          Press the pairing button now
        </div>
        <p className="text-sm text-foreground/80">{t("pair.press_button")}</p>
      </div>
    );
  }
  if (status.kind === "discovering") {
    return (
      <InfoLine icon={<Loader2 className="size-4 animate-spin" />}>
        {status.detail ?? "Reading processor info…"}
      </InfoLine>
    );
  }
  return null;
}

function SuccessView({ serial, name }: { serial: string; name?: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
      <CheckCircle2 className="mt-0.5 size-4 text-emerald-500" />
      <div className="flex flex-col gap-0.5 text-sm">
        <span className="font-medium">{t("pair.success")}</span>
        <span className="text-muted-foreground">
          {name ? `Profile "${name}" · ` : ""}Serial {serial}
        </span>
      </div>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm">
      <AlertTriangle className="mt-0.5 size-4 text-destructive" />
      <span className="leading-snug">{message}</span>
    </div>
  );
}

function InfoLine({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className={cn("flex items-center gap-2 text-sm text-muted-foreground")}>
      {icon}
      {children}
    </div>
  );
}
