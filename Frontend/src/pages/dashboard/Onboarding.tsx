import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StyleProfileForm, type StyleProfileSection } from "@/components/style/StyleProfileForm";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const onboardingSteps: Array<{
  title: string;
  description: string;
  section: StyleProfileSection;
}> = [
  {
    title: "Lifestyle & Questionnaire",
    description: "Tell WardrobeWiz where you dress, how formal you like to be, and what you avoid.",
    section: "questionnaire",
  },
  {
    title: "Aesthetics & Preferences",
    description: "Choose colors, style aesthetics, layers, and accessories.",
    section: "preferences",
  },
  {
    title: "Measurements & Fit",
    description: "Add your fit preference and optional measurements for better future recommendations.",
    section: "measurements",
  },
  {
    title: "Review & Complete",
    description: "Review everything before unlocking the dashboard.",
    section: "review",
  },
];

const Onboarding = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const currentStep = onboardingSteps[currentStepIndex];
  const isLastStep = currentStepIndex === onboardingSteps.length - 1;
  const progress = useMemo(
    () => Math.round(((currentStepIndex + 1) / onboardingSteps.length) * 100),
    [currentStepIndex],
  );

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 rounded-md border border-border bg-background p-5 shadow-card sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">WardrobeWiz onboarding</p>
          <h1 className="mt-1 text-3xl font-semibold text-foreground">
            Build your personal style profile
          </h1>
          <p className="mt-2 max-w-3xl text-muted-foreground">
            WardrobeWiz needs a few style preferences before it can personalize your wardrobe,
            recommendations, and outfit explanations.
          </p>
        </div>
        <Button variant="outline" onClick={handleLogout}>
          Log Out
        </Button>
      </div>

      <Card className="shadow-card">
        <CardContent className="space-y-5 pt-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-medium text-primary">
                Step {currentStepIndex + 1} of {onboardingSteps.length}
              </p>
              <h2 className="text-2xl font-semibold text-foreground">{currentStep.title}</h2>
            </div>
            <p className="text-sm font-medium text-muted-foreground">{progress}% complete</p>
          </div>
          <div className="h-2 rounded-full bg-muted">
            <div
              className="h-2 rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-4">
            {onboardingSteps.map((step, index) => (
              <button
                key={step.section}
                type="button"
                className={cn(
                  "rounded-md border p-3 text-left transition hover:border-primary/60 hover:bg-muted/50",
                  index === currentStepIndex
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground",
                )}
                onClick={() => setCurrentStepIndex(index)}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold",
                      index < currentStepIndex
                        ? "border-primary bg-primary text-primary-foreground"
                        : index === currentStepIndex
                          ? "border-primary text-primary"
                          : "border-border",
                    )}
                  >
                    {index < currentStepIndex ? <Check className="h-4 w-4" /> : index + 1}
                  </span>
                  <span className="text-sm font-semibold">{step.title}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  {step.description}
                </p>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div>
          <p className="text-sm font-medium text-primary">Current section</p>
          <h2 className="mt-1 text-2xl font-semibold text-foreground">{currentStep.title}</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {currentStep.description}
          </p>
        </div>

        <StyleProfileForm
          mode="onboarding"
          sections={[currentStep.section]}
          showHeader={false}
          showTabs={false}
          submitLabel={isLastStep ? "Complete Profile" : "Save & Next"}
          requireCompleteOnSave={isLastStep}
          footerStart={
            <Button
              type="button"
              variant="outline"
              onClick={() => setCurrentStepIndex((step) => Math.max(step - 1, 0))}
              disabled={currentStepIndex === 0}
            >
              Back
            </Button>
          }
          onSaved={(profile) => {
            if (profile.profile_completed) {
              navigate("/dashboard");
              return;
            }
            if (!isLastStep) {
              setCurrentStepIndex((step) => Math.min(step + 1, onboardingSteps.length - 1));
            }
          }}
          onCompleted={() => navigate("/dashboard")}
        />
      </div>
    </div>
  );
};

export default Onboarding;
