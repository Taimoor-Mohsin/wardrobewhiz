import colorsys
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.services.outfit_retrieval_service import retrieve_relevant_items

GROQ_OUTFIT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_HOT_REMOVE_WORDS = frozenset({"winter", "heavy", "wool", "knit", "fleece", "puffer", "coat", "jacket"})
_COLD_REMOVE_WORDS = frozenset({"sleeveless", "tank", "swimwear"})

REQUIRED_RESPONSE_FIELDS = {
    "outfit_name",
    "selected_item_ids",
    "outfit_description",
    "styling_tips",
    "color_story",
    "why_it_fits_you",
}


class OutfitRecommendationError(RuntimeError):
    pass


def build_outfit_prompt(context: dict, profile: dict, items: list) -> str:
    """Build the context-stuffing RAG prompt for outfit selection.

    WardrobeWhiz uses context-stuffing RAG here because a user's wardrobe is
    small enough to inject directly after deterministic retrieval. The retrieval
    service filters the closet down to the strongest candidates first, which
    keeps Groq latency low and makes the prompt sharper than sending every item.
    """
    context_data = _to_plain_dict(context)
    profile_data = _to_plain_dict(profile)
    item_lines = "\n".join(_format_item_for_prompt(item) for item in items)

    return f"""
You are a personal fashion stylist for WardrobeWhiz.
Your job is to select a complete outfit from the user's wardrobe for a specific occasion.

USER STYLE PROFILE:
- Usually dresses for: {_json_text(_list_value(profile_data, "usual_contexts"))}
- Everyday style: {_text(profile_data.get("style_text"))}
- Formality preference: {_text(profile_data.get("formality_level"))}/5
- Comfort vs style: {_text(profile_data.get("comfort_style_level"))}/5
- Eastern/Western preference: {_text(profile_data.get("eastern_western_preference"))}
- Modesty preference: {_text(profile_data.get("modesty_preference"))}
- Aesthetics: {_json_text(_list_value(profile_data, "preferred_styles"))}
- Fit preference: {_text(profile_data.get("fit_preference"))}
- Layering preference: {_text(profile_data.get("layering_preference"))}
- Accessories preference: {_text(profile_data.get("accessories_preference"))}
- Avoids: {_text(profile_data.get("clothing_avoid_text"))}
- Preferred colors: {_json_text(_list_value(profile_data, "preferred_colors"))}
- Disliked colors: {_json_text(_list_value(profile_data, "disliked_colors"))}

OUTFIT CONTEXT:
- Occasion: {_text(context_data.get("occasion"))}
- Location: {_text(context_data.get("location"))}
- Weather: {_text(context_data.get("weather"))}
- Temperature: {_text(context_data.get("temperature_c"))} C
- Mood/Style: {_text(context_data.get("mood"))}
- Dress Code: {_text(context_data.get("dress_code"))}
- Notes: {_text(context_data.get("notes"))}

AVAILABLE WARDROBE ITEMS:
{item_lines}

TASK:
Select a complete, cohesive outfit from ONLY the items listed above.
A complete outfit must contain either:
1. one top, one bottom, and one footwear item
2. one dress and one footwear item
Outerwear and accessories are optional. Include them only when useful for the weather, occasion, profile, or dress code.
Do not invent item IDs. Do not use items outside AVAILABLE WARDROBE ITEMS.
Avoid duplicate item IDs.
Avoid structurally invalid outfits, such as two bottoms, no footwear, or a dress plus a separate bottom.
Respect disliked colors strictly when enough alternatives exist.
Prioritize preferred colors, aesthetics, dress code, weather, and mood.

Return ONLY a valid JSON object. No markdown. No extra text.

{{
  "outfit_name": "short catchy outfit name e.g. Sharp Monday Formal",
  "selected_item_ids": [12, 7, 23, 31],
  "outfit_description": "2-3 sentence overview of the full outfit and why it works for this occasion",
  "styling_tips": [
    "Tuck in the shirt to accentuate the slim fit",
    "Roll the sleeves once for a smart casual look",
    "The navy blazer ties the color palette together"
  ],
  "color_story": "Brief explanation of why these colors work together",
  "why_it_fits_you": "Personalized note referencing the user's profile"
}}
""".strip()


def clean_json_response(raw: str) -> dict:
    """Parse Groq JSON with safe cleanup for common wrapper text."""
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise OutfitRecommendationError("Groq response did not contain a JSON object")
        try:
            parsed = json.loads(text[start: end + 1])
        except json.JSONDecodeError as exc:
            raise OutfitRecommendationError("Groq response JSON could not be parsed") from exc

    if not isinstance(parsed, dict):
        raise OutfitRecommendationError("Groq response JSON was not an object")
    return parsed


async def generate_outfit_recommendation(
    wardrobe: list,
    context: dict,
    profile: dict,
    feedback_history: list | None = None,
    recent_item_ids: list | None = None,
) -> dict:
    """Generate a recommendation from current-user wardrobe data.

    The caller is responsible for fetching only the authenticated user's
    wardrobe and profile. This service performs no global wardrobe access.
    """
    context_data = _to_plain_dict(context)
    profile_data = _to_plain_dict(profile)
    retrieved_items = retrieve_relevant_items(
        wardrobe,
        context_data,
        profile_data,
        feedback_history=feedback_history or [],
        recent_item_ids=recent_item_ids or [],
    )
    if not retrieved_items:
        return _empty_fallback_response("No wardrobe items were available for recommendation.")

    used_fallback = False
    validation_passed = False
    weather_structure_preserved = True

    try:
        raw_recommendation = await _call_groq(build_outfit_prompt(context_data, profile_data, retrieved_items))
        recommendation = _normalize_recommendation(clean_json_response(raw_recommendation))
    except Exception:
        recommendation = _fallback_recommendation(retrieved_items, context_data, profile_data)
        used_fallback = True

    if not used_fallback:
        validation = validate_outfit_selection(
            recommendation.get("selected_item_ids", []),
            retrieved_items,
        )
        if not validation["is_valid"]:
            fallback = _fallback_recommendation(retrieved_items, context_data, profile_data)
            if fallback["selected_item_ids"]:
                recommendation["selected_item_ids"] = fallback["selected_item_ids"]
                recommendation["outfit_description"] = (
                    recommendation["outfit_description"] or fallback["outfit_description"]
                )
            else:
                recommendation = fallback
                used_fallback = True
        else:
            recommendation["selected_item_ids"] = validation["selected_item_ids"]
            validation_passed = True

    weather_result = _apply_weather_filter(
        recommendation["selected_item_ids"],
        retrieved_items,
        context_data,
    )
    recommendation["selected_item_ids"] = weather_result["filtered_ids"]
    weather_structure_preserved = weather_result["structure_preserved"]

    if not recommendation.get("selected_item_ids"):
        recommendation = _fallback_recommendation(retrieved_items, context_data, profile_data)
        used_fallback = True
        weather_structure_preserved = False

    harmony = _score_color_harmony(recommendation["selected_item_ids"], retrieved_items)
    recommendation["harmony_score"] = harmony["harmony_score"]
    recommendation["harmony_type"] = harmony["harmony_type"]
    existing_color_story = recommendation.get("color_story") or ""
    if existing_color_story and harmony["harmony_note"]:
        recommendation["color_story"] = f"{existing_color_story} {harmony['harmony_note']}"
    elif harmony["harmony_note"]:
        recommendation["color_story"] = harmony["harmony_note"]

    style_cons = _check_style_consistency(recommendation["selected_item_ids"], retrieved_items)
    recommendation["style_consistency"] = style_cons
    if style_cons["consistent"]:
        existing_why = recommendation.get("why_it_fits_you") or ""
        recommendation["why_it_fits_you"] = (
            f"{existing_why} {style_cons['note']}" if existing_why else style_cons["note"]
        )

    confidence = 60
    if validation_passed and not used_fallback:
        confidence += 10
    if harmony["harmony_score"] > 0:
        confidence += 10
    if style_cons["consistent"]:
        confidence += 10
    if weather_structure_preserved:
        confidence += 10
    if used_fallback:
        confidence -= 20
    recommendation["confidence_score"] = max(0, min(100, confidence))

    return _fill_missing_recommendation_fields(recommendation, context_data, profile_data)


def validate_outfit_selection(selected_item_ids: list, items: list) -> dict:
    """Validate selected IDs and basic outfit structure.

    Valid structures are top + bottom + footwear or dress + footwear. Duplicate
    and unknown IDs are rejected because the LLM must stay grounded in retrieved
    wardrobe items.
    """
    item_by_id = {_item_id(item): _to_plain_dict(item) for item in items if _item_id(item) is not None}
    errors: list[str] = []
    cleaned_ids: list[Any] = []
    seen: set[Any] = set()

    for raw_id in selected_item_ids or []:
        item_id = _coerce_item_id(raw_id)
        if item_id in seen:
            errors.append(f"Duplicate item ID: {item_id}")
            continue
        if item_id not in item_by_id:
            errors.append(f"Unknown item ID: {item_id}")
            continue
        cleaned_ids.append(item_id)
        seen.add(item_id)

    selected_items = [item_by_id[item_id] for item_id in cleaned_ids]
    categories = {_category(item) for item in selected_items}
    has_top = "Tops" in categories
    has_bottom = "Bottoms" in categories
    has_dress = "Dresses" in categories
    has_footwear = "Footwear" in categories

    if not cleaned_ids:
        errors.append("No selected item IDs")
    if len([item for item in selected_items if _category(item) == "Bottoms"]) > 1:
        errors.append("Outfit contains more than one bottom")
    if has_dress and has_bottom:
        errors.append("Outfit mixes a dress with a separate bottom")
    if has_dress:
        if not has_footwear:
            errors.append("Dress outfit is missing footwear")
    elif not (has_top and has_bottom and has_footwear):
        errors.append("Outfit must contain top + bottom + footwear or dress + footwear")

    return {
        "is_valid": not errors,
        "selected_item_ids": cleaned_ids,
        "errors": errors,
    }


async def _call_groq(prompt: str) -> str:
    _load_backend_env()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise OutfitRecommendationError("GROQ_API_KEY is not configured")

    try:
        from groq import AsyncGroq
    except ImportError as exc:
        raise OutfitRecommendationError("groq package is not installed") from exc

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model=GROQ_OUTFIT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


def _fallback_recommendation(items: list, context: dict, profile: dict) -> dict:
    selected_items = _fallback_select_items(items, context)
    selected_ids = [_item_id(item) for item in selected_items if _item_id(item) is not None]
    occasion = _text(context.get("occasion")) or "your plans"
    dress_code = _text(context.get("dress_code")) or "the requested dress code"
    styles = _list_value(profile, "preferred_styles")

    return {
        "outfit_name": "WardrobeWhiz Fallback Look",
        "selected_item_ids": selected_ids,
        "outfit_description": (
            f"This deterministic look uses the highest-ranked valid pieces for {occasion}. "
            f"It is grounded in your wardrobe and keeps the structure suitable for {dress_code}."
        ),
        "styling_tips": [
            "Keep the strongest-scored pieces as the base of the outfit.",
            "Adjust optional layers or accessories based on comfort and weather.",
        ],
        "color_story": "The fallback favors retrieved items that matched your profile colors and context.",
        "why_it_fits_you": (
            f"It reflects your saved preferences"
            f"{' such as ' + ', '.join(styles[:3]) if styles else ''} while avoiding invalid outfit structure."
        ),
    }


def _fallback_select_items(items: list, context: dict | None = None) -> list[dict]:
    normalized_items = [_to_plain_dict(item) for item in items]
    tops = _items_by_category(normalized_items, "Tops")
    bottoms = _items_by_category(normalized_items, "Bottoms")
    dresses = _items_by_category(normalized_items, "Dresses")
    footwear = _items_by_category(normalized_items, "Footwear")
    outerwear = _items_by_category(normalized_items, "Outerwear")
    accessories = _items_by_category(normalized_items, "Accessories")

    selected: list[dict] = []
    if dresses and footwear:
        selected.extend([dresses[0], footwear[0]])
    elif tops and bottoms and footwear:
        selected.extend([tops[0], bottoms[0], footwear[0]])
    else:
        return []

    if outerwear and _score(outerwear[0]) > 0:
        selected.append(outerwear[0])
    if accessories and _score(accessories[0]) > 0:
        selected.append(accessories[0])

    if context:
        selected_ids = [_item_id(item) for item in selected if _item_id(item) is not None]
        weather_result = _apply_weather_filter(selected_ids, normalized_items, context)
        if weather_result["structure_preserved"] and weather_result["removed_ids"]:
            kept = set(weather_result["filtered_ids"])
            selected = [item for item in selected if _item_id(item) in kept]

    return selected


def _apply_weather_filter(selected_ids: list, items: list, context: dict) -> dict:
    """Remove weather-inappropriate items post-LLM, falling back if structure breaks.

    Returns a dict with:
      filtered_ids       — IDs to use (equals selected_ids when removal was unsafe)
      structure_preserved — True when the filter kept outfit structure intact
      removed_ids        — IDs flagged for removal (whether or not removal was applied)
    """
    temp = _parse_temperature(context)
    is_hot = temp is not None and temp >= 28
    is_cold = temp is not None and temp <= 12

    if not is_hot and not is_cold:
        return {"filtered_ids": list(selected_ids), "structure_preserved": True, "removed_ids": []}

    item_by_id = {_item_id(item): _to_plain_dict(item) for item in items if _item_id(item) is not None}

    kept_ids: list = []
    removed_ids: list = []

    for item_id in selected_ids:
        item = item_by_id.get(item_id)
        if item is None:
            kept_ids.append(item_id)
            continue
        if is_hot and _is_hot_inappropriate(item):
            removed_ids.append(item_id)
        elif is_cold and _is_cold_inappropriate(item):
            removed_ids.append(item_id)
        else:
            kept_ids.append(item_id)

    if not removed_ids:
        return {"filtered_ids": list(selected_ids), "structure_preserved": True, "removed_ids": []}

    validation = validate_outfit_selection(kept_ids, items)
    if validation["is_valid"]:
        return {
            "filtered_ids": validation["selected_item_ids"],
            "structure_preserved": True,
            "removed_ids": removed_ids,
        }

    return {"filtered_ids": list(selected_ids), "structure_preserved": False, "removed_ids": removed_ids}


def _is_hot_inappropriate(item: dict) -> bool:
    if _category(item) == "Outerwear":
        return True
    text = " ".join([
        " ".join(_flat_tags(item.get("style_tags"))),
        " ".join(_flat_tags(item.get("occasion_tags"))),
        _text(item.get("season")),
        " ".join(_flat_tags(item.get("seasons"))),
    ]).lower()
    return any(word in text for word in _HOT_REMOVE_WORDS)


def _is_cold_inappropriate(item: dict) -> bool:
    seasons = [s.lower().strip() for s in (_flat_tags(item.get("seasons")) or [_text(item.get("season"))]) if s]
    if seasons and all(s == "summer" for s in seasons):
        return True
    style_text = " ".join(_flat_tags(item.get("style_tags"))).lower()
    return any(word in style_text for word in _COLD_REMOVE_WORDS)


def _flat_tags(value: Any) -> list[str]:
    """Coerce a tags field (list, JSON string, or scalar) to a flat list of strings."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return [str(v) for v in decoded if v]
        except json.JSONDecodeError:
            pass
        return [value] if value.strip() else []
    return [str(value)]


def _check_style_consistency(selected_ids: list, items: list) -> dict:
    item_by_id = {_item_id(item): _to_plain_dict(item) for item in items if _item_id(item) is not None}
    tag_counts: dict[str, int] = {}

    for item_id in selected_ids:
        item = item_by_id.get(item_id)
        if item is None:
            continue
        raw = item.get("style_tags") or item.get("tags") or []
        tags: list[str] = []
        if isinstance(raw, list):
            tags = [str(t).lower().strip() for t in raw if t]
        elif isinstance(raw, str):
            try:
                decoded = json.loads(raw)
                tags = [str(t).lower().strip() for t in decoded if t] if isinstance(decoded, list) else []
            except json.JSONDecodeError:
                tags = [raw.lower().strip()] if raw.strip() else []
        for tag in set(tags):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    shared = [tag for tag, count in tag_counts.items() if count >= 2]
    if shared:
        return {
            "consistent": True,
            "shared_tags": shared,
            "note": f"Cohesive around: {', '.join(shared[:3])}.",
        }
    return {"consistent": False, "shared_tags": [], "note": "Mixed styles — bold but intentional."}


def _score_color_harmony(selected_ids: list, items: list) -> dict:
    item_by_id = {_item_id(item): _to_plain_dict(item) for item in items if _item_id(item) is not None}
    hues: list[float] = []
    neutral_count = 0

    for item_id in selected_ids:
        item = item_by_id.get(item_id)
        if item is None:
            continue
        hsv = _primary_hsv(item)
        if hsv is None:
            continue
        h, s, _ = hsv
        if s < 0.15:
            neutral_count += 1
        else:
            hues.append(h * 360.0)

    if not hues:
        return {
            "harmony_score": 0.0,
            "harmony_type": "Neutral-dominant",
            "harmony_note": "The palette is built on neutrals — a versatile, easy-to-wear combination.",
        }

    spread = _circular_spread(hues)
    if spread <= 30:
        score, harmony_type = 3.0, "Monochromatic"
    elif spread <= 60:
        score, harmony_type = 2.0, "Analogous"
    elif len(hues) == 2 and _is_complementary(hues[0], hues[1]):
        score, harmony_type = 2.0, "Complementary"
    elif len(hues) >= 3 and _all_clashing(hues):
        score, harmony_type = -2.0, "Clashing"
    else:
        score, harmony_type = 0.0, "Mixed"

    _HARMONY_NOTES = {
        "Monochromatic": "The palette stays within a single hue family for a sleek, tonal effect.",
        "Analogous": "Adjacent hues create a cohesive, harmonious palette that reads naturally together.",
        "Complementary": "Opposite hues on the colour wheel generate a bold, high-contrast pairing.",
        "Clashing": "The mix of unrelated hues may compete for attention — consider swapping one item to unify the palette.",
        "Mixed": "The colours are varied; a neutral layer can help tie the outfit together.",
    }
    note = _HARMONY_NOTES[harmony_type]
    if neutral_count and harmony_type != "Neutral-dominant":
        note += f" {neutral_count} neutral piece{'s' if neutral_count > 1 else ''} help{'s' if neutral_count == 1 else ''} anchor the look."

    return {"harmony_score": score, "harmony_type": harmony_type, "harmony_note": note}


def _primary_hsv(item: dict) -> tuple[float, float, float] | None:
    dominant = item.get("dominant_colors")
    if not dominant and item.get("dominant_colors_json"):
        try:
            dominant = json.loads(item["dominant_colors_json"])
        except (json.JSONDecodeError, TypeError):
            dominant = None
    if isinstance(dominant, list) and dominant:
        first = dominant[0]
        if isinstance(first, dict) and first.get("hex"):
            result = _hex_to_hsv(str(first["hex"]))
            if result is not None:
                return result
    for color in (item.get("colors") or []):
        if isinstance(color, str) and color.startswith("#"):
            result = _hex_to_hsv(color)
            if result is not None:
                return result
    color = item.get("color", "")
    if color and str(color).startswith("#"):
        return _hex_to_hsv(str(color))
    return None


def _hex_to_hsv(hex_color: str) -> tuple[float, float, float] | None:
    cleaned = re.sub(r"[^0-9a-fA-F]", "", hex_color)
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    if len(cleaned) != 6:
        return None
    try:
        r, g, b = int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16)
    except ValueError:
        return None
    return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)


def _circular_spread(hues: list[float]) -> float:
    if len(hues) <= 1:
        return 0.0
    sorted_hues = sorted(hues)
    gaps = [sorted_hues[i + 1] - sorted_hues[i] for i in range(len(sorted_hues) - 1)]
    gaps.append(360.0 - sorted_hues[-1] + sorted_hues[0])
    return 360.0 - max(gaps)


def _is_complementary(h1: float, h2: float) -> bool:
    diff = abs(h1 - h2)
    if diff > 180:
        diff = 360.0 - diff
    return abs(diff - 180.0) <= 30.0


def _all_clashing(hues: list[float]) -> bool:
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            diff = abs(hues[i] - hues[j])
            if diff > 180:
                diff = 360.0 - diff
            if diff <= 60:
                return False
    return True


def _parse_temperature(context: dict) -> float | None:
    raw = context.get("temperature_c")
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _normalize_recommendation(recommendation: dict) -> dict:
    missing = REQUIRED_RESPONSE_FIELDS - set(recommendation)
    if missing:
        raise OutfitRecommendationError(f"Groq response missing fields: {sorted(missing)}")

    selected_ids = recommendation.get("selected_item_ids")
    if not isinstance(selected_ids, list) or not selected_ids:
        raise OutfitRecommendationError("Groq response did not include selected_item_ids")

    styling_tips = recommendation.get("styling_tips")
    if not isinstance(styling_tips, list):
        recommendation["styling_tips"] = [_text(styling_tips)] if styling_tips else []

    for key in REQUIRED_RESPONSE_FIELDS - {"selected_item_ids", "styling_tips"}:
        recommendation[key] = _text(recommendation.get(key))
    recommendation["selected_item_ids"] = [_coerce_item_id(item_id) for item_id in selected_ids]
    return recommendation


def _fill_missing_recommendation_fields(
    recommendation: dict,
    context: dict,
    profile: dict,
) -> dict:
    fallback = _fallback_recommendation([], context, profile)
    for key in REQUIRED_RESPONSE_FIELDS:
        if not recommendation.get(key):
            recommendation[key] = fallback[key]
    if not isinstance(recommendation.get("styling_tips"), list):
        recommendation["styling_tips"] = fallback["styling_tips"]
    return recommendation


def _empty_fallback_response(reason: str) -> dict:
    return {
        "outfit_name": "No Outfit Available",
        "selected_item_ids": [],
        "outfit_description": reason,
        "styling_tips": [],
        "color_story": "",
        "why_it_fits_you": "Add more wardrobe items to generate a complete recommendation.",
    }


def _format_item_for_prompt(item: Any) -> str:
    item_data = _to_plain_dict(item)
    colors = item_data.get("colors") or [item_data.get("color")]
    return (
        f"ID:{_item_id(item_data)} | "
        f"{_text(item_data.get('name')) or 'Wardrobe item'} | "
        f"{_category(item_data)} | "
        f"Type:{_text(item_data.get('type') or item_data.get('subcategory'))} | "
        f"Color:{_json_text(colors)} | "
        f"Season:{_json_text(item_data.get('seasons') or [item_data.get('season')])} | "
        f"Occasion:{_json_text(item_data.get('occasion_tags') or [])} | "
        f"Tags:{_json_text(item_data.get('style_tags') or item_data.get('tags') or [])} | "
        f"Score:{_text(item_data.get('retrieval_score'))}"
    )


def _load_backend_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception:
        pass


def _items_by_category(items: list[dict], category: str) -> list[dict]:
    return [item for item in items if _category(item) == category]


def _category(item: Mapping[str, Any]) -> str:
    return _text(item.get("category"))


def _item_id(item: Any) -> Any:
    item_data = _to_plain_dict(item)
    return _coerce_item_id(item_data.get("id"))


def _coerce_item_id(item_id: Any) -> Any:
    if isinstance(item_id, str) and item_id.isdigit():
        return int(item_id)
    return item_id


def _score(item: Mapping[str, Any]) -> float:
    try:
        return float(item.get("retrieval_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raw = getattr(value, "__dict__", {})
    return {key: item for key, item in raw.items() if not key.startswith("_")}


def _list_value(source: Mapping[str, Any], key: str) -> list[str]:
    value = source.get(key)
    if value is None and f"{key}_json" in source:
        value = source.get(f"{key}_json")
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip():
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(decoded, list):
            return [str(item) for item in decoded]
        return [value]
    return []


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def _text(value: Any) -> str:
    return str(value or "").strip()
