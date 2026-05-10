export type OutfitContext = {
  weather?: string;
  event?: string;
  location?: string;
  mood?: string;
  temperature?: number;
  occasion?: string;
  dressCode?: string;
};

export type FeedbackType = "like" | "dislike" | "swap";

export interface OutfitPiece {
  id: string;
  wardrobeItemId: string;
  imageUrl: string;
  name: string;
  category: string;
  position: "top" | "bottom" | "footwear" | "accessory" | "outerwear";
}

export interface Outfit {
  id: string;
  userId: string;
  pieces: OutfitPiece[];
  explanation: string; // RAG-generated explanation
  context: OutfitContext;
  createdAt: string;
  isFavorite: boolean;
  feedback?: FeedbackType;
  swapSuggestions?: OutfitPiece[]; // Alternative pieces for swap
  rating?: number; // User rating 1-5
}

export interface OutfitGenerationRequest {
  context: OutfitContext;
  excludeItems?: string[]; // Item IDs to exclude
  preferredItems?: string[]; // Item IDs to prefer
  stylePreferences?: string[];
}

export interface OutfitGenerationResponse {
  outfit: Outfit;
  alternatives?: Outfit[]; // Alternative outfit suggestions
}

export interface OutfitRecommendationRequest {
  occasion: string;
  location: string;
  weather: string;
  temperature_c: number;
  mood: string;
  dress_code: string;
  notes?: string | null;
}

export interface OutfitRecommendationItem {
  id: number;
  name: string;
  category?: string | null;
  image_url: string;
  image_path?: string | null;
  segmented_image_path?: string | null;
  color?: string | null;
  color_label?: string | null;
  color_hex?: string | null;
}

export interface OutfitRecommendationResponse {
  outfit_name: string;
  outfit_description: string;
  styling_tips: string[];
  color_story: string;
  why_it_fits_you: string;
  items: OutfitRecommendationItem[];
}

export interface OutfitFeedback {
  outfitId: string;
  feedbackType: FeedbackType;
  swappedItemId?: string; // If feedback is "swap"
  newItemId?: string; // Item to replace with
  notes?: string;
}

export interface SavedOutfit extends Outfit {
  savedAt: string;
  tags?: string[];
}

export interface OutfitLookbook {
  outfits: SavedOutfit[];
  total: number;
  filters?: {
    dateRange?: { start: string; end: string };
    tags?: string[];
    favoritesOnly?: boolean;
  };
}

