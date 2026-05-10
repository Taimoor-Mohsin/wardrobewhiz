import apiClient from "./client";
import type {
  Outfit,
  OutfitGenerationRequest,
  OutfitGenerationResponse,
  OutfitRecommendationRequest,
  OutfitRecommendationResponse,
  OutfitFeedback,
  SavedOutfit,
  OutfitLookbook,
} from "@/types/outfit";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const STATIC_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");

const resolveBackendUrl = (path?: string | null): string | undefined => {
  if (!path) return undefined;
  if (/^https?:\/\//i.test(path) || path.startsWith("data:") || path.startsWith("blob:")) {
    return path;
  }
  return `${STATIC_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
};

const normalizeRecommendationResponse = (
  response: OutfitRecommendationResponse
): OutfitRecommendationResponse => ({
  ...response,
  items: response.items.map((item) => {
    const imageUrl =
      resolveBackendUrl(item.segmented_image_path) ||
      resolveBackendUrl(item.image_path) ||
      resolveBackendUrl(item.image_url) ||
      item.image_url;

    return {
      ...item,
      image_url: imageUrl || "",
      image_path: resolveBackendUrl(item.image_path) || item.image_path,
      segmented_image_path: resolveBackendUrl(item.segmented_image_path) || item.segmented_image_path,
    };
  }),
});

export const outfitApi = {
  // Generate outfit based on context
  generateOutfit: async (
    request: OutfitGenerationRequest
  ): Promise<OutfitGenerationResponse> => {
    const response = await apiClient.post("/outfit/generate", request);
    return response.data;
  },

  recommendOutfit: async (
    request: OutfitRecommendationRequest
  ): Promise<OutfitRecommendationResponse> => {
    const response = await apiClient.post("/outfit/recommend", request);
    return normalizeRecommendationResponse(response.data);
  },

  // Get saved outfits
  getSavedOutfits: async (filters?: {
    favoritesOnly?: boolean;
    tags?: string[];
    dateRange?: { start: string; end: string };
  }): Promise<OutfitLookbook> => {
    const response = await apiClient.get("/outfit/saved", { params: filters });
    return response.data;
  },

  // Get single outfit
  getOutfit: async (id: string): Promise<Outfit> => {
    const response = await apiClient.get(`/outfit/${id}`);
    return response.data;
  },

  // Save outfit to favorites
  saveOutfit: async (id: string): Promise<SavedOutfit> => {
    const response = await apiClient.post(`/outfit/${id}/save`);
    return response.data;
  },

  // Unsave outfit
  unsaveOutfit: async (id: string): Promise<void> => {
    await apiClient.delete(`/outfit/${id}/save`);
  },

  // Submit feedback
  submitFeedback: async (feedback: OutfitFeedback): Promise<void> => {
    await apiClient.post("/outfit/feedback", feedback);
  },

  // Get outfit alternatives
  getAlternatives: async (outfitId: string): Promise<Outfit[]> => {
    const response = await apiClient.get(`/outfit/${outfitId}/alternatives`);
    return response.data;
  },
};

