import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
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
  const [pairingOpen, setPairingOpen] = useState(false);
  const [profilePickerOpen, setProfilePickerOpen] = useState(false);
  const [activeProfileSerial, setActiveProfileSerial] = useState<string | null>(
    null,
  );
  const [extractTrigger, setExtractTrigger] = useState(0);
  const [isExtracting, setIsExtracting] = useState(false);

  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    queryFn: () => api.listProfiles(),
    retry: false,
  });

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

  return (
    <>
      <AppShell>
        {activeProfileSerial ? (
          <InventoryBrowser
            onExtract={() => setExtractTrigger((value) => value + 1)}
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
        onPaired={setActiveProfileSerial}
      />
      <ProfilePickerDialog
        open={profilePickerOpen}
        onOpenChange={setProfilePickerOpen}
        onPicked={setActiveProfileSerial}
      />
      <ExtractionToast
        trigger={extractTrigger}
        profileSerial={activeProfileSerial}
        onRunningChange={setIsExtracting}
      />
    </>
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
