import json
import re
from collections.abc import Mapping
from typing import Any


TOP_RETRIEVAL_LIMIT = 30

CORE_CATEGORIES = {
    "Tops",
    "Bottoms",
    "Dresses",
    "Outerwear",
    "Footwear",
    "Accessories",
}

FORMAL_TYPES = {
    "blazer",
    "coat",
    "shirt",
    "trousers",
    "formal shoes",
    "loafers",
    "waistcoat",
    "dress",
    "saree",
    "kurta",
}

CASUAL_TYPES = {
    "t-shirt",
    "tee",
    "hoodie",
    "jeans",
    "shorts",
    "sneakers",
    "sandals",
}

WARM_LAYER_TYPES = {"hoodie", "sweater", "jacket", "coat", "blazer", "waistcoat"}
HOT_FRIENDLY_TYPES = {"t-shirt", "shirt", "polo shirt", "shorts", "skirt", "sandals"}
COLD_FRIENDLY_TYPES = {"hoodie", "sweater", "jacket", "coat", "boots"}
RAIN_FRIENDLY_TYPES = {"jacket", "coat", "boots"}


def retrieve_relevant_items(wardrobe: list, context: dict, profile: dict) -> list:
    """Return the top wardrobe items for the later LLM recommendation step.

    Retrieval exists so the recommendation prompt is grounded in the user's
    actual closet without sending every garment to the model. WardrobeWhiz uses
    context-stuffing RAG here instead of a vector DB because a single user's
    wardrobe is small, structured, and already rich with metadata. This simple
    pre-filter keeps latency low and improves prompt quality by giving the LLM a
    focused set of relevant items rather than a noisy dump of the full closet.

    This function does not query the database. Callers must pass only the
    current authenticated user's wardrobe items to keep retrieval user-specific.
    """
    context_data = _to_plain_dict(context)
    profile_data = _to_plain_dict(profile)
    scored_items: list[tuple[float, int, dict[str, Any]]] = []

    for input_index, item in enumerate(wardrobe):
        item_data = _normalize_item(item)
        if item_data["category"] not in CORE_CATEGORIES:
            continue

        score, reasons = _score_item(item_data, context_data, profile_data)
        item_data["retrieval_score"] = round(score, 2)
        item_data["retrieval_reasons"] = reasons
        scored_items.append((score, input_index, item_data))

    scored_items.sort(key=lambda scored: (-scored[0], scored[1]))
    return [item for _, _, item in scored_items[:TOP_RETRIEVAL_LIMIT]]


def _score_item(
    item: dict[str, Any],
    context: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    season_score = _score_season(item, context)
    score += season_score
    if season_score:
        reasons.append(f"season/weather match {season_score:+.1f}")

    occasion_score = _score_occasion(item, context, profile)
    score += occasion_score
    if occasion_score:
        reasons.append(f"occasion match {occasion_score:+.1f}")

    dress_code_score = _score_dress_code(item, context)
    score += dress_code_score
    if dress_code_score:
        reasons.append(f"dress code fit {dress_code_score:+.1f}")

    color_score = _score_color_preferences(item, profile)
    score += color_score
    if color_score:
        reasons.append(f"color preference {color_score:+.1f}")

    style_score = _score_style_tags(item, context, profile)
    score += style_score
    if style_score:
        reasons.append(f"style tag match {style_score:+.1f}")

    layering_score = _score_layering(item, context, profile)
    score += layering_score
    if layering_score:
        reasons.append(f"layering fit {layering_score:+.1f}")

    weather_score = _score_weather_suitability(item, context)
    score += weather_score
    if weather_score:
        reasons.append(f"weather suitability {weather_score:+.1f}")

    return score, reasons


def _score_season(item: dict[str, Any], context: dict[str, Any]) -> float:
    seasons = {_normalize_token(value) for value in item["seasons"]}
    temp = _temperature(context)
    weather_text = _context_text(context, "weather")
    score = 0.0

    if temp >= 28 or _contains_any(weather_text, {"hot", "sunny", "humid"}):
        if "summer" in seasons:
            score += 3
        if "winter" in seasons:
            score -= 2
    elif temp <= 15 or _contains_any(weather_text, {"cold", "chilly", "winter"}):
        if "winter" in seasons:
            score += 3
        if "summer" in seasons:
            score -= 1
    elif _contains_any(weather_text, {"rain", "rainy", "storm", "wet"}):
        if seasons & {"fall", "winter", "all-season", "all season"}:
            score += 2
    elif seasons & {"spring", "fall", "all-season", "all season"}:
        score += 1

    if seasons & {"all-season", "all season"}:
        score += 1

    return score


def _score_occasion(
    item: dict[str, Any],
    context: dict[str, Any],
    profile: dict[str, Any],
) -> float:
    context_terms = _tokens(
        " ".join(
            [
                str(context.get("occasion") or ""),
                str(context.get("notes") or ""),
                str(context.get("location") or ""),
            ]
        )
    )
    preferred_occasions = _tokens(" ".join(_list_value(profile, "preferred_occasions")))
    item_terms = _tokens(
        " ".join(
            [
                item["name"],
                item["type"],
                item["description"],
                item["notes"],
                " ".join(item["occasion_tags"]),
                " ".join(item["style_tags"]),
            ]
        )
    )

    matches = len((context_terms | preferred_occasions) & item_terms)
    return min(matches * 2, 6)


def _score_dress_code(item: dict[str, Any], context: dict[str, Any]) -> float:
    dress_code = _context_text(context, "dress_code")
    item_type = _normalize_token(item["type"])
    category = item["category"]
    item_text = _item_search_text(item)
    score = 0.0

    if "formal" in dress_code or "business" in dress_code:
        if category in {"Outerwear", "Tops", "Bottoms", "Footwear", "Dresses"}:
            score += 1
        if item_type in FORMAL_TYPES or _contains_any(item_text, FORMAL_TYPES):
            score += 2
        if item_type in {"t-shirt", "hoodie", "shorts", "sneakers", "sandals"}:
            score -= 3

    if "casual" in dress_code:
        if item_type in CASUAL_TYPES or "casual" in item_text:
            score += 2
        if "smart" in dress_code and item_type in {"blazer", "shirt", "loafers", "trousers"}:
            score += 2

    if "wedding" in dress_code or "wedding" in _context_text(context, "occasion"):
        if item_type in {"blazer", "saree", "dress", "formal shoes", "loafers", "kurta"}:
            score += 2

    return score


def _score_color_preferences(item: dict[str, Any], profile: dict[str, Any]) -> float:
    item_colors = {_normalize_color(value) for value in item["colors"] if value}
    preferred = {
        _normalize_color(value)
        for value in _list_value(profile, "preferred_colors")
        if value
    }
    disliked = {
        _normalize_color(value)
        for value in _list_value(profile, "disliked_colors")
        if value
    }

    score = 0.0
    if item_colors & preferred:
        score += 2
    if item_colors & disliked:
        score -= 5
    return score


def _score_style_tags(
    item: dict[str, Any],
    context: dict[str, Any],
    profile: dict[str, Any],
) -> float:
    preferred_styles = _tokens(" ".join(_list_value(profile, "preferred_styles")))
    profile_text = _tokens(str(profile.get("style_text") or ""))
    mood_terms = _tokens(str(context.get("mood") or ""))
    item_terms = _tokens(_item_search_text(item))

    matches = len((preferred_styles | profile_text | mood_terms) & item_terms)
    return min(matches * 1.5, 4.5)


def _score_layering(
    item: dict[str, Any],
    context: dict[str, Any],
    profile: dict[str, Any],
) -> float:
    layering = _normalize_token(profile.get("layering_preference"))
    item_type = _normalize_token(item["type"])
    category = item["category"]
    temp = _temperature(context)
    weather_text = _context_text(context, "weather")
    is_layer = category == "Outerwear" or item_type in WARM_LAYER_TYPES

    if not is_layer:
        return 0.0

    score = 0.0
    if "like" in layering:
        score += 2
    elif "light" in layering:
        score += 1
    elif "avoid" in layering:
        score -= 3

    if temp >= 28 or _contains_any(weather_text, {"hot", "humid"}):
        score -= 3
    elif temp <= 18 or _contains_any(weather_text, {"cold", "chilly", "rain"}):
        score += 2

    return score


def _score_weather_suitability(item: dict[str, Any], context: dict[str, Any]) -> float:
    item_type = _normalize_token(item["type"])
    category = item["category"]
    temp = _temperature(context)
    weather_text = _context_text(context, "weather")
    score = 0.0

    if temp >= 30 or _contains_any(weather_text, {"hot", "humid"}):
        if item_type in HOT_FRIENDLY_TYPES:
            score += 2
        if item_type in {"hoodie", "sweater", "coat"}:
            score -= 4
        elif category == "Outerwear":
            score -= 2

    if temp <= 15 or _contains_any(weather_text, {"cold", "chilly"}):
        if item_type in COLD_FRIENDLY_TYPES or category == "Outerwear":
            score += 2
        if item_type in {"sandals", "shorts"}:
            score -= 3

    if _contains_any(weather_text, {"rain", "rainy", "storm", "wet"}):
        if item_type in RAIN_FRIENDLY_TYPES:
            score += 2
        if item_type in {"sandals"}:
            score -= 2

    return score


def _normalize_item(item: Any) -> dict[str, Any]:
    item_data = _to_plain_dict(item)
    category = _clean_text(item_data.get("category"))
    subcategory = _clean_text(item_data.get("subcategory") or item_data.get("type"))
    dominant_colors = _decode_json_list(item_data.get("dominant_colors_json"))
    if not dominant_colors:
        dominant_colors = _list_value(item_data, "dominant_colors")

    colors = [_clean_text(item_data.get("color"))]
    colors.extend(_color_values_from_dominant_colors(dominant_colors))

    style_tags = _decode_json_list(item_data.get("pattern_tags_json"))
    style_tags.extend(_list_value(item_data, "tags"))

    occasion_tags = _decode_json_list(item_data.get("occasion_tags_json"))
    season_tags = _decode_json_list(item_data.get("season_tags_json"))
    seasons = [_clean_text(item_data.get("season"))]
    seasons.extend(season_tags)

    return {
        "id": item_data.get("id"),
        "user_id": item_data.get("user_id"),
        "name": _clean_text(item_data.get("name")),
        "category": category,
        "type": subcategory,
        "subcategory": subcategory,
        "color": _clean_text(item_data.get("color")),
        "colors": [value for value in colors if value],
        "dominant_colors": dominant_colors,
        "season": _clean_text(item_data.get("season")),
        "seasons": [value for value in seasons if value],
        "style_tags": _unique_strings(style_tags),
        "occasion_tags": _unique_strings(occasion_tags),
        "description": _clean_text(item_data.get("description")),
        "notes": _clean_text(item_data.get("notes")),
        "image_path": item_data.get("image_path"),
        "thumbnail_path": item_data.get("thumbnail_path"),
        "segmented_image_path": item_data.get("segmented_image_path"),
        "wear_count": item_data.get("wear_count"),
        "last_worn": item_data.get("last_worn"),
    }


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raw = getattr(value, "__dict__", {})
    return {key: item for key, item in raw.items() if not key.startswith("_")}


def _decode_json_list(value: Any) -> list[str] | list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def _list_value(source: Mapping[str, Any], key: str) -> list[str]:
    value = source.get(key)
    if value is None and f"{key}_json" in source:
        value = source.get(f"{key}_json")
    decoded = _decode_json_list(value)
    if decoded:
        return [str(item) for item in decoded if not isinstance(item, dict)]
    if isinstance(value, tuple | set):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _color_values_from_dominant_colors(colors: list[Any]) -> list[str]:
    values: list[str] = []
    for color in colors:
        if not isinstance(color, Mapping):
            continue
        for key in ("hex", "label", "family"):
            value = color.get(key)
            if value:
                values.append(str(value))
    return values


def _unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            continue
        text = _clean_text(value)
        key = text.lower()
        if text and key not in seen:
            unique.append(text)
            seen.add(key)
    return unique


def _item_search_text(item: dict[str, Any]) -> str:
    return " ".join(
        [
            item["name"],
            item["category"],
            item["type"],
            item["description"],
            item["notes"],
            " ".join(item["style_tags"]),
            " ".join(item["occasion_tags"]),
        ]
    ).lower()


def _context_text(context: dict[str, Any], key: str) -> str:
    return str(context.get(key) or "").lower()


def _temperature(context: dict[str, Any]) -> float:
    try:
        return float(context.get("temperature_c", 20) or 20)
    except (TypeError, ValueError):
        return 20.0


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in {"the", "and", "for", "with", "any"}
    }


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_token(value: Any) -> str:
    return _clean_text(value).lower()


def _normalize_color(value: Any) -> str:
    return _clean_text(value).lower().replace(" ", "")
