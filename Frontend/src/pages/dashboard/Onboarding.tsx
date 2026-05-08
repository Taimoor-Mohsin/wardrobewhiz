import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { StyleProfileForm } from "@/components/style/StyleProfileForm";
import { useAuth } from "@/hooks/use-auth";

const Onboarding = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

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

      <StyleProfileForm mode="onboarding" onCompleted={() => navigate("/dashboard")} />
    </div>
  );
};

export default Onboarding;
