import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
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
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ExtractionToast } from "@/features/extraction/ExtractionToast";
import { InventoryBrowser } from "@/features/inventory/InventoryBrowser";
import { PairingDialog } from "@/features/pairing/PairingDialog";
import { ProfilePickerDialog } from "@/features/profiles/ProfilePickerDialog";
import { WelcomeScreen } from "@/features/welcome/WelcomeScreen";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";
import { ApiError, api } from "@/lib/api";

/**
 * Top-level routing logic.
 *
 * For M1 there's no router — the screen is determined by local app state:
 *   - no chosen profile yet → WelcomeScreen
 *   - paired / picked profile → three-pane inventory browser
 */
export function App() {
  const qc = useQueryClient();
  const [pairingOpen, setPairingOpen] = useState(false);
  const [profilePickerOpen, setProfilePickerOpen] = useState(false);
  const [extractTrigger, setExtractTrigger] = useState(0);
  const [diskPassphrase, setDiskPassphrase] = useState("");
  const [passphrasePromptOpen, setPassphrasePromptOpen] = useState(false);

  // Pairing state + extraction-in-flight live in the Zustand store so the
  // top-bar BackendStatus pill can read them without prop drilling.
  const activeProfileSerial = useAppStore((s) => s.activeProfileSerial);
  const setActiveProfileSerial = useAppStore((s) => s.setActiveProfileSerial);
  const isExtracting = useAppStore((s) => s.isExtracting);
  const setIsExtracting = useAppStore((s) => s.setIsExtracting);

  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    queryFn: () => api.listProfiles(),
    retry: false,
  });

  const activeProfile = profilesQuery.data?.find(
    (profile) => profile.serial === activeProfileSerial,
  );

  // Hydrate the backend's remembered active profile first. If there isn't
  // one, auto-activate the only saved profile (most homes have one processor).
  useEffect(() => {
    if (activeProfileSerial) return;
    const profiles = profilesQuery.data;
    if (!profiles) return;
    const remembered = profiles.find((profile) => profile.active);
    if (remembered) {
      setActiveProfileSerial(remembered.serial);
      qc.invalidateQueries({ queryKey: ["inventory"] });
      return;
    }
    if (profiles.length !== 1) return;
    const serial = profiles[0].serial;
    let cancelled = false;
    void api.activateProfile(serial).then(() => {
      if (cancelled) return;
      setActiveProfileSerial(serial);
      qc.invalidateQueries({ queryKey: ["inventory"] });
    });
    return () => {
      cancelled = true;
    };
  }, [profilesQuery.data, activeProfileSerial, setActiveProfileSerial, qc]);

  if (profilesQuery.isPending) {
    return (
      <AppShell>
        <StartupState
          icon={<Loader2 className="size-5 animate-spin" />}
          title={t("startup.loading_title")}
          body={t("startup.loading_body")}
        />
      </AppShell>
    );
  }

  if (profilesQuery.isError) {
    const authFailed =
      profilesQuery.error instanceof ApiError &&
      profilesQuery.error.status === 401;

    return (
      <AppShell>
        <StartupState
          icon={<AlertTriangle className="size-5" />}
          title={t(authFailed ? "startup.auth_title" : "startup.error_title")}
          body={t(authFailed ? "startup.auth_body" : "startup.error_body")}
          action={
            <Button variant="outline" onClick={() => profilesQuery.refetch()}>
              {t("common.retry")}
            </Button>
          }
        />
      </AppShell>
    );
  }

  const hasProfiles = (profilesQuery.data?.length ?? 0) > 0;
  const requestExtract = () => {
    if (
      activeProfile?.credential_storage === "encrypted_disk" &&
      !diskPassphrase.trim()
    ) {
      setPassphrasePromptOpen(true);
      return;
    }
    setExtractTrigger((value) => value + 1);
  };

  return (
    <>
      <AppShell>
        {activeProfileSerial ? (
          <InventoryBrowser
            onExtract={requestExtract}
            isExtracting={isExtracting}
          />
        ) : (
          <WelcomeScreen
            hasExistingProfiles={hasProfiles}
            onPair={() => setPairingOpen(true)}
            onOpenExisting={() => setProfilePickerOpen(true)}
          />
        )}
      </AppShell>
      <PairingDialog
        open={pairingOpen}
        onOpenChange={setPairingOpen}
        onPaired={(serial, nextPassphrase) => {
          setActiveProfileSerial(serial);
          setDiskPassphrase(nextPassphrase ?? "");
        }}
      />
      <ProfilePickerDialog
        open={profilePickerOpen}
        onOpenChange={setProfilePickerOpen}
        onPicked={(serial) => {
          setActiveProfileSerial(serial);
          setDiskPassphrase("");
        }}
      />
      <ExtractionToast
        trigger={extractTrigger}
        profileSerial={activeProfileSerial}
        diskPassphrase={diskPassphrase.trim() || undefined}
        onRunningChange={setIsExtracting}
        onCredentialError={() => setDiskPassphrase("")}
      />
      <DiskPassphraseDialog
        open={passphrasePromptOpen}
        onOpenChange={setPassphrasePromptOpen}
        value={diskPassphrase}
        onValueChange={setDiskPassphrase}
        onContinue={() => {
          setPassphrasePromptOpen(false);
          setExtractTrigger((value) => value + 1);
        }}
      />
    </>
  );
}

function DiskPassphraseDialog({
  open,
  onOpenChange,
  value,
  onValueChange,
  onContinue,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  value: string;
  onValueChange: (value: string) => void;
  onContinue: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("extract.passphrase_title")}</DialogTitle>
          <DialogDescription>{t("extract.passphrase_body")}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="extract-passphrase">
            {t("pair.passphrase_label")}
          </Label>
          <Input
            id="extract-passphrase"
            type="password"
            value={value}
            onChange={(event) => onValueChange(event.target.value)}
            autoComplete="current-password"
          />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={onContinue} disabled={!value.trim()}>
            {t("extract.continue")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StartupState({
  icon,
  title,
  body,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-full items-center justify-center px-6 py-12">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex size-11 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
            {icon}
          </div>
          <CardTitle>{title}</CardTitle>
          <CardDescription className="text-balance leading-relaxed">
            {body}
          </CardDescription>
        </CardHeader>
        {action && (
          <CardContent className="flex justify-center">{action}</CardContent>
        )}
      </Card>
    </div>
  );
}
