import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { WelcomeScreen } from "@/features/welcome/WelcomeScreen";
import { api } from "@/lib/api";

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
