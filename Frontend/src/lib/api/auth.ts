import apiClient from "./client";

export type AuthUser = {
  id: number;
  name: string;
  email: string;
  created_at: string;
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  name: string;
  email: string;
  password: string;
};

export const authApi = {
  login: async (payload: LoginPayload): Promise<AuthTokenResponse> => {
    const response = await apiClient.post("/auth/login", payload);
    return response.data;
  },

  register: async (payload: RegisterPayload): Promise<AuthTokenResponse> => {
    const response = await apiClient.post("/auth/register", payload);
    return response.data;
  },

  me: async (): Promise<AuthUser> => {
    const response = await apiClient.get("/auth/me");
    return response.data;
  },
};
