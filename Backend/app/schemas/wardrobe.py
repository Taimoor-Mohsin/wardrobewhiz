from datetime import datetime

from pydantic import BaseModel, Field


class WardrobeItemBase(BaseModel):
    name: str | None = None
    category: str | None = None
    type: str | None = None
    subcategory: str | None = None
    color: str | None = None
    season: str | None = None
    description: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    image_path: str | None = None
    segmented_image_path: str | None = None


class WardrobeItemCreate(WardrobeItemBase):
    image_path: str | None = None


class WardrobeItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    type: str | None = None
    subcategory: str | None = None
    color: str | None = None
    season: str | None = None
    description: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class WardrobeItemRead(BaseModel):
    id: int
    user_id: int
    userId: str
    name: str
    category: str | None = None
    type: str
    subcategory: str | None = None
    color: str | None = None
    season: str | None = None
    description: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    image_path: str
    imageUrl: str
    thumbnail_path: str | None = None
    thumbnailUrl: str | None = None
    segmented_image_path: str | None = None
    created_at: datetime | None = None
    createdAt: datetime | None = None
    updated_at: datetime | None = None
    updatedAt: datetime | None = None
    lastWorn: datetime | None = None
    wearCount: int = 0


class WardrobeUploadResponse(BaseModel):
    items: list[WardrobeItemRead] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class WardrobeStats(BaseModel):
    totalItems: int
    itemsByCategory: dict[str, int]
    itemsBySeason: dict[str, int]
    mostWorn: list[WardrobeItemRead]
    leastWorn: list[WardrobeItemRead]
    rewearRate: float
