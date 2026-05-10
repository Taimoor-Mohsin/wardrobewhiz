from pydantic import BaseModel


class OutfitContextSchema(BaseModel):
    occasion: str
    location: str
    weather: str
    temperature_c: int | float
    mood: str
    dress_code: str
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
