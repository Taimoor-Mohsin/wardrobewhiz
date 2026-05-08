import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";

type AuthRedirectProps = {
  children: React.ReactElement;
};

export const AuthRedirect = ({ children }: AuthRedirectProps) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};
