import json
import re
from pathlib import Path

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.feedback import OutfitFeedback
from app.models.outfit import Outfit as OutfitModel
from app.models.profile import UserProfile
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem
from app.schemas.outfit import (
    OutfitContextSchema,
    OutfitRecommendationItem,
    OutfitRecommendationResponse,
    SaveOutfitRequest,
    SavedOutfitResponse,
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

    feedback_history = _build_feedback_history(current_user.id, wardrobe_items, db)
    recent_item_ids = _get_recent_item_ids(current_user.id, db)
    recommendation = await generate_outfit_recommendation(
        wardrobe_items,
        context.model_dump(),
        profile,
        feedback_history=feedback_history,
        recent_item_ids=recent_item_ids,
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
        confidence_score=recommendation.get("confidence_score", 60),
        harmony_type=recommendation.get("harmony_type"),
    )


@router.post("/recommend/surprise", response_model=OutfitRecommendationResponse)
async def surprise_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wardrobe_items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == current_user.id)
        .order_by(WardrobeItem.created_at.desc())
        .all()
    )
    if not wardrobe_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add wardrobe items before using Surprise Me.",
        )

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

    feedback_history = _build_feedback_history(current_user.id, wardrobe_items, db)
    recent_item_ids = _get_recent_item_ids(current_user.id, db)
    recommendation = await generate_outfit_recommendation(
        wardrobe_items,
        {},
        profile,
        feedback_history=feedback_history,
        recent_item_ids=recent_item_ids,
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
        confidence_score=recommendation.get("confidence_score", 60),
        harmony_type=recommendation.get("harmony_type"),
    )


@router.post("/save")
def save_outfit(
    request: SaveOutfitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    outfit = OutfitModel(
        user_id=current_user.id,
        outfit_name=request.outfit_name,
        outfit_description=request.outfit_description,
        styling_tips=json.dumps(request.styling_tips),
        color_story=request.color_story,
        why_it_fits_you=request.why_it_fits_you,
        item_ids=json.dumps([item.id for item in request.items]),
        context_occasion=request.occasion,
    )
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    return {"id": outfit.id, "message": "Outfit saved"}


@router.get("/saved", response_model=list[SavedOutfitResponse])
def get_saved_outfits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    outfits = (
        db.query(OutfitModel)
        .filter(OutfitModel.user_id == current_user.id)
        .order_by(OutfitModel.created_at.desc())
        .all()
    )

    all_item_ids: set[int] = set()
    for outfit in outfits:
        all_item_ids.update(json.loads(outfit.item_ids or "[]"))

    wardrobe_items = (
        db.query(WardrobeItem)
        .filter(
            WardrobeItem.user_id == current_user.id,
            WardrobeItem.id.in_(all_item_ids),
        )
        .all()
        if all_item_ids
        else []
    )
    item_map = {item.id: item for item in wardrobe_items}

    result = []
    for outfit in outfits:
        item_ids = json.loads(outfit.item_ids or "[]")
        items = [
            item_to_recommendation_item(item_map[iid])
            for iid in item_ids
            if iid in item_map
        ]
        result.append(
            SavedOutfitResponse(
                id=outfit.id,
                outfit_name=outfit.outfit_name,
                outfit_description=outfit.outfit_description or "",
                styling_tips=json.loads(outfit.styling_tips or "[]"),
                color_story=outfit.color_story or "",
                why_it_fits_you=outfit.why_it_fits_you or "",
                items=items,
                context_occasion=outfit.context_occasion,
                created_at=outfit.created_at,
            )
        )
    return result


@router.delete("/saved/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_outfit(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    outfit = (
        db.query(OutfitModel)
        .filter(OutfitModel.id == outfit_id, OutfitModel.user_id == current_user.id)
        .first()
    )
    if not outfit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found.",
        )
    db.delete(outfit)
    db.commit()


def _build_feedback_history(
    user_id: int,
    wardrobe_items: list[WardrobeItem],
    db: Session,
) -> list[dict]:
    feedbacks = (
        db.query(OutfitFeedback)
        .filter(OutfitFeedback.user_id == user_id)
        .order_by(OutfitFeedback.created_at.desc())
        .limit(50)
        .all()
    )
    if not feedbacks:
        return []

    outfit_ids = [fb.outfit_id for fb in feedbacks]
    outfits = (
        db.query(OutfitModel)
        .filter(OutfitModel.id.in_(outfit_ids))
        .all()
    )
    outfit_map = {o.id: o for o in outfits}
    item_map = {item.id: item for item in wardrobe_items}

    history: list[dict] = []
    for fb in feedbacks:
        outfit = outfit_map.get(fb.outfit_id)
        if outfit is None:
            continue
        for item_id in json.loads(outfit.item_ids or "[]"):
            wardrobe_item = item_map.get(item_id)
            if wardrobe_item is None:
                continue
            try:
                style_tags = json.loads(wardrobe_item.pattern_tags_json or "[]")
            except (json.JSONDecodeError, TypeError):
                style_tags = []
            history.append({
                "item_category": wardrobe_item.category or "",
                "item_style_tags": [str(t) for t in style_tags if isinstance(style_tags, list) and t],
                "rating": fb.rating,
            })
    return history


def _get_recent_item_ids(user_id: int, db: Session) -> list[int]:
    recent_outfits = (
        db.query(OutfitModel)
        .filter(OutfitModel.user_id == user_id)
        .order_by(OutfitModel.created_at.desc())
        .limit(3)
        .all()
    )
    item_ids: list[int] = []
    for outfit in recent_outfits:
        item_ids.extend(json.loads(outfit.item_ids or "[]"))
    return item_ids


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
