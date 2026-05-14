import apiClient from "./client";
import type { OutfitFeedbackRequest } from "@/types/outfit";

export const feedbackApi = {
  submitFeedback: async (payload: OutfitFeedbackRequest): Promise<void> => {
    await apiClient.post("/feedback", payload);
  },
};
