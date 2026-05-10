import logging
from pathlib import Path

from app.api.routes import auth, health, outfits, profile, upload, wardrobe
from app.core.config import settings
from app.core.database import Base, engine
from app.core.dev_migrations import apply_sqlite_dev_migrations
from app.models import profile as profile_model, user, wardrobe_item  # noqa: F401
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
apply_sqlite_dev_migrations(engine)

app = FastAPI(title="WardrobeWhiz API")
logger.info(
    "LLM config: groq_key_present=%s gemini_key_present=%s",
    bool(settings.groq_api_key),
    bool(settings.gemini_api_key),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(profile.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(wardrobe.router, prefix="/api/wardrobe", tags=["Wardrobe"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(outfits.router, prefix="/api/outfit", tags=["Outfit"])

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.thumbnail_dir).mkdir(parents=True, exist_ok=True)
segmented_dir = Path(settings.upload_dir).parent / "segmented"
segmented_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount(
    "/static/thumbnails",
    StaticFiles(directory=settings.thumbnail_dir),
    name="thumbnails",
)
app.mount("/static/segmented", StaticFiles(directory=segmented_dir), name="segmented")


@app.get("/")
def root():
    return {"message": "WardrobeWhiz backend running"}
