import json
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.profile import ProfileCompletionStatus, ProfileRead, ProfileUpdate
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

LIST_FIELDS = {
    "usual_contexts": "usual_contexts_json",
    "preferred_styles": "preferred_styles_json",
    "preferred_colors": "preferred_colors_json",
    "disliked_colors": "disliked_colors_json",
    "preferred_occasions": "preferred_occasions_json",
}


def encode_list(values: list[str] | None) -> str:
    return json.dumps(values or [])


def decode_list(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def get_or_create_profile(db: Session, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile:
        return profile

    profile = UserProfile(user_id=user_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def profile_to_read(profile: UserProfile) -> ProfileRead:
    return ProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        usual_contexts=decode_list(profile.usual_contexts_json),
        usual_context_other=profile.usual_context_other,
        style_text=profile.style_text,
        formality_level=profile.formality_level,
        comfort_style_level=profile.comfort_style_level,
        modesty_preference=profile.modesty_preference,
        preferred_styles=decode_list(profile.preferred_styles_json),
        preferred_colors=decode_list(profile.preferred_colors_json),
        disliked_colors=decode_list(profile.disliked_colors_json),
        preferred_occasions=decode_list(profile.preferred_occasions_json),
        eastern_western_preference=profile.eastern_western_preference,
        clothing_avoid_text=profile.clothing_avoid_text,
        fit_preference=profile.fit_preference,
        layering_preference=profile.layering_preference,
        accessories_preference=profile.accessories_preference,
        height=profile.height,
        weight=profile.weight,
        collar=profile.collar,
        waist=profile.waist,
        inseam=profile.inseam,
        shoe_size=profile.shoe_size,
        chest=profile.chest,
        shoulder=profile.shoulder,
        sleeve_length=profile.sleeve_length,
        profile_completed=profile.profile_completed,
        completed_at=profile.completed_at,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def get_missing_completion_fields(profile: UserProfile) -> list[str]:
    missing_fields: list[str] = []
    usual_contexts = decode_list(profile.usual_contexts_json)
    preferred_colors = decode_list(profile.preferred_colors_json)
    preferred_styles = decode_list(profile.preferred_styles_json)

    if not usual_contexts:
        missing_fields.append("usual_contexts")
    if "Other" in usual_contexts and not (profile.usual_context_other or "").strip():
        missing_fields.append("usual_context_other")
    if not (profile.style_text or "").strip():
        missing_fields.append("style_text")
    if profile.formality_level is None:
        missing_fields.append("formality_level")
    if profile.comfort_style_level is None:
        missing_fields.append("comfort_style_level")
    if not (profile.modesty_preference or "").strip():
        missing_fields.append("modesty_preference")
    if not (profile.eastern_western_preference or "").strip():
        missing_fields.append("eastern_western_preference")
    if not preferred_colors:
        missing_fields.append("preferred_colors")
    if not preferred_styles:
        missing_fields.append("preferred_styles")
    if not (profile.fit_preference or "").strip():
        missing_fields.append("fit_preference")
    if not (profile.layering_preference or "").strip():
        missing_fields.append("layering_preference")
    if not (profile.accessories_preference or "").strip():
        missing_fields.append("accessories_preference")

    return missing_fields


def get_completion_percentage(profile: UserProfile, missing_fields: list[str]) -> int:
    total_fields = 11
    if "Other" in decode_list(profile.usual_contexts_json):
        total_fields += 1

    completed_fields = max(total_fields - len(missing_fields), 0)
    return round((completed_fields / total_fields) * 100)


def update_completion(profile: UserProfile) -> list[str]:
    missing_fields = get_missing_completion_fields(profile)
    is_complete = not missing_fields

    if is_complete and not profile.profile_completed:
        profile.completed_at = datetime.now(timezone.utc)
    if not is_complete:
        profile.completed_at = None

    profile.profile_completed = is_complete
    return missing_fields


@router.get("/me", response_model=ProfileRead)
def read_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db, current_user.id)
    return profile_to_read(profile)


@router.put("/me", response_model=ProfileRead)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db, current_user.id)
    update_data = payload.model_dump(exclude_unset=True)

    for public_name, column_name in LIST_FIELDS.items():
        if public_name in update_data:
            setattr(profile, column_name, encode_list(update_data.pop(public_name)))

    for field_name, value in update_data.items():
        setattr(profile, field_name, value)

    update_completion(profile)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile_to_read(profile)


@router.get("/me/completion", response_model=ProfileCompletionStatus)
def read_my_profile_completion(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db, current_user.id)
    missing_fields = get_missing_completion_fields(profile)
    return ProfileCompletionStatus(
        profile_completed=not missing_fields,
        missing_fields=missing_fields,
        completion_percentage=get_completion_percentage(profile, missing_fields),
    )
