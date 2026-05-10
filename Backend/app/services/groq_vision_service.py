import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from PIL import Image

GARMENT_PROMPT = """
You are a fashion expert and wardrobe cataloging assistant analyzing a clothing item image.
Return ONLY a valid JSON object. No markdown. No explanation. No extra text.

{
  "name": "specific descriptive name e.g. Green Floral Tiered Sundress, Light Blue Acid Wash Skinny Jeans",
  "category": "one of: Tops, Bottoms, Dresses, Outerwear, Footwear, Accessories",
  "type": "specific type e.g. Sundress, Skinny Jeans, Sneakers, Hoodie, Blazer",
  "subcategory": "more specific e.g. Tiered Dress, Distressed Jeans, Low-Top Sneakers",
  "color_label": "precise human color name e.g. Bright Green, Light Blue, Cream, Burgundy",
  "pattern": "one of: solid, floral, striped, plaid, colorblock, graphic, denim wash, animal print, geometric, textured, embroidered, camouflage, polka dot, abstract",
  "season": "one of: Summer, Winter, Spring, Fall, All-Season",
  "occasion": ["list of occasions e.g. casual, formal, beach, work, party, gym, vacation"],
  "style_tags": ["list of style descriptors e.g. feminine, oversized, streetwear, minimalist, bohemian"],
  "description": "2-3 sentence natural language description of the item"
}

Critical rules:
- Washed or faded denim jeans are NEVER grey. Call them light blue, acid wash, or stone wash.
- A dress with repeated flower motifs is floral, NOT colorblock.
- Colorblock means large solid blocks of two or more distinct colors with clean boundaries.
- Bright green is NOT olive. Olive is a dark muted yellow-green.
- Be specific in naming — avoid generic names like just Dress or Jeans.
- Season should reflect the garment visually, not just the type. A floral mini dress is Summer not Fall.
"""

GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
ALLOWED_CATEGORIES = {"Tops", "Bottoms", "Dresses", "Outerwear", "Footwear", "Accessories"}
ALLOWED_PATTERNS = {
    "solid",
    "floral",
    "striped",
    "plaid",
    "colorblock",
    "graphic",
    "denim wash",
    "animal print",
    "geometric",
    "textured",
    "embroidered",
    "camouflage",
    "polka dot",
    "abstract",
}
ALLOWED_SEASONS = {"Summer", "Winter", "Spring", "Fall", "All-Season"}
VAGUE_COLORS = {"unknown", "mixed", "multicolor", "multi-color", "various", ""}
FASHION_COLOR_PALETTE: dict[str, tuple[str, str]] = {
    "black": ("Black", "#181818"),
    "charcoal": ("Charcoal", "#3A3A3A"),
    "white": ("White", "#F5F5F5"),
    "cream": ("Cream", "#F4ECDD"),
    "grey": ("Grey", "#808080"),
    "gray": ("Grey", "#808080"),
    "navy": ("Navy", "#283856"),
    "blue": ("Blue", "#4273BE"),
    "light blue": ("Light Blue", "#A8C6E6"),
    "denim blue": ("Denim Blue", "#5C7094"),
    "red": ("Red", "#BA2D34"),
    "maroon": ("Maroon", "#742636"),
    "burgundy": ("Burgundy", "#742636"),
    "pink": ("Pink", "#D68AA2"),
    "green": ("Green", "#4D7952"),
    "bright green": ("Bright Green", "#3FA34D"),
    "olive green": ("Olive Green", "#6F743F"),
    "olive": ("Olive", "#6F743F"),
    "mint": ("Mint", "#A6D1B4"),
    "yellow": ("Yellow", "#E4C658"),
    "mustard": ("Mustard", "#B69136"),
    "orange": ("Orange", "#D17D44"),
    "beige": ("Beige", "#D8C9A3"),
    "cream beige": ("Cream Beige", "#D8C9A3"),
    "brown": ("Brown", "#6E4F3A"),
    "dark brown": ("Dark Brown", "#3F2B1F"),
    "tan": ("Tan", "#B2916A"),
    "khaki": ("Khaki", "#A39A6D"),
    "purple": ("Purple", "#805E90"),
}
CUE_WORDS = {"with", "and", "plus", "accent", "accents", "trim", "graphic", "logo"}
CATEGORY_ALIASES = {
    "top": "Tops",
    "tops": "Tops",
    "shirt": "Tops",
    "bottom": "Bottoms",
    "bottoms": "Bottoms",
    "pants": "Bottoms",
    "trousers": "Bottoms",
    "dress": "Dresses",
    "dresses": "Dresses",
    "outerwear": "Outerwear",
    "jacket": "Outerwear",
    "coat": "Outerwear",
    "footwear": "Footwear",
    "shoe": "Footwear",
    "shoes": "Footwear",
    "sneakers": "Footwear",
    "accessory": "Accessories",
    "accessories": "Accessories",
}
TYPE_CATEGORY_HINTS = (
    ({"hoodie"}, "Tops"),
    ({"t-shirt", "tshirt", "tee", "shirt", "polo", "sweater", "kurta"}, "Tops"),
    ({"jeans", "trousers", "pants", "shorts", "skirt"}, "Bottoms"),
    ({"dress", "sundress", "saree"}, "Dresses"),
    ({"jacket", "coat", "blazer", "waistcoat"}, "Outerwear"),
    ({"sneaker", "sneakers", "boot", "boots", "loafer", "loafers", "sandal", "sandals", "shoe", "shoes"}, "Footwear"),
)
KNOWN_TYPES_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "Tops": ("Shirt", "T-Shirt", "Polo Shirt", "Sweater", "Hoodie", "Kurta", "Other"),
    "Bottoms": ("Pants", "Trousers", "Jeans", "Shorts", "Skirt", "Other"),
    "Footwear": ("Shoes", "Boots", "Sneakers", "Loafers", "Sandals", "Formal Shoes", "Other"),
    "Accessories": ("Hat", "Bag", "Jewelry", "Other"),
    "Outerwear": ("Jacket", "Coat", "Blazer", "Waistcoat", "Other"),
    "Dresses": ("Dress", "Saree", "Other"),
}


class GroqVisionError(RuntimeError):
    pass


def _load_backend_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception:
        pass


def _image_data_url(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise GroqVisionError(f"Image not found: {image_path}")

    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def clean_json_response(raw: str) -> dict:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise GroqVisionError("Groq response did not contain a JSON object")
        parsed = json.loads(text[start : end + 1])

    if not isinstance(parsed, dict):
        raise GroqVisionError("Groq response JSON was not an object")
    return parsed


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_choice(value: Any, allowed_values: set[str], default: str) -> str:
    cleaned = _clean_string(value)
    for allowed_value in allowed_values:
        if cleaned.lower() == allowed_value.lower():
            return allowed_value
    return default


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean_string(item) for item in value if _clean_string(item)]


def _normalize_metadata(metadata: dict) -> dict:
    normalized = {
        "name": _clean_string(metadata.get("name")),
        "category": _normalize_choice(metadata.get("category"), ALLOWED_CATEGORIES, "Tops"),
        "type": _clean_string(metadata.get("type")),
        "subcategory": _clean_string(metadata.get("subcategory")),
        "color_label": _clean_string(metadata.get("color_label")),
        "pattern": _normalize_choice(metadata.get("pattern"), ALLOWED_PATTERNS, "solid"),
        "season": _normalize_choice(metadata.get("season"), ALLOWED_SEASONS, "All-Season"),
        "occasion": _normalize_string_list(metadata.get("occasion")),
        "style_tags": _normalize_string_list(metadata.get("style_tags")),
        "description": _clean_string(metadata.get("description")),
    }
    normalized["confidence"] = score_confidence(normalized)
    return normalized


def _normalize_category(category: Any, garment_type: str, subcategory: str) -> str:
    cleaned = _clean_string(category)
    normalized = CATEGORY_ALIASES.get(cleaned.lower())
    if normalized:
        return normalized

    for allowed_category in ALLOWED_CATEGORIES:
        if cleaned.lower() == allowed_category.lower():
            return allowed_category

    type_text = f"{garment_type} {subcategory}".lower()
    for keywords, hinted_category in TYPE_CATEGORY_HINTS:
        if any(keyword in type_text for keyword in keywords):
            return hinted_category

    return "Tops"


def _title_words(value: str) -> str:
    special_cases = {
        "t-shirt": "T-Shirt",
        "tshirt": "T-Shirt",
        "low-top": "Low-Top",
        "short-sleeve": "Short-Sleeve",
        "polo shirt": "Polo Shirt",
        "formal shoes": "Formal Shoes",
    }
    normalized = value.strip().lower()
    if normalized in special_cases:
        return special_cases[normalized]
    return " ".join(
        special_cases.get(part.lower(), part.capitalize())
        for part in value.replace("_", " ").split()
    )


def _normalize_llm_type(garment_type: Any, subcategory: Any) -> tuple[str, str]:
    type_value = _clean_string(garment_type)
    subcategory_value = _clean_string(subcategory) or type_value
    combined = f"{type_value} {subcategory_value}".lower()

    if "hoodie" in combined:
        return "Hoodie", "Hoodie"
    if not type_value and subcategory_value:
        type_value = subcategory_value
    if not subcategory_value and type_value:
        subcategory_value = type_value
    return type_value or "Shirt", subcategory_value or type_value or "Shirt"


def normalize_llm_taxonomy(
    category: Any,
    garment_type: Any,
    subcategory: Any = None,
) -> dict[str, str]:
    raw_type = _clean_string(garment_type)
    raw_subcategory = _clean_string(subcategory)
    specific = raw_subcategory or raw_type
    text = f"{raw_type} {raw_subcategory}".lower()
    normalized_category = _normalize_category(category, raw_type, specific)

    known_type = ""
    if "hoodie" in text:
        normalized_category = "Tops"
        known_type = "Hoodie"
        specific = "Hoodie"
    elif normalized_category == "Footwear":
        if "sneaker" in text or "trainer" in text or "low-top" in text or "low top" in text:
            known_type = "Sneakers"
        elif "boot" in text:
            known_type = "Boots"
        elif "loafer" in text:
            known_type = "Loafers"
        elif "sandal" in text:
            known_type = "Sandals"
        elif "formal" in text or "dress shoe" in text:
            known_type = "Formal Shoes"
        else:
            known_type = "Shoes"
    elif normalized_category == "Tops":
        if "t-shirt" in text or "tshirt" in text or "tee" in text:
            known_type = "T-Shirt"
        elif "polo" in text:
            known_type = "Polo Shirt"
        elif "sweater" in text:
            known_type = "Sweater"
        elif "kurta" in text:
            known_type = "Kurta"
        elif "shirt" in text:
            known_type = "Shirt"
        else:
            known_type = "Shirt"
    elif normalized_category == "Dresses":
        known_type = "Saree" if "saree" in text else "Dress"
    elif normalized_category == "Bottoms":
        if "jean" in text or "denim" in text:
            known_type = "Jeans"
        elif "trouser" in text:
            known_type = "Trousers"
        elif "short" in text:
            known_type = "Shorts"
        elif "skirt" in text:
            known_type = "Skirt"
        else:
            known_type = "Pants"
    elif normalized_category == "Outerwear":
        if "blazer" in text:
            known_type = "Blazer"
        elif "coat" in text:
            known_type = "Coat"
        elif "waistcoat" in text:
            known_type = "Waistcoat"
        else:
            known_type = "Jacket"
    elif normalized_category == "Accessories":
        if "bag" in text:
            known_type = "Bag"
        elif "jewel" in text:
            known_type = "Jewelry"
        elif "hat" in text or "cap" in text:
            known_type = "Hat"
        else:
            known_type = "Other"

    if known_type not in KNOWN_TYPES_BY_CATEGORY.get(normalized_category, ()):
        known_type = KNOWN_TYPES_BY_CATEGORY.get(normalized_category, ("Other",))[-1]

    specific_subcategory = _title_words(specific) if specific else known_type
    return {
        "category": normalized_category,
        "type": known_type,
        "subcategory": specific_subcategory or known_type,
    }


def _json_list(values: list[str]) -> str:
    return json.dumps(values)


def _normalize_hex(color_hex: str | None) -> str | None:
    if not color_hex:
        return None
    cleaned = color_hex.strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", cleaned):
        return f"#{cleaned.lstrip('#').upper()}"
    return None


def _color_pattern() -> re.Pattern:
    color_terms = sorted(FASHION_COLOR_PALETTE, key=len, reverse=True)
    return re.compile(
        r"\b(" + "|".join(re.escape(color) for color in color_terms) + r")\b",
        flags=re.IGNORECASE,
    )


def _find_color_mentions(text: str) -> list[tuple[int, str]]:
    mentions: list[tuple[int, str]] = []
    occupied_spans: list[tuple[int, int]] = []
    for match in _color_pattern().finditer(text.lower()):
        start, end = match.span()
        if any(start >= used_start and end <= used_end for used_start, used_end in occupied_spans):
            continue
        color_key = match.group(1).lower()
        label, _ = FASHION_COLOR_PALETTE[color_key]
        mentions.append((start, label))
        occupied_spans.append((start, end))
    mentions.sort(key=lambda item: item[0])
    return mentions


def _has_color_separator(text: str) -> bool:
    normalized_text = text.lower()
    return any(re.search(rf"\b{re.escape(word)}\b", normalized_text) for word in CUE_WORDS)


def _dedupe_color_labels(labels: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for label in labels:
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(label)
    return deduped


def _extract_llm_color_labels(
    color_label: str,
    name: str,
    description: str,
) -> list[str]:
    normalized_color_label = color_label.strip().lower()
    if normalized_color_label in VAGUE_COLORS:
        color_label = ""

    labels = [label for _, label in _find_color_mentions(color_label)]
    if len(labels) > 1 or (len(labels) == 1 and not _has_color_separator(color_label)):
        return _dedupe_color_labels(labels)

    extra_labels = [
        label
        for _, label in _find_color_mentions(f"{name} {description}")
    ]
    return _dedupe_color_labels([*labels, *extra_labels])[:3]


def _hex_for_color_label(label: str) -> str | None:
    return next(
        (
            hex_value
            for palette_label, hex_value in FASHION_COLOR_PALETTE.values()
            if palette_label.lower() == label.lower()
        ),
        None,
    )


def _dominant_colors_from_llm(
    color_label: str,
    name: str,
    description: str,
    fallback_hex: str | None,
    confidence: float,
) -> list[dict]:
    labels = _extract_llm_color_labels(color_label, name, description)
    if labels:
        colors: list[dict] = []
        for index, label in enumerate(labels[:3]):
            role = "primary" if index == 0 else "secondary" if index == 1 else "accent"
            colors.append(
                {
                    "label": label,
                    "hex": _hex_for_color_label(label) or fallback_hex or "#9CA3AF",
                    "role": role,
                    "source": "llm",
                    "percentage": 1.0 if index == 0 and len(labels) == 1 else 0.65 if index == 0 else 0.25 if index == 1 else 0.1,
                    "confidence": confidence,
                }
            )
        return colors

    if fallback_hex:
        return [
            {
                "label": "Custom",
                "hex": fallback_hex,
                "role": "primary",
                "source": "pillow",
                "percentage": 1.0,
                "confidence": max(0.0, round(confidence - 0.2, 2)),
            }
        ]
    return []


def extract_hex_pillow(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise GroqVisionError(f"Image not found: {image_path}")

    try:
        with Image.open(path) as image:
            image = image.convert("RGBA")
            image.thumbnail((320, 320))
            pixels = [
                (red, green, blue)
                for red, green, blue, alpha in image.getdata()
                if alpha > 48
            ]
    except Exception as exc:
        raise GroqVisionError(f"Could not extract image color: {image_path}") from exc

    if not pixels:
        raise GroqVisionError(f"No visible pixels found: {image_path}")

    max_samples = 12000
    if len(pixels) > max_samples:
        step = max(1, len(pixels) // max_samples)
        pixels = pixels[::step]

    red_values = sorted(pixel[0] for pixel in pixels)
    green_values = sorted(pixel[1] for pixel in pixels)
    blue_values = sorted(pixel[2] for pixel in pixels)
    midpoint = len(pixels) // 2
    return f"#{red_values[midpoint]:02X}{green_values[midpoint]:02X}{blue_values[midpoint]:02X}"


def map_llm_metadata_to_wardrobe_fields(
    metadata: dict,
    color_hex: str | None,
) -> dict:
    normalized = _normalize_metadata(metadata)
    taxonomy = normalize_llm_taxonomy(
        metadata.get("category"),
        normalized.get("type"),
        normalized.get("subcategory"),
    )
    hex_value = _normalize_hex(color_hex)
    confidence = float(normalized.get("confidence", 0.0))
    name = _clean_string(normalized.get("name"))
    description = _clean_string(normalized.get("description"))
    dominant_colors = _dominant_colors_from_llm(
        _clean_string(normalized.get("color_label")),
        name,
        description,
        hex_value,
        confidence,
    )
    primary_color = dominant_colors[0]["label"] if dominant_colors else hex_value or ""

    pattern = _clean_string(normalized.get("pattern")).lower()
    pattern_tags = [pattern] if pattern in ALLOWED_PATTERNS and pattern != "solid" else []
    occasion_tags = _normalize_string_list(normalized.get("occasion"))
    style_tags = _normalize_string_list(normalized.get("style_tags"))

    return {
        "name": name or f"{primary_color} {taxonomy['type']}".strip(),
        "category": taxonomy["category"],
        "type": taxonomy["type"],
        "subcategory": taxonomy["subcategory"],
        "color": primary_color,
        "season": _clean_string(normalized.get("season")) or "All-Season",
        "description": description,
        "tags": pattern_tags,
        "pattern_tags": pattern_tags,
        "occasion_tags": occasion_tags,
        "pattern_tags_json": _json_list(pattern_tags),
        "occasion_tags_json": _json_list(occasion_tags),
        "style_tags": style_tags,
        "dominant_colors": dominant_colors,
        "dominant_colors_json": json.dumps(dominant_colors),
        "confidence": confidence,
    }


def score_confidence(metadata: dict) -> float:
    score = 1.0
    color = _clean_string(metadata.get("color_label")).lower()
    description = _clean_string(metadata.get("description"))
    pattern = _clean_string(metadata.get("pattern")).lower()
    name = _clean_string(metadata.get("name"))

    if color in VAGUE_COLORS:
        score -= 0.3
    if "floral" in description.lower() and pattern in {"solid", "colorblock"}:
        score -= 0.4
    if not description:
        score -= 0.2
    if not name or len(name) < 5:
        score -= 0.3

    return round(max(0.0, score), 2)


async def analyze_garment_groq(image_path: str) -> dict:
    _load_backend_env()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise GroqVisionError("GROQ_API_KEY is not configured")

    image_url = _image_data_url(image_path)
    try:
        from groq import AsyncGroq
    except ImportError as exc:
        raise GroqVisionError("groq package is not installed") from exc

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        temperature=0.1,
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": GARMENT_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )
    raw_content = response.choices[0].message.content or ""
    return _normalize_metadata(clean_json_response(raw_content))


# Manual smoke test:
# python -c "import asyncio; from app.services.groq_vision_service import analyze_garment_groq; print(asyncio.run(analyze_garment_groq('app/storage/uploads/example.jpg')))"
