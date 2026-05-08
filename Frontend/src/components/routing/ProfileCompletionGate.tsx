import { Navigate, useLocation } from "react-router-dom";
import { useProfileCompletion } from "@/hooks/useProfile";

type ProfileCompletionGateProps = {
  children: React.ReactElement;
};

export const ProfileCompletionGate = ({ children }: ProfileCompletionGateProps) => {
  const location = useLocation();
  const { data, isLoading, isError } = useProfileCompletion();
  const isOnboarding = location.pathname === "/dashboard/onboarding";

  if (isLoading) {
    return null;
  }

  if (isError) {
    return children;
  }

  if (!data?.profile_completed && !isOnboarding) {
    return <Navigate to="/dashboard/onboarding" replace />;
  }

  if (data?.profile_completed && isOnboarding) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};
