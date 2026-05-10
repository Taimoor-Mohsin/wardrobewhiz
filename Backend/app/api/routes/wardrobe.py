import asyncio
import json
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
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
from app.services.garment_classifier_service import classify_garment, detect_patterns
from app.services.groq_vision_service import (
    analyze_garment_groq,
    extract_hex_pillow,
    map_llm_metadata_to_wardrobe_fields,
    normalize_llm_taxonomy,
)
from app.services.vision_service import analyze_wardrobe_image, infer_season
from app.services.wardrobe_taxonomy import generate_item_name
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

DEFAULT_CATEGORY_VALUES = {"", "tops"}
DEFAULT_TYPE_VALUES = {"", "shirt"}
DEFAULT_NAME_VALUES = {"", "shirt", "wardrobe item", "new item", "untitled"}
DEFAULT_COLOR_VALUES = {"", "#000000", "black"}
DEFAULT_SEASON_VALUES = {"", "all-season", "all season"}
GROQ_CONFIDENCE_THRESHOLD = 0.6
GROQ_BATCH_CONCURRENCY = 3


@dataclass
class BatchUploadInput:
    index: int
    filename: str | None
    payload: WardrobeItemCreate
    image_path: str


@dataclass
class VisionAnalysisStatus:
    groq_analyzed: bool = False
    used_fallback: bool = False


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


def normalized(value: str | None) -> str:
    return (value or "").strip().lower()


def is_default_value(value: str | None, defaults: set[str]) -> bool:
    return normalized(value) in defaults


def color_label_for_name(color: str | None) -> str | None:
    value = (color or "").strip()
    if not value or value.startswith("#"):
        return None
    return value


def run_groq_analysis_sync(image_path: str) -> dict:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(analyze_garment_groq(image_path))

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(analyze_garment_groq(image_path))).result()


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
    taxonomy = normalize_llm_taxonomy(item.category, item.subcategory, item.subcategory)
    return taxonomy["type"] or item.subcategory or "Other"


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
        dominant_colors=decode_dict_list(item.dominant_colors_json),
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


def apply_mapped_vision_fields(
    item: WardrobeItem,
    mapped_fields: dict,
    force_category: bool = False,
    force_pattern: bool = False,
) -> None:
    dominant_colors = mapped_fields.get("dominant_colors")
    if dominant_colors:
        item.dominant_colors_json = mapped_fields.get("dominant_colors_json") or json.dumps(dominant_colors)

    if is_default_value(item.color, DEFAULT_COLOR_VALUES):
        item.color = mapped_fields.get("color") or item.color
    if force_category or is_default_value(item.category, DEFAULT_CATEGORY_VALUES):
        item.category = mapped_fields.get("category") or item.category
    if force_category or is_default_value(item.subcategory, DEFAULT_TYPE_VALUES):
        item.subcategory = (
            mapped_fields.get("subcategory")
            or mapped_fields.get("type")
            or item.subcategory
        )
    if is_default_value(item.name, DEFAULT_NAME_VALUES):
        item.name = mapped_fields.get("name") or item.name
    if is_default_value(item.season, DEFAULT_SEASON_VALUES):
        item.season = mapped_fields.get("season") or item.season
    if not item.description and mapped_fields.get("description"):
        item.description = mapped_fields["description"]

    pattern_tags = mapped_fields.get("pattern_tags") or mapped_fields.get("tags") or []
    if pattern_tags and (force_pattern or not decode_list(item.pattern_tags_json)):
        item.pattern_tags_json = encode_list(pattern_tags)

    occasion_tags = mapped_fields.get("occasion_tags") or []
    if occasion_tags and not decode_list(item.occasion_tags_json):
        item.occasion_tags_json = encode_list(occasion_tags)


def apply_legacy_vision_fields(
    item: WardrobeItem,
    payload: WardrobeItemCreate,
    classification_path: str,
    vision_result,
    filename_hint: str | None = None,
    force_category: bool = False,
    force_pattern: bool = False,
    category_pattern_only: bool = False,
) -> None:
    if vision_result.dominant_color and not category_pattern_only:
        item.dominant_colors_json = json.dumps(vision_result.dominant_colors)
        if is_default_value(item.color, DEFAULT_COLOR_VALUES):
            item.color = vision_result.dominant_color["label"]

    classification = classify_garment(classification_path, filename_hint=filename_hint)
    taxonomy_item = classification.taxonomy_item
    logger.info(
        "Classified wardrobe upload as %s using %s (confidence %.3f)",
        classification.label,
        classification.model,
        classification.confidence,
    )

    if force_category or is_default_value(item.category, DEFAULT_CATEGORY_VALUES):
        item.category = taxonomy_item.category
    if force_category or is_default_value(item.subcategory, DEFAULT_TYPE_VALUES):
        item.subcategory = taxonomy_item.subcategory

    pattern_tags = detect_patterns(
        classification_path,
        filename_hint=filename_hint,
        dominant_colors=vision_result.dominant_colors,
    )
    if pattern_tags and (force_pattern or not decode_list(item.pattern_tags_json)):
        item.pattern_tags_json = encode_list(pattern_tags)

    if category_pattern_only:
        return

    if is_default_value(item.name, DEFAULT_NAME_VALUES):
        item.name = generate_item_name(
            color_label_for_name(item.color),
            taxonomy_item.type,
            dominant_colors=vision_result.dominant_colors,
            pattern_tags=pattern_tags,
        )

    if is_default_value(item.season, DEFAULT_SEASON_VALUES):
        item.season = infer_season(
            item.category,
            taxonomy_item.type,
            item.subcategory,
            color_label_for_name(item.color),
        )


def apply_upload_vision(
    item: WardrobeItem,
    payload: WardrobeItemCreate,
    filename_hint: str | None = None,
) -> None:
    original_category_was_default = is_default_value(item.category, DEFAULT_CATEGORY_VALUES)
    original_type_was_default = is_default_value(item.subcategory, DEFAULT_TYPE_VALUES)
    original_tags_were_empty = not decode_list(item.pattern_tags_json)

    vision_result = analyze_wardrobe_image(
        item.image_path,
        category=item.category,
        item_type=payload.type,
        subcategory=item.subcategory,
    )
    if vision_result.segmented_image_path:
        item.segmented_image_path = vision_result.segmented_image_path

    analysis_path = item.segmented_image_path or item.image_path
    try:
        color_hex = extract_hex_pillow(analysis_path)
    except Exception as exc:
        logger.warning("Pillow color hex extraction failed for upload: %s", exc)
        color_hex = (
            str(vision_result.dominant_color.get("hex"))
            if vision_result.dominant_color
            else None
        )

    try:
        groq_metadata = run_groq_analysis_sync(analysis_path)
        mapped_fields = map_llm_metadata_to_wardrobe_fields(groq_metadata, color_hex)
        confidence = float(mapped_fields.get("confidence", 0.0))
        logger.info("Groq garment analysis confidence %.2f", confidence)

        apply_mapped_vision_fields(item, mapped_fields)
        if confidence < GROQ_CONFIDENCE_THRESHOLD:
            logger.warning(
                "Groq garment analysis confidence %.2f below %.2f; patching category/pattern with local fallback",
                confidence,
                GROQ_CONFIDENCE_THRESHOLD,
            )
            apply_legacy_vision_fields(
                item,
                payload,
                analysis_path,
                vision_result,
                filename_hint=filename_hint,
                force_category=original_category_was_default or original_type_was_default,
                force_pattern=original_tags_were_empty,
                category_pattern_only=True,
            )
    except Exception as exc:
        logger.warning("Groq garment analysis failed; using local vision fallback: %s", exc)
        apply_legacy_vision_fields(
            item,
            payload,
            analysis_path,
            vision_result,
            filename_hint=filename_hint,
        )


async def apply_upload_vision_async(
    item: WardrobeItem,
    payload: WardrobeItemCreate,
    filename_hint: str | None,
    semaphore: asyncio.Semaphore,
) -> VisionAnalysisStatus:
    async with semaphore:
        status = VisionAnalysisStatus()
        original_category_was_default = is_default_value(item.category, DEFAULT_CATEGORY_VALUES)
        original_type_was_default = is_default_value(item.subcategory, DEFAULT_TYPE_VALUES)
        original_tags_were_empty = not decode_list(item.pattern_tags_json)

        try:
            vision_result = await asyncio.to_thread(
                analyze_wardrobe_image,
                item.image_path,
                category=item.category,
                item_type=payload.type,
                subcategory=item.subcategory,
            )
        except Exception as exc:
            status.used_fallback = True
            logger.warning(
                "Batch local image preprocessing failed; saving upload with provided metadata: %s",
                exc,
            )
            return status
        if vision_result.segmented_image_path:
            item.segmented_image_path = vision_result.segmented_image_path

        analysis_path = item.segmented_image_path or item.image_path
        try:
            color_hex = await asyncio.to_thread(extract_hex_pillow, analysis_path)
        except Exception as exc:
            logger.warning("Pillow color hex extraction failed for batch upload: %s", exc)
            color_hex = (
                str(vision_result.dominant_color.get("hex"))
                if vision_result.dominant_color
                else None
            )

        try:
            groq_metadata = await analyze_garment_groq(analysis_path)
            status.groq_analyzed = True
            mapped_fields = map_llm_metadata_to_wardrobe_fields(groq_metadata, color_hex)
            confidence = float(mapped_fields.get("confidence", 0.0))
            logger.info("Groq garment batch analysis confidence %.2f", confidence)

            apply_mapped_vision_fields(item, mapped_fields)
            if confidence < GROQ_CONFIDENCE_THRESHOLD:
                status.used_fallback = True
                logger.warning(
                    "Groq garment batch analysis confidence %.2f below %.2f; patching category/pattern with local fallback",
                    confidence,
                    GROQ_CONFIDENCE_THRESHOLD,
                )
                await asyncio.to_thread(
                    apply_legacy_vision_fields,
                    item,
                    payload,
                    analysis_path,
                    vision_result,
                    filename_hint=filename_hint,
                    force_category=original_category_was_default or original_type_was_default,
                    force_pattern=original_tags_were_empty,
                    category_pattern_only=True,
                )
        except Exception as exc:
            status.used_fallback = True
            logger.warning("Groq garment batch analysis failed; using local vision fallback: %s", exc)
            await asyncio.to_thread(
                apply_legacy_vision_fields,
                item,
                payload,
                analysis_path,
                vision_result,
                filename_hint=filename_hint,
            )

        return status


def build_item_for_user(
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
    return item


def persist_item(db: Session, item: WardrobeItem) -> WardrobeItem:
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


async def create_batch_items_for_user(
    db: Session,
    user_id: int,
    uploads: list[BatchUploadInput],
) -> WardrobeUploadResponse:
    logger.info("Starting batch upload analysis for %d images", len(uploads))
    semaphore = asyncio.Semaphore(GROQ_BATCH_CONCURRENCY)
    prepared_items: list[tuple[BatchUploadInput, WardrobeItem]] = [
        (upload, build_item_for_user(user_id, upload.payload, upload.image_path))
        for upload in uploads
    ]

    analysis_results = await asyncio.gather(
        *(
            apply_upload_vision_async(item, upload.payload, upload.filename, semaphore)
            for upload, item in prepared_items
        ),
        return_exceptions=True,
    )

    items: list[WardrobeItemRead] = []
    errors: list[str] = []
    groq_count = 0
    fallback_count = 0

    for (upload, item), result in zip(prepared_items, analysis_results, strict=False):
        filename = upload.filename or f"file {upload.index + 1}"
        if isinstance(result, Exception):
            fallback_count += 1
            logger.warning("Batch upload analysis failed for item %d: %s", upload.index, result)
            errors.append(f"{filename}: {result}")
            continue

        if result.groq_analyzed:
            groq_count += 1
        if result.used_fallback:
            fallback_count += 1

        try:
            persist_item(db, item)
            items.append(item_to_read(item))
        except Exception as exc:  # pragma: no cover - defensive DB isolation
            db.rollback()
            errors.append(f"{filename}: {exc}")

    logger.info(
        "Batch upload analysis complete: images=%d groq_analyzed=%d fallback=%d",
        len(uploads),
        groq_count,
        fallback_count,
    )
    return WardrobeUploadResponse(items=items, errors=errors)


def create_item_for_user(
    db: Session,
    user_id: int,
    payload: WardrobeItemCreate,
    image_path: str | None = None,
    run_vision: bool = False,
    filename_hint: str | None = None,
) -> WardrobeItem:
    item = build_item_for_user(user_id, payload, image_path)

    if run_vision and item.image_path:
        apply_upload_vision(item, payload, filename_hint=filename_hint)

    return persist_item(db, item)


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
async def upload_wardrobe_items(
    files: list[UploadFile] = File(...),
    metadata: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uploads: list[BatchUploadInput] = []
    errors: list[str] = []

    for index, file in enumerate(files):
        try:
            file_metadata = metadata_from_json(metadata)
            image_path = save_upload_file(file)
            uploads.append(
                BatchUploadInput(
                    index=index,
                    filename=file.filename,
                    payload=file_metadata,
                    image_path=image_path,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive batch isolation
            errors.append(f"{file.filename or f'file {index + 1}'}: {exc}")

    batch_response = await create_batch_items_for_user(db, current_user.id, uploads)
    return WardrobeUploadResponse(
        items=batch_response.items,
        errors=[*errors, *batch_response.errors],
    )


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
