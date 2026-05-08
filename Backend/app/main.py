from app.api.routes import health, profile, wardrobe
from app.core.database import Base, engine
from app.models import profile as profile_model, user, wardrobe_item  # noqa: F401
from fastapi import FastAPI

Base.metadata.create_all(bind=engine)

app = FastAPI(title="WardrobeWhiz API")

app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(profile.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(wardrobe.router, prefix="/api/wardrobe", tags=["Wardrobe"])


@app.get("/")
def root():
    return {"message": "WardrobeWhiz backend running"}
