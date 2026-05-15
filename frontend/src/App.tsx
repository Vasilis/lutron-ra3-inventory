import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { WelcomeScreen } from "@/features/welcome/WelcomeScreen";
import { t } from "@/i18n";
import { ApiError, api } from "@/lib/api";

/**
 * Top-level routing logic.
 *
 * For M1 there's no router — the screen is determined by app state:
 *   - No profiles    → WelcomeScreen
 *   - Profiles exist → three-pane inventory browser (task #11)
 *
 * Once #11 lands this will route between the welcome state, the pairing
 * wizard, the extraction-in-progress overlay, and the three-pane browser.
 */
export function App() {
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
      profilesQuery.error instanceof ApiError && profilesQuery.error.status === 401;

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
    <AppShell>
      <WelcomeScreen
        hasExistingProfiles={hasProfiles}
        onPair={() => {
          /* task #11: open pairing wizard */
        }}
        onOpenExisting={() => {
          /* task #11: route to inventory browser */
        }}
      />
    </AppShell>
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
        {action && <CardContent className="flex justify-center">{action}</CardContent>}
      </Card>
    </div>
  );
}
