import json
import re
from pathlib import Path

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.profile import UserProfile
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem
from app.schemas.outfit import (
    OutfitContextSchema,
    OutfitRecommendationItem,
    OutfitRecommendationResponse,
)
from app.services.outfit_recommendation_service import (
    generate_outfit_recommendation,
    validate_outfit_selection,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/recommend", response_model=OutfitRecommendationResponse)
async def recommend_outfit(
    context: OutfitContextSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if not profile or not profile.profile_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete your style profile before requesting outfit recommendations.",
        )

    wardrobe_items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == current_user.id)
        .order_by(WardrobeItem.created_at.desc())
        .all()
    )
    if not wardrobe_items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add wardrobe items before requesting outfit recommendations.",
        )

    recommendation = await generate_outfit_recommendation(
        wardrobe_items,
        context.model_dump(),
        profile,
    )
    selected_ids = recommendation.get("selected_item_ids") or []
    validation = validate_outfit_selection(selected_ids, wardrobe_items)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Wardrobe is insufficient for a complete outfit: "
                + "; ".join(validation["errors"])
            ),
        )

    id_to_item = {item.id: item for item in wardrobe_items}
    ordered_items = [
        id_to_item[item_id]
        for item_id in validation["selected_item_ids"]
        if item_id in id_to_item
    ]
    if not ordered_items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recommendation did not resolve to any owned wardrobe items.",
        )

    return OutfitRecommendationResponse(
        outfit_name=recommendation["outfit_name"],
        outfit_description=recommendation["outfit_description"],
        styling_tips=recommendation["styling_tips"],
        color_story=recommendation["color_story"],
        why_it_fits_you=recommendation["why_it_fits_you"],
        items=[item_to_recommendation_item(item) for item in ordered_items],
    )


def item_to_recommendation_item(item: WardrobeItem) -> OutfitRecommendationItem:
    color_hex = color_hex_for_item(item)
    image_path = public_path(item.image_path)
    segmented_image_path = public_path(item.segmented_image_path)
    return OutfitRecommendationItem(
        id=item.id,
        name=item.name or item.subcategory or item.category or "Wardrobe item",
        category=item.category,
        image_url=segmented_image_path or image_path or "",
        image_path=image_path,
        segmented_image_path=segmented_image_path,
        color=item.color,
        color_label=item.color,
        color_hex=color_hex,
    )


def public_path(path: str | None) -> str | None:
    if not path:
        return None
    normalized_path = path.replace("\\", "/")
    filename = Path(normalized_path).name
    if "/segmented/" in normalized_path:
        return f"/static/segmented/{filename}"
    if "/uploads/" in normalized_path:
        return f"/static/uploads/{filename}"
    if "/thumbnails/" in normalized_path:
        return f"/static/thumbnails/{filename}"
    return "/" + normalized_path.lstrip("/")


def color_hex_for_item(item: WardrobeItem) -> str | None:
    direct_hex = normalize_hex(item.color)
    if direct_hex:
        return direct_hex

    for color in decode_dict_list(item.dominant_colors_json):
        hex_value = normalize_hex(color.get("hex"))
        if hex_value:
            return hex_value
    return None


def normalize_hex(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", cleaned):
        return f"#{cleaned.lstrip('#').upper()}"
    return None


def decode_dict_list(raw_value: str | None) -> list[dict]:
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
