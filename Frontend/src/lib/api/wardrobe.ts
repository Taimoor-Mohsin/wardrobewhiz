import apiClient from "./client";
import type { WardrobeItem, WardrobeFilters, WardrobeStats, WardrobeItemMetadata, WardrobeSuggestions } from "@/types/wardrobe";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const STATIC_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");
const NEUTRAL_SWATCH_HEX = "#9CA3AF";

const FASHION_COLOR_TO_HEX: Record<string, string> = {
  black: "#181818",
  charcoal: "#3A3A3A",
  white: "#F5F5F5",
  grey: "#808080",
  gray: "#808080",
  navy: "#283856",
  blue: "#4273BE",
  "light blue": "#A8C6E6",
  "denim blue": "#5C7094",
  red: "#BA2D34",
  maroon: "#742636",
  pink: "#D68AA2",
  green: "#4D7952",
  "bright green": "#3FA34D",
  "olive green": "#6F743F",
  olive: "#6F743F",
  mint: "#A6D1B4",
  yellow: "#E4C658",
  mustard: "#B69136",
  orange: "#D17D44",
  beige: "#D2BE9E",
  cream: "#F4ECDD",
  brown: "#6E4F3A",
  "dark brown": "#3F2B1F",
  tan: "#B2916A",
  khaki: "#A39A6D",
  purple: "#805E90",
};

const resolveBackendUrl = (path?: string): string | undefined => {
  if (!path) {
    return undefined;
  }

  if (/^https?:\/\//i.test(path) || path.startsWith("data:") || path.startsWith("blob:")) {
    return path;
  }

  return `${STATIC_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
};

const buildStaticImageUrl = (
  imagePath?: string,
  staticFolder: "uploads" | "segmented" | "thumbnails" = "uploads"
): string | undefined => {
  if (!imagePath) {
    return undefined;
  }

  if (imagePath.startsWith("/static/") || /^https?:\/\//i.test(imagePath)) {
    return resolveBackendUrl(imagePath);
  }

  const filename = imagePath.split(/[/\\]/).pop();
  if (!filename) {
    return undefined;
  }

  return `${STATIC_BASE_URL}/static/${staticFolder}/${filename}`;
};

const normalizeColorLabel = (value?: string): string | undefined => {
  if (!value) {
    return undefined;
  }

  return value.trim().toLowerCase();
};

const isHexColor = (value?: string): boolean =>
  Boolean(value && /^#(?:[0-9a-fA-F]{3}){1,2}$/.test(value));

const getWardrobeSwatchHex = (rawColor?: string): string => {
  if (isHexColor(rawColor)) {
    return rawColor!;
  }

  const normalizedLabel = normalizeColorLabel(rawColor);
  if (!normalizedLabel) {
    return NEUTRAL_SWATCH_HEX;
  }

  return FASHION_COLOR_TO_HEX[normalizedLabel] || NEUTRAL_SWATCH_HEX;
};

const formatColorLabel = (rawColor?: string): string | undefined => {
  if (!rawColor) {
    return undefined;
  }

  if (isHexColor(rawColor)) {
    return undefined;
  }

  return rawColor
    .trim()
    .split(/\s+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
};

export const normalizeWardrobeItem = (item: WardrobeItem): WardrobeItem => {
  const rawApiColor = item.color;
  const primaryDominantColor = item.dominant_colors?.[0];
  const swatchColorHex = primaryDominantColor?.hex || getWardrobeSwatchHex(rawApiColor);
  const colorLabel = primaryDominantColor?.label || formatColorLabel(rawApiColor);
  const imageUrl =
    buildStaticImageUrl(item.imageUrl, "uploads") ||
    buildStaticImageUrl(item.image_path, "uploads") ||
    item.imageUrl;
  const thumbnailUrl =
    buildStaticImageUrl(item.thumbnailUrl, "thumbnails") ||
    buildStaticImageUrl(item.thumbnail_path, "thumbnails") ||
    item.thumbnailUrl;
  const segmentedImageUrl = buildStaticImageUrl(item.segmented_image_path, "segmented");
  const normalizedItem = {
    ...item,
    imageUrl,
    thumbnailUrl,
    color: swatchColorHex,
    colorLabel,
    swatchColorHex,
    segmentedImageUrl,
  };

  console.log("[wardrobeApi] Normalized wardrobe item", {
    id: item.id,
    rawApiColor,
    normalizedColor: normalizedItem.color,
    swatchColorHex: normalizedItem.swatchColorHex,
    colorLabel: normalizedItem.colorLabel,
    segmented_image_path: item.segmented_image_path,
    segmentedImageUrl: normalizedItem.segmentedImageUrl,
    subcategory: item.subcategory,
  });

  return normalizedItem;
};

export const wardrobeApi = {
  // Get all wardrobe items
  getWardrobe: async (filters?: WardrobeFilters): Promise<WardrobeItem[]> => {
    const response = await apiClient.get("/wardrobe", { params: filters });
    return response.data.map(normalizeWardrobeItem);
  },

  // Get single wardrobe item
  getWardrobeItem: async (id: string): Promise<WardrobeItem> => {
    const response = await apiClient.get(`/wardrobe/${id}`);
    return normalizeWardrobeItem(response.data);
  },

  // Upload wardrobe items with images
  uploadWardrobeItems: async (
    formData: FormData
  ): Promise<{ items: WardrobeItem[]; errors?: string[] }> => {
    const response = await apiClient.post("/wardrobe/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return {
      ...response.data,
      items: (response.data?.items || []).map(normalizeWardrobeItem),
    };
  },

  // Create wardrobe item
  createWardrobeItem: async (
    item: Omit<WardrobeItem, "id" | "userId" | "createdAt" | "updatedAt" | "wearCount">
  ): Promise<WardrobeItem> => {
    const response = await apiClient.post("/wardrobe", item);
    return normalizeWardrobeItem(response.data);
  },

  // Update wardrobe item
  updateWardrobeItem: async (
    id: string,
    updates: Partial<WardrobeItemMetadata>
  ): Promise<WardrobeItem> => {
    console.log("[wardrobeApi] updateWardrobeItem request", {
      id,
      updates,
    });
    const response = await apiClient.patch(`/wardrobe/${id}`, updates);
    console.log("[wardrobeApi] updateWardrobeItem response", response.data);
    return normalizeWardrobeItem(response.data);
  },

  // Delete wardrobe item
  deleteWardrobeItem: async (id: string): Promise<void> => {
    await apiClient.delete(`/wardrobe/${id}`);
  },

  // Get wardrobe statistics
  getWardrobeStats: async (): Promise<WardrobeStats> => {
    const response = await apiClient.get("/wardrobe/stats");
    const data = response.data;
    const normalizeList = (list: unknown[]) =>
      list.map((item) => normalizeWardrobeItem(item as WardrobeItem));
    return {
      ...data,
      mostWorn: normalizeList(data.mostWorn ?? []),
      leastWorn: normalizeList(data.leastWorn ?? []),
      recentlyWorn: normalizeList(data.recentlyWorn ?? []),
    };
  },

  // Mark item as worn
  markItemWorn: async (id: string): Promise<WardrobeItem> => {
    const response = await apiClient.post(`/wardrobe/${id}/worn`);
    return normalizeWardrobeItem(response.data);
  },

  // Get items never worn
  getUnwornItems: async (): Promise<WardrobeItem[]> => {
    const response = await apiClient.get("/wardrobe/unworn");
    return response.data.map(normalizeWardrobeItem);
  },

  // Get wardrobe suggestions (underused items stats)
  getWardrobeSuggestions: async (): Promise<WardrobeSuggestions> => {
    const response = await apiClient.get("/wardrobe/suggestions");
    return response.data;
  },
};

