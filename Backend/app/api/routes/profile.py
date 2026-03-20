from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def profile_placeholder():
    return {"message": "Profile routes placeholder"}
