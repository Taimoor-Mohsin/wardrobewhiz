from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def wardrobe_placeholder():
    return {"message": "Wardrobe routes placeholder"}
