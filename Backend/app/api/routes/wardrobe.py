import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem
from app.schemas.wardrobe import (
    WardrobeItemCreate,
    WardrobeItemRead,
    WardrobeItemUpdate,
    WardrobeStats,
    WardrobeUploadResponse,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

router = APIRouter()

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
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


def public_path(path: str | None) -> str | None:
    if not path:
        return None
    normalized_path = path.replace("\\", "/")
    filename = Path(normalized_path).name
    if "/uploads/" in normalized_path:
        return f"/static/uploads/{filename}"
    if "/thumbnails/" in normalized_path:
        return f"/static/thumbnails/{filename}"
    if "/segmented/" in normalized_path:
        return f"/static/segmented/{filename}"
    return "/" + normalized_path.lstrip("/")


def item_type(item: WardrobeItem) -> str:
    return item.subcategory or "Other"


def item_to_read(item: WardrobeItem) -> WardrobeItemRead:
    image_url = public_path(item.image_path) or ""
    thumbnail_url = public_path(item.thumbnail_path)
    return WardrobeItemRead(
        id=item.id,
        user_id=item.user_id,
        userId=str(item.user_id),
        name=item.name or item.subcategory or item.category or "Wardrobe item",
        category=item.category,
        type=item_type(item),
        subcategory=item.subcategory,
        color=item.color,
        season=item.season,
        description=item.description,
        notes=item.notes,
        tags=decode_list(item.pattern_tags_json),
        image_path=item.image_path,
        imageUrl=image_url,
        thumbnail_path=item.thumbnail_path,
        thumbnailUrl=thumbnail_url,
        segmented_image_path=item.segmented_image_path,
        created_at=item.created_at,
        createdAt=item.created_at,
        updated_at=item.updated_at,
        updatedAt=item.updated_at,
        lastWorn=item.last_worn,
        wearCount=item.wear_count or 0,
    )


def get_owned_item(db: Session, item_id: int, user_id: int) -> WardrobeItem:
    item = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.id == item_id, WardrobeItem.user_id == user_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    return item


def apply_item_payload(item: WardrobeItem, payload: WardrobeItemCreate | WardrobeItemUpdate) -> None:
    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("user_id", None)

    if "type" in update_data:
        item.subcategory = update_data.pop("type") or item.subcategory
    if "tags" in update_data:
        item.pattern_tags_json = encode_list(update_data.pop("tags"))

    for field_name in [
        "name",
        "category",
        "subcategory",
        "color",
        "season",
        "description",
        "notes",
        "image_path",
        "segmented_image_path",
    ]:
        if field_name in update_data:
            setattr(item, field_name, update_data[field_name])


def create_item_for_user(
    db: Session,
    user_id: int,
    payload: WardrobeItemCreate,
    image_path: str | None = None,
) -> WardrobeItem:
    item = WardrobeItem(
        user_id=user_id,
        image_path=image_path or payload.image_path or "",
    )
    apply_item_payload(item, payload)
    if image_path:
        item.image_path = image_path

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def save_upload_file(file: UploadFile) -> str:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = CONTENT_TYPE_EXTENSIONS.get(file.content_type or "", ".jpg")
    filename = f"{uuid4().hex}{suffix}"
    destination = upload_dir / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return str(destination)


def metadata_from_json(raw_metadata: str | None) -> WardrobeItemCreate:
    if not raw_metadata:
        return WardrobeItemCreate()
    try:
        data = json.loads(raw_metadata)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Metadata must be an object")
    return WardrobeItemCreate(**data)


@router.get("", response_model=list[WardrobeItemRead])
@router.get("/", response_model=list[WardrobeItemRead])
def list_wardrobe_items(
    category: str | None = None,
    color: str | None = None,
    season: str | None = None,
    type: str | None = None,
    searchQuery: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WardrobeItem).filter(WardrobeItem.user_id == current_user.id)

    if category and category != "All":
        query = query.filter(WardrobeItem.category == category)
    if color:
        query = query.filter(WardrobeItem.color == color)
    if season and season != "All":
        query = query.filter(WardrobeItem.season == season)
    if type and type != "All":
        query = query.filter(WardrobeItem.subcategory == type)
    if searchQuery:
        like_value = f"%{searchQuery}%"
        query = query.filter(
            (WardrobeItem.name.ilike(like_value))
            | (WardrobeItem.description.ilike(like_value))
            | (WardrobeItem.notes.ilike(like_value))
        )

    items = query.order_by(WardrobeItem.created_at.desc()).all()
    return [item_to_read(item) for item in items]


@router.post("", response_model=WardrobeItemRead)
@router.post("/", response_model=WardrobeItemRead)
def create_wardrobe_item(
    payload: WardrobeItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = create_item_for_user(db, current_user.id, payload)
    return item_to_read(item)


@router.post("/upload", response_model=WardrobeUploadResponse)
def upload_wardrobe_items(
    files: list[UploadFile] = File(...),
    metadata: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items: list[WardrobeItemRead] = []
    errors: list[str] = []

    for index, file in enumerate(files):
        try:
            file_metadata = metadata_from_json(metadata)
            image_path = save_upload_file(file)
            item = create_item_for_user(db, current_user.id, file_metadata, image_path)
            items.append(item_to_read(item))
        except Exception as exc:  # pragma: no cover - defensive batch isolation
            errors.append(f"{file.filename or f'file {index + 1}'}: {exc}")

    return WardrobeUploadResponse(items=items, errors=errors)


@router.get("/stats", response_model=WardrobeStats)
def get_wardrobe_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == current_user.id)
        .order_by(WardrobeItem.created_at.desc())
        .all()
    )

    by_category: dict[str, int] = {}
    by_season: dict[str, int] = {}
    for item in items:
        if item.category:
            by_category[item.category] = by_category.get(item.category, 0) + 1
        if item.season:
            by_season[item.season] = by_season.get(item.season, 0) + 1

    sorted_by_wear = sorted(items, key=lambda item: item.wear_count or 0, reverse=True)
    total_wears = sum(item.wear_count or 0 for item in items)
    return WardrobeStats(
        totalItems=len(items),
        itemsByCategory=by_category,
        itemsBySeason=by_season,
        mostWorn=[item_to_read(item) for item in sorted_by_wear[:5]],
        leastWorn=[item_to_read(item) for item in sorted_by_wear[-5:]],
        rewearRate=(total_wears / len(items)) if items else 0,
    )


@router.get("/{item_id}", response_model=WardrobeItemRead)
def get_wardrobe_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return item_to_read(get_owned_item(db, item_id, current_user.id))


@router.patch("/{item_id}", response_model=WardrobeItemRead)
def update_wardrobe_item(
    item_id: int,
    payload: WardrobeItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_owned_item(db, item_id, current_user.id)
    apply_item_payload(item, payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item_to_read(item)


@router.delete("/{item_id}", status_code=204)
def delete_wardrobe_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_owned_item(db, item_id, current_user.id)
    db.delete(item)
    db.commit()
    return None


@router.post("/{item_id}/worn", response_model=WardrobeItemRead)
def mark_item_worn(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_owned_item(db, item_id, current_user.id)
    item.wear_count = (item.wear_count or 0) + 1
    item.last_worn = datetime.now(timezone.utc)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item_to_read(item)
