export type GarmentCategory = 
  | "Tops" 
  | "Bottoms" 
  | "Footwear" 
  | "Accessories" 
  | "Outerwear" 
  | "Dresses" 
  | "Other";

export type Season = "Spring" | "Summer" | "Fall" | "Winter" | "All-Season";

export type GarmentType = 
  | "Shirt" 
  | "T-Shirt" 
  | "Polo Shirt"
  | "Hoodie"
  | "Pants" 
  | "Trousers"
  | "Jeans" 
  | "Shorts" 
  | "Skirt"
  | "Dress" 
  | "Jacket" 
  | "Coat" 
  | "Blazer"
  | "Sweater" 
  | "Shoes" 
  | "Boots" 
  | "Sneakers" 
  | "Loafers"
  | "Sandals"
  | "Formal Shoes"
  | "Kurta"
  | "Shalwar Kameez"
  | "Saree"
  | "Waistcoat"
  | "Hat" 
  | "Bag" 
  | "Jewelry" 
  | "Other";

export interface DominantColor {
  label: string;
  hex: string;
  percentage: number;
  role: "primary" | "secondary" | "accent" | string;
  confidence?: number;
  source?: string;
}

export interface WardrobeItem {
  id: string;
  userId: string;
  imageUrl: string;
  image_path?: string;
  thumbnailUrl?: string;
  thumbnail_path?: string;
  segmented_image_path?: string;
  segmentedImageUrl?: string;
  name: string;
  category: GarmentCategory;
  type: GarmentType;
  subcategory?: string;
  color: string; // Hex color code
  colorLabel?: string;
  swatchColorHex?: string;
  dominant_colors?: DominantColor[];
  season: Season;
  description?: string;
  notes?: string;
  embedding?: number[]; // CLIP embedding vector
  createdAt: string;
  updatedAt: string;
  lastWorn?: string;
  wearCount: number;
  tags?: string[];
}

export interface WardrobeItemMetadata {
  name?: string;
  category: GarmentCategory;
  type: GarmentType;
  subcategory?: string;
  color: string;
  season: Season;
  description?: string;
  notes?: string;
  tags?: string[];
}

export interface UploadedImage {
  file: File;
  preview: string;
  metadata?: WardrobeItemMetadata;
  id: string; // Temporary ID for preview
}

export interface WardrobeUploadResponse {
  success: boolean;
  items: WardrobeItem[];
  errors?: string[];
}

export interface WardrobeFilters {
  category?: GarmentCategory | "All";
  color?: string;
  season?: Season | "All";
  type?: GarmentType | "All";
  searchQuery?: string;
  sort_by?: "newest" | "most_worn" | "least_worn" | "last_worn";
}

export interface WardrobeSuggestions {
  underused_count: number;
  most_underused_category: string | null;
  message: string;
}

export interface WardrobeStats {
  totalItems: number;
  itemsByCategory: Record<GarmentCategory, number>;
  itemsBySeason: Record<Season, number>;
  mostWorn: WardrobeItem[];
  leastWorn: WardrobeItem[];
  rewearRate: number;
  totalWears: number;
  neverWorn: number;
  recentlyWorn: WardrobeItem[];
}

