import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { AxiosError } from "axios";
import { authApi, type AuthUser, type LoginPayload, type RegisterPayload } from "@/lib/api/auth";

type AuthResult = {
  success: boolean;
  message?: string;
};

type AuthState = {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<AuthResult>;
  register: (payload: RegisterPayload) => Promise<AuthResult>;
  logout: () => void;
};

const TOKEN_KEY = "wardrobewiz-auth-token";

const AuthContext = createContext<AuthState | undefined>(undefined);

const getErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      const token = window.localStorage.getItem(TOKEN_KEY);
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await authApi.me();
        setUser(currentUser);
      } catch (error) {
        window.localStorage.removeItem(TOKEN_KEY);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    void restoreSession();
  }, []);

  const login = async (email: string, password: string): Promise<AuthResult> => {
    try {
      const response = await authApi.login({
        email: email.trim().toLowerCase(),
        password,
      } satisfies LoginPayload);
      window.localStorage.setItem(TOKEN_KEY, response.access_token);
      setUser(response.user);
      return { success: true };
    } catch (error) {
      window.localStorage.removeItem(TOKEN_KEY);
      setUser(null);
      return {
        success: false,
        message: getErrorMessage(error, "Unable to sign in. Please check your email and password."),
      };
    }
  };

  const register = async (payload: RegisterPayload): Promise<AuthResult> => {
    try {
      const response = await authApi.register({
        name: payload.name.trim(),
        email: payload.email.trim().toLowerCase(),
        password: payload.password,
      });
      window.localStorage.setItem(TOKEN_KEY, response.access_token);
      setUser(response.user);
      return { success: true };
    } catch (error) {
      window.localStorage.removeItem(TOKEN_KEY);
      setUser(null);
      return {
        success: false,
        message: getErrorMessage(error, "Unable to create your account. Please try again."),
      };
    }
  };

  const logout = () => {
    setUser(null);
    window.localStorage.removeItem(TOKEN_KEY);
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: Boolean(user),
        isLoading,
        user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
