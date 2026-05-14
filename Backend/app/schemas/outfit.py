from datetime import datetime

from pydantic import BaseModel


class OutfitContextSchema(BaseModel):
    occasion: str
    location: str | None = None
    weather: str | None = None
    temperature_c: int | float | None = None
    mood: str | None = None
    dress_code: str | None = None
    notes: str | None = None


class OutfitRecommendationItem(BaseModel):
    id: int
    name: str
    category: str | None = None
    image_url: str
    image_path: str | None = None
    segmented_image_path: str | None = None
    color: str | None = None
    color_label: str | None = None
    color_hex: str | None = None


class OutfitRecommendationResponse(BaseModel):
    outfit_name: str
    outfit_description: str
    styling_tips: list[str]
    color_story: str
    why_it_fits_you: str
    items: list[OutfitRecommendationItem]
    confidence_score: int = 0
    harmony_type: str | None = None


class SaveOutfitRequest(BaseModel):
    outfit_name: str
    outfit_description: str
    styling_tips: list[str]
    color_story: str
    why_it_fits_you: str
    items: list[OutfitRecommendationItem]
    occasion: str | None = None


class SavedOutfitResponse(BaseModel):
    id: int
    outfit_name: str
    outfit_description: str
    styling_tips: list[str]
    color_story: str
    why_it_fits_you: str
    items: list[OutfitRecommendationItem]
    context_occasion: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
