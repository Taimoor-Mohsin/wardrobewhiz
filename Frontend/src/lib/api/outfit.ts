import apiClient from "./client";
import type {
  Outfit,
  OutfitGenerationRequest,
  OutfitGenerationResponse,
  OutfitRecommendationRequest,
  OutfitRecommendationResponse,
  OutfitFeedback,
  SaveOutfitRequest,
  SavedOutfitResponse,
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

  surpriseMe: async (): Promise<OutfitRecommendationResponse> => {
    const response = await apiClient.post("/outfit/recommend/surprise");
    return normalizeRecommendationResponse(response.data);
  },

  saveOutfit: async (
    outfit: OutfitRecommendationResponse,
    occasion?: string | null
  ): Promise<{ id: number; message: string }> => {
    const body: SaveOutfitRequest = { ...outfit, occasion };
    const response = await apiClient.post("/outfit/save", body);
    return response.data;
  },

  getSavedOutfits: async (): Promise<SavedOutfitResponse[]> => {
    const response = await apiClient.get("/outfit/saved");
    return response.data;
  },

  deleteSavedOutfit: async (id: number): Promise<void> => {
    await apiClient.delete(`/outfit/saved/${id}`);
  },

  getOutfit: async (id: string): Promise<Outfit> => {
    const response = await apiClient.get(`/outfit/${id}`);
    return response.data;
  },

  submitFeedback: async (feedback: OutfitFeedback): Promise<void> => {
    await apiClient.post("/outfit/feedback", feedback);
  },

  getAlternatives: async (outfitId: string): Promise<Outfit[]> => {
    const response = await apiClient.get(`/outfit/${outfitId}/alternatives`);
    return response.data;
  },
};
