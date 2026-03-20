from app.api.routes import health, profile, wardrobe
from app.core.database import Base, engine
from fastapi import FastAPI

Base.metadata.create_all(bind=engine)

app = FastAPI(title="WardrobeWhiz API")

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(profile.router, prefix="/profiles", tags=["Profiles"])
app.include_router(wardrobe.router, prefix="/wardrobe", tags=["Wardrobe"])


@app.get("/")
def root():
    return {"message": "WardrobeWhiz backend running"}
