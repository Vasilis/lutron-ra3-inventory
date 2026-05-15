import { Plug, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { t } from "@/i18n";

interface WelcomeScreenProps {
  onPair: () => void;
  onOpenExisting?: () => void;
  hasExistingProfiles: boolean;
}

/**
 * Empty-state screen shown when no profile is paired yet (or when no
 * snapshot exists for the active profile). The visual anchor when an
 * integrator first opens the app.
 */
export function WelcomeScreen({
  onPair,
  onOpenExisting,
  hasExistingProfiles,
}: WelcomeScreenProps) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="flex min-h-full items-center justify-center px-6 py-12">
        <Card className="w-full max-w-xl">
        <CardHeader className="items-center text-center">
          <div className="mb-3 flex size-12 items-center justify-center rounded-2xl bg-primary/15 text-primary">
            <Zap className="size-6" />
          </div>
          <CardTitle className="text-2xl">{t("welcome.heading")}</CardTitle>
          <CardDescription className="text-balance leading-relaxed">
            {t("welcome.body")}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-stretch gap-3">
          <Button size="lg" onClick={onPair}>
            <Plug className="size-4" />
            {t("welcome.pair")}
          </Button>
          {hasExistingProfiles && (
            <Button size="lg" variant="outline" onClick={onOpenExisting}>
              {t("welcome.existing")}
            </Button>
          )}
        </CardContent>
        </Card>
      </div>
    </div>
  );
}
