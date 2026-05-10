import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StyleProfileForm, type StyleProfileSection } from "@/components/style/StyleProfileForm";
import { useAuth } from "@/hooks/use-auth";

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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Complete your style profile</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            WardrobeWiz needs a few style preferences before it can personalize your wardrobe,
            recommendations, and outfit explanations.
          </p>
        </div>
        <Button variant="outline" onClick={handleLogout}>
          Log Out
        </Button>
      </div>

      <Card className="shadow-card">
        <CardContent className="space-y-4 pt-6">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-medium text-foreground">
              Step {currentStepIndex + 1} of {onboardingSteps.length}
            </p>
            <p className="text-sm text-muted-foreground">{progress}%</p>
          </div>
          <div className="h-2 rounded-full bg-muted">
            <div
              className="h-2 rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="grid gap-2 sm:grid-cols-4">
            {onboardingSteps.map((step, index) => (
              <button
                key={step.section}
                type="button"
                className={`rounded-md border px-3 py-2 text-left text-sm transition ${
                  index === currentStepIndex
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground hover:bg-muted/60"
                }`}
                onClick={() => setCurrentStepIndex(index)}
              >
                {step.title}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div>
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-foreground">{currentStep.title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{currentStep.description}</p>
        </div>

        <StyleProfileForm
          mode="onboarding"
          sections={[currentStep.section]}
          showHeader={false}
          showTabs={false}
          submitLabel={isLastStep ? "Complete Profile" : "Save & Next"}
          requireCompleteOnSave={isLastStep}
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

      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => setCurrentStepIndex((step) => Math.max(step - 1, 0))}
          disabled={currentStepIndex === 0}
        >
          Back
        </Button>
      </div>
    </div>
  );
};

export default Onboarding;
