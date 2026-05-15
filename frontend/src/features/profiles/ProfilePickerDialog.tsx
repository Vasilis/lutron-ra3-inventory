import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cpu, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { t } from "@/i18n";

interface ProfilePickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPicked: (serial: string) => void;
}

/**
 * Lists existing profiles and lets the user activate one.
 *
 * Activation hits ``POST /profiles/{serial}/activate``, which sets
 * ``config.active_profile_serial`` on the backend. After that, the
 * inventory routes will resolve to that profile's snapshot.
 */
export function ProfilePickerDialog({
  open,
  onOpenChange,
  onPicked,
}: ProfilePickerDialogProps) {
  const qc = useQueryClient();
  const profiles = useQuery({
    queryKey: ["profiles"],
    queryFn: () => api.listProfiles(),
    enabled: open,
  });

  const activate = useMutation({
    mutationFn: (serial: string) => api.activateProfile(serial),
    onSuccess: (_data, serial) => {
      qc.invalidateQueries({ queryKey: ["inventory"] });
      onPicked(serial);
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("profiles.open_title")}</DialogTitle>
          <DialogDescription>
            {t("profiles.open_description")}
          </DialogDescription>
        </DialogHeader>

        {profiles.isPending ? (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            {t("profiles.loading")}
          </div>
        ) : profiles.isError ? (
          <p className="py-6 text-sm text-destructive">
            {t("profiles.load_error")}
          </p>
        ) : profiles.data && profiles.data.length === 0 ? (
          <p className="py-6 text-sm text-muted-foreground">
            {t("profiles.empty")}
          </p>
        ) : (
          <ul className="flex flex-col gap-2 py-2">
            {profiles.data?.map((p) => (
              <li key={p.serial}>
                <Button
                  variant="outline"
                  className="h-auto w-full justify-start gap-3 p-3 text-left"
                  disabled={activate.isPending}
                  onClick={() => activate.mutate(p.serial)}
                >
                  <Cpu className="size-4 shrink-0 text-primary" />
                  <span className="flex flex-1 flex-col items-start">
                    <span className="text-sm font-medium">{p.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {p.host} · serial {p.serial}
                      {p.firmware ? ` · ${p.firmware}` : ""}
                    </span>
                  </span>
                  {!p.has_certs && (
                    <span className="rounded bg-destructive/15 px-2 py-0.5 text-[10px] uppercase text-destructive">
                      {t("profiles.no_certs")}
                    </span>
                  )}
                  {p.active && (
                    <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] uppercase text-emerald-500">
                      {t("profiles.active")}
                    </span>
                  )}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}
