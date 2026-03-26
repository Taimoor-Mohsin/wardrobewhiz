import json
import os
from typing import Dict, List, Optional, Tuple

from PIL import Image

from app.utils.color_utils import extract_dominant_colors
from app.utils.image_utils import create_thumbnail, open_image, save_upload, validate_image

# Simple category heuristics based on filename keywords (fallback when no ML)
CATEGORY_KEYWORDS = {
    "tops": ["shirt", "top", "tee", "blouse", "sweater", "hoodie", "polo", "tank"],
    "bottoms": ["pants", "jeans", "trouser", "shorts", "skirt", "leggings"],
    "dresses": ["dress", "gown", "jumpsuit", "romper"],
    "jackets": ["jacket", "coat", "blazer", "parka", "cardigan"],
    "shoes": ["shoe", "boot", "sneaker", "heel", "sandal", "loafer", "slipper"],
    "accessories": ["bag", "hat", "scarf", "belt", "watch", "jewel", "necklace", "bracelet", "sunglasses"],
}


def process_upload(
    file_bytes: bytes,
    filename: str,
    upload_dir: str,
    thumbnail_dir: str,
) -> Dict:
    """
    Full pipeline for a wardrobe image upload:
    1. Validate
    2. Save to disk
    3. Create thumbnail
    4. Extract dominant colors
    5. Guess category from filename

    Returns a dict with: image_path, thumbnail_path, dominant_colors, category
    """
    valid, msg = validate_image(file_bytes, filename)
    if not valid:
        raise ValueError(msg)

    image_path = save_upload(file_bytes, filename, upload_dir)
    thumbnail_path = create_thumbnail(image_path, thumbnail_dir)

    img = open_image(image_path)
    dominant_colors: List[str] = []
    if img:
        dominant_colors = extract_dominant_colors(img, n_colors=3)

    category = _guess_category(filename)

    return {
        "image_path": image_path,
        "thumbnail_path": thumbnail_path,
        "dominant_colors": dominant_colors,
        "category": category,
    }


def _guess_category(filename: str) -> Optional[str]:
    """Heuristic: guess clothing category from filename keywords."""
    name_lower = filename.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return None
