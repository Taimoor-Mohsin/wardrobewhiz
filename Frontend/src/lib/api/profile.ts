import apiClient from "./client";
import type { ProfileCompletionStatus, ProfileUpdatePayload, UserProfile } from "@/types/profile";

export const profileApi = {
  getCurrentProfile: async (): Promise<UserProfile> => {
    const response = await apiClient.get("/profiles/me");
    return response.data;
  },

  updateCurrentProfile: async (payload: ProfileUpdatePayload): Promise<UserProfile> => {
    const response = await apiClient.put("/profiles/me", payload);
    return response.data;
  },

  getCompletionStatus: async (): Promise<ProfileCompletionStatus> => {
    const response = await apiClient.get("/profiles/me/completion");
    return response.data;
  },
};
