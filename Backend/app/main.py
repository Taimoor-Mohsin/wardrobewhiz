import logging
import logging.config

from app.api.routes import feedback, health, outfits, profile, wardrobe
from app.core.database import Base, engine
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ── Logging ───────────────────────────────────────────────────────────────────
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-8s %(name)s  %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
})

logger = logging.getLogger(__name__)

# ── DB bootstrap ──────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="WardrobeWhiz API", version="0.1.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(profile.router, prefix="/profiles", tags=["Profiles"])
app.include_router(wardrobe.router, prefix="/wardrobe", tags=["Wardrobe"])
app.include_router(outfits.router, prefix="/outfits", tags=["Outfits"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])


@app.get("/")
def root():
    return {"message": "WardrobeWhiz backend running"}
