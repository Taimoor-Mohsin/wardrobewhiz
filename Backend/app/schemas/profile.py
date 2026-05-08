from datetime import datetime

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    usual_contexts: list[str] | None = None
    usual_context_other: str | None = None
    style_text: str | None = None
    formality_level: int | None = None
    comfort_style_level: int | None = None
    modesty_preference: str | None = None
    preferred_styles: list[str] | None = None
    preferred_colors: list[str] | None = None
    disliked_colors: list[str] | None = None
    preferred_occasions: list[str] | None = None
    eastern_western_preference: str | None = None
    clothing_avoid_text: str | None = None
    fit_preference: str | None = None
    layering_preference: str | None = None
    accessories_preference: str | None = None


class ProfileRead(BaseModel):
    id: int
    user_id: int
    usual_contexts: list[str] = Field(default_factory=list)
    usual_context_other: str | None = None
    style_text: str | None = None
    formality_level: int | None = None
    comfort_style_level: int | None = None
    modesty_preference: str | None = None
    preferred_styles: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    disliked_colors: list[str] = Field(default_factory=list)
    preferred_occasions: list[str] = Field(default_factory=list)
    eastern_western_preference: str | None = None
    clothing_avoid_text: str | None = None
    fit_preference: str | None = None
    layering_preference: str | None = None
    accessories_preference: str | None = None
    profile_completed: bool
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProfileCompletionStatus(BaseModel):
    profile_completed: bool
    missing_fields: list[str] = Field(default_factory=list)
