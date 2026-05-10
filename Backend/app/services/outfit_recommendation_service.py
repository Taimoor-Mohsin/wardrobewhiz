import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.services.outfit_retrieval_service import retrieve_relevant_items

GROQ_OUTFIT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
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
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise OutfitRecommendationError("Groq response JSON could not be parsed") from exc

    if not isinstance(parsed, dict):
        raise OutfitRecommendationError("Groq response JSON was not an object")
    return parsed


async def generate_outfit_recommendation(
    wardrobe: list,
    context: dict,
    profile: dict,
) -> dict:
    """Generate a recommendation from current-user wardrobe data.

    The caller is responsible for fetching only the authenticated user's
    wardrobe and profile. This service performs no global wardrobe access.
    """
    context_data = _to_plain_dict(context)
    profile_data = _to_plain_dict(profile)
    retrieved_items = retrieve_relevant_items(wardrobe, context_data, profile_data)
    if not retrieved_items:
        return _empty_fallback_response("No wardrobe items were available for recommendation.")

    try:
        raw_recommendation = await _call_groq(build_outfit_prompt(context_data, profile_data, retrieved_items))
        recommendation = _normalize_recommendation(clean_json_response(raw_recommendation))
    except Exception:
        return _fallback_recommendation(retrieved_items, context_data, profile_data)

    validation = validate_outfit_selection(
        recommendation.get("selected_item_ids", []),
        retrieved_items,
    )
    if not validation["is_valid"]:
        fallback = _fallback_recommendation(retrieved_items, context_data, profile_data)
        if fallback["selected_item_ids"]:
            recommendation["selected_item_ids"] = fallback["selected_item_ids"]
            recommendation["outfit_description"] = (
                recommendation["outfit_description"]
                or fallback["outfit_description"]
            )
        else:
            return fallback
    else:
        recommendation["selected_item_ids"] = validation["selected_item_ids"]

    if not recommendation.get("selected_item_ids"):
        return _fallback_recommendation(retrieved_items, context_data, profile_data)
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
    selected_items = _fallback_select_items(items)
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


def _fallback_select_items(items: list) -> list[dict]:
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
    return selected


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
