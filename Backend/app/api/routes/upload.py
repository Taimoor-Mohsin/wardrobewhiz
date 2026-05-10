from app.api.routes.wardrobe import (
    create_item_for_user,
    item_to_read,
    metadata_from_json,
    save_upload_file,
)
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.wardrobe import WardrobeItemRead, WardrobeUploadResponse
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/image", response_model=WardrobeItemRead)
def upload_image(
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_path = save_upload_file(file)
    item = create_item_for_user(
        db,
        current_user.id,
        metadata_from_json(metadata),
        image_path,
    )
    return item_to_read(item)


@router.post("/batch", response_model=WardrobeUploadResponse)
async def upload_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    items: list[WardrobeItemRead] = []
    errors: list[str] = []

    for index, file in enumerate(files):
        try:
            metadata = metadata_from_json(form.get(f"metadata_{index}"))
            image_path = save_upload_file(file)
            item = create_item_for_user(db, current_user.id, metadata, image_path)
            items.append(item_to_read(item))
        except Exception as exc:  # pragma: no cover - defensive batch isolation
            errors.append(f"{file.filename or f'file {index + 1}'}: {exc}")

    return WardrobeUploadResponse(items=items, errors=errors)
