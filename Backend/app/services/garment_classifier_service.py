import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from app.services.wardrobe_taxonomy import (
    DEFAULT_TAXONOMY_ITEM,
    TaxonomyItem,
    prompt_entries,
    taxonomy_item_from_filename,
)

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
HF_CACHE_DIR = Path(__file__).resolve().parents[1] / "storage" / "hf_cache"
FASHION_CLIP_MODEL_ID = "patrickjohncyh/fashion-clip"

PATTERN_PROMPTS: dict[str, tuple[str, ...]] = {
    "solid": (
        "a photo of a solid plain garment with no print",
        "a product photo of a plain solid color clothing item",
    ),
    "striped": (
        "a photo of a striped garment",
        "a product photo of clothing with horizontal or vertical stripes",
    ),
    "plaid": (
        "a photo of a plaid garment",
        "a product photo of clothing with a plaid tartan pattern",
    ),
    "checked": (
        "a photo of a checked garment",
        "a product photo of clothing with a checkered pattern",
    ),
    "floral": (
        "a photo of a floral dress or garment",
        "a product photo of clothing with a flower print",
    ),
    "polka dot": (
        "a photo of a polka dot garment",
        "a product photo of clothing with dot print",
    ),
    "graphic": (
        "a photo of a graphic t-shirt",
        "a product photo of clothing with a printed graphic design",
    ),
    "logo": (
        "a photo of a garment with a visible logo",
        "a product photo of clothing with a logo print",
    ),
    "colorblock": (
        "a photo of colorblock clothing with large blocks of different colors",
        "a product photo of a two tone color blocked garment",
    ),
    "geometric": (
        "a photo of a geometric print garment",
        "a product photo of clothing with geometric shapes",
    ),
    "animal print": (
        "a photo of animal print clothing",
        "a product photo of leopard zebra or animal print fabric",
    ),
    "camouflage": (
        "a photo of camouflage clothing",
        "a product photo of clothing with camo print",
    ),
    "denim wash": (
        "a photo of denim wash fabric",
        "a product photo of washed denim clothing",
    ),
    "embroidered": (
        "a photo of embroidered clothing",
        "a product photo of a garment with embroidery",
    ),
    "textured": (
        "a photo of textured fabric clothing",
        "a product photo of a garment with visible fabric texture",
    ),
}


def load_backend_env() -> None:
    env_path = BACKEND_DIR / ".env"
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception as exc:  # pragma: no cover - dotenv is optional at runtime
        logger.debug("Backend .env load skipped: %s", exc)

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def configure_hugging_face_cache() -> None:
    load_backend_env()
    HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (HF_CACHE_DIR / "hub").mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(HF_CACHE_DIR)
    os.environ["HF_HUB_CACHE"] = str(HF_CACHE_DIR / "hub")
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
        os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token
    logger.info(
        "Hugging Face model config: hf_token_present=%s HF_HOME=%s HF_HUB_CACHE=%s",
        bool(hf_token),
        os.environ["HF_HOME"],
        os.environ["HF_HUB_CACHE"],
    )


configure_hugging_face_cache()


@dataclass
class GarmentClassification:
    label: str
    confidence: float
    model: str
    taxonomy_item: TaxonomyItem


@dataclass
class PatternClassification:
    label: str
    confidence: float
    model: str


@lru_cache(maxsize=1)
def _load_fashion_clip():
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        model_kwargs = {
            "cache_dir": str(HF_CACHE_DIR / "hub"),
        }
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            model_kwargs["token"] = hf_token

        processor = CLIPProcessor.from_pretrained(FASHION_CLIP_MODEL_ID, **model_kwargs)
        model = CLIPModel.from_pretrained(FASHION_CLIP_MODEL_ID, **model_kwargs)
        model.eval()
        entries = prompt_entries()
        prompts = [prompt for _, prompt in entries]

        with torch.no_grad():
            text_inputs = processor(
                text=prompts,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            text_features = model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        logger.info("FashionCLIP transformers model loaded: %s", FASHION_CLIP_MODEL_ID)
        return torch, model, processor, entries, text_features
    except Exception as exc:  # pragma: no cover - optional dependency/runtime
        logger.warning(
            "FashionCLIP transformers load failed for %s; falling back to OpenCLIP/rules: %s",
            FASHION_CLIP_MODEL_ID,
            exc,
        )
        return None


@lru_cache(maxsize=1)
def _load_open_clip():
    try:
        import open_clip
        import torch

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k",
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        model.eval()

        entries = prompt_entries()
        prompts = [prompt for _, prompt in entries]
        with torch.no_grad():
            text_tokens = tokenizer(prompts)
            text_features = model.encode_text(text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return torch, model, preprocess, tokenizer, entries, text_features
    except Exception as exc:  # pragma: no cover - optional model/runtime
        logger.warning("OpenCLIP unavailable, using rule fallback: %s", exc)
        return None


def _normalize_numpy(values):
    array = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return array / norms


def _confidence_from_scores(scores: np.ndarray, best_index: int) -> float:
    shifted = scores - np.max(scores)
    probabilities = np.exp(shifted) / np.sum(np.exp(shifted))
    return float(probabilities[best_index])


def _classification_from_prompt_scores(
    scores: np.ndarray,
    entries: list[tuple[TaxonomyItem, str]],
    model_name: str,
) -> GarmentClassification:
    label_scores: dict[str, float] = {}
    label_items: dict[str, TaxonomyItem] = {}

    for score, (item, _) in zip(scores, entries, strict=False):
        previous_score = label_scores.get(item.label)
        if previous_score is None or score > previous_score:
            label_scores[item.label] = float(score)
            label_items[item.label] = item

    labels = list(label_scores.keys())
    label_score_array = np.array([label_scores[label] for label in labels], dtype=np.float32)
    best_index = int(np.argmax(label_score_array))
    label = labels[best_index]
    return GarmentClassification(
        label=label,
        confidence=_confidence_from_scores(label_score_array, best_index),
        model=model_name,
        taxonomy_item=label_items[label],
    )


def pattern_prompt_entries() -> list[tuple[str, str]]:
    return [(label, prompt) for label, prompts in PATTERN_PROMPTS.items() for prompt in prompts]


def _pattern_from_prompt_scores(
    scores: np.ndarray,
    entries: list[tuple[str, str]],
    model_name: str,
) -> PatternClassification:
    label_scores: dict[str, float] = {}

    for score, (label, _) in zip(scores, entries, strict=False):
        previous_score = label_scores.get(label)
        if previous_score is None or score > previous_score:
            label_scores[label] = float(score)

    labels = list(label_scores.keys())
    label_score_array = np.array([label_scores[label] for label in labels], dtype=np.float32)
    best_index = int(np.argmax(label_score_array))
    label = labels[best_index]
    return PatternClassification(
        label=label,
        confidence=_confidence_from_scores(label_score_array, best_index),
        model=model_name,
    )


def _classify_with_fashion_clip(image_path: str) -> GarmentClassification | None:
    loaded = _load_fashion_clip()
    if not loaded:
        return None

    try:
        torch, model, processor, entries, text_features = loaded
        image = Image.open(image_path).convert("RGB")
        with torch.no_grad():
            image_inputs = processor(images=image, return_tensors="pt")
            image_features = model.get_image_features(**image_inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            scores = (image_features @ text_features.T).squeeze(0).cpu().numpy()
        return _classification_from_prompt_scores(
            scores,
            entries,
            f"FashionCLIP transformers ({FASHION_CLIP_MODEL_ID})",
        )
    except Exception as exc:  # pragma: no cover - optional model/runtime
        logger.warning("FashionCLIP classification failed for %s: %s", image_path, exc)
        return None


def _classify_with_open_clip(image_path: str) -> GarmentClassification | None:
    loaded = _load_open_clip()
    if not loaded:
        return None

    try:
        torch, model, preprocess, _, entries, text_features = loaded
        image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            image_features = model.encode_image(image)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            scores = (image_features @ text_features.T).squeeze(0).cpu().numpy()
        return _classification_from_prompt_scores(scores, entries, "OpenCLIP ViT-B-32")
    except Exception as exc:  # pragma: no cover - optional model/runtime
        logger.warning("OpenCLIP classification failed for %s: %s", image_path, exc)
        return None


def _classify_pattern_with_fashion_clip(image_path: str) -> PatternClassification | None:
    loaded = _load_fashion_clip()
    if not loaded:
        return None

    try:
        torch, model, processor, _, _ = loaded
        entries = pattern_prompt_entries()
        prompts = [prompt for _, prompt in entries]
        image = Image.open(image_path).convert("RGB")
        with torch.no_grad():
            text_inputs = processor(
                text=prompts,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            text_features = model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            image_inputs = processor(images=image, return_tensors="pt")
            image_features = model.get_image_features(**image_inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            scores = (image_features @ text_features.T).squeeze(0).cpu().numpy()
        return _pattern_from_prompt_scores(
            scores,
            entries,
            f"FashionCLIP transformers ({FASHION_CLIP_MODEL_ID})",
        )
    except Exception as exc:  # pragma: no cover - optional model/runtime
        logger.warning("FashionCLIP pattern classification failed for %s: %s", image_path, exc)
        return None


def _classify_pattern_with_open_clip(image_path: str) -> PatternClassification | None:
    loaded = _load_open_clip()
    if not loaded:
        return None

    try:
        torch, model, preprocess, tokenizer, _, _ = loaded
        entries = pattern_prompt_entries()
        prompts = [prompt for _, prompt in entries]
        image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            text_tokens = tokenizer(prompts)
            text_features = model.encode_text(text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            image_features = model.encode_image(image)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            scores = (image_features @ text_features.T).squeeze(0).cpu().numpy()
        return _pattern_from_prompt_scores(scores, entries, "OpenCLIP ViT-B-32")
    except Exception as exc:  # pragma: no cover - optional model/runtime
        logger.warning("OpenCLIP pattern classification failed for %s: %s", image_path, exc)
        return None


def _patterns_from_rules(
    image_path: str,
    filename_hint: str | None = None,
    dominant_colors: list[dict] | None = None,
) -> list[str]:
    filename = f"{filename_hint or ''} {Path(image_path).stem}".lower()
    for label in PATTERN_PROMPTS:
        if label != "solid" and label.replace(" ", "") in filename.replace("_", "").replace("-", ""):
            return [label]
    if "flower" in filename:
        return ["floral"]
    if "camo" in filename:
        return ["camouflage"]
    if "embroider" in filename:
        return ["embroidered"]

    if dominant_colors and len(dominant_colors) > 1:
        secondary_percentage = float(dominant_colors[1].get("percentage", 0))
        if secondary_percentage >= 0.25:
            return ["colorblock"]
    return []


def _classify_with_rules(image_path: str, filename_hint: str | None = None) -> GarmentClassification:
    taxonomy_item = (
        taxonomy_item_from_filename(filename_hint or "")
        or taxonomy_item_from_filename(image_path)
        or DEFAULT_TAXONOMY_ITEM
    )
    confidence = 0.55 if taxonomy_item != DEFAULT_TAXONOMY_ITEM else 0.0
    model_name = "filename-rules" if confidence else "default-rules"
    return GarmentClassification(
        label=taxonomy_item.label,
        confidence=confidence,
        model=model_name,
        taxonomy_item=taxonomy_item,
    )


def classify_garment(image_path: str, filename_hint: str | None = None) -> GarmentClassification:
    classification = _classify_with_fashion_clip(image_path)
    if classification:
        return classification

    logger.info("Using OpenCLIP fallback for garment classification")
    classification = _classify_with_open_clip(image_path)
    if classification:
        return classification

    logger.info("Using rule-based fallback for garment classification")
    return _classify_with_rules(image_path, filename_hint)


def detect_patterns(
    image_path: str,
    filename_hint: str | None = None,
    dominant_colors: list[dict] | None = None,
) -> list[str]:
    classification = _classify_pattern_with_fashion_clip(image_path)
    if not classification:
        logger.info("Using OpenCLIP fallback for pattern classification")
        classification = _classify_pattern_with_open_clip(image_path)

    if classification and classification.confidence >= 0.16:
        logger.info(
            "Detected pattern as %s using %s (confidence %.3f)",
            classification.label,
            classification.model,
            classification.confidence,
        )
        if classification.label == "solid":
            return ["solid"] if classification.confidence >= 0.24 else []
        tags = [classification.label]
        if (
            dominant_colors
            and len(dominant_colors) > 1
            and float(dominant_colors[1].get("percentage", 0)) >= 0.25
            and "colorblock" not in tags
            and classification.label in {"solid", "textured"}
        ):
            tags.append("colorblock")
        return tags

    logger.info("Using rule-based fallback for pattern classification")
    return _patterns_from_rules(image_path, filename_hint, dominant_colors)
