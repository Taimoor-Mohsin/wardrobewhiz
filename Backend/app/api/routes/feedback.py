from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.feedback import OutfitFeedback
from app.models.outfit import Outfit
from app.models.user import User
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    outfit = (
        db.query(Outfit)
        .filter(Outfit.id == request.outfit_id, Outfit.user_id == current_user.id)
        .first()
    )
    if not outfit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found.",
        )

    feedback = OutfitFeedback(
        outfit_id=request.outfit_id,
        user_id=current_user.id,
        rating=request.rating,
    )
    db.add(feedback)
    db.commit()
    return FeedbackResponse(message="Feedback recorded")
