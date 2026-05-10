import logging
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from app.core.config import settings
from PIL import Image

logger = logging.getLogger(__name__)

FASHION_COLORS: dict[str, str] = {
    "black": "#181818",
    "charcoal": "#3A3A3A",
    "white": "#F5F5F5",
    "cream": "#F4ECDD",
    "grey": "#808080",
    "navy": "#283856",
    "blue": "#4273BE",
    "light blue": "#A8C6E6",
    "denim blue": "#5C7094",
    "red": "#BA2D34",
    "maroon": "#742636",
    "pink": "#D68AA2",
    "green": "#4D7952",
    "olive": "#6F743F",
    "mint": "#A6D1B4",
    "yellow": "#E4C658",
    "mustard": "#B69136",
    "orange": "#D17D44",
    "beige": "#D2BE9E",
    "brown": "#6E4F3A",
    "dark brown": "#3F2B1F",
    "tan": "#B2916A",
    "khaki": "#A39A6D",
    "purple": "#805E90",
}


@dataclass
class VisionResult:
    segmented_image_path: str | None
    dominant_color: dict[str, str] | None
    dominant_colors: list[dict[str, str | float]]
    inferred_season: str | None


def hex_to_rgb(hex_value: str) -> np.ndarray:
    value = hex_value.lstrip("#")
    return np.array([int(value[index : index + 2], 16) for index in (0, 2, 4)])


PALETTE_RGB = {
    label: hex_to_rgb(hex_value) for label, hex_value in FASHION_COLORS.items()
}


def remove_background(original_path: str) -> str | None:
    original = Path(original_path)
    segmented_dir = Path(settings.upload_dir).parent / "segmented"
    segmented_dir.mkdir(parents=True, exist_ok=True)
    segmented_path = segmented_dir / f"{original.stem}_segmented.png"

    try:
        model_dir = Path(settings.upload_dir).parent / "rembg"
        model_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("U2NET_HOME", str(model_dir))

        from rembg import remove

        segmented_bytes = remove(original.read_bytes())
        segmented_path.write_bytes(segmented_bytes)
        return str(segmented_path)
    except Exception as exc:  # pragma: no cover - depends on optional model/runtime
        logger.warning("Background removal failed for %s: %s", original_path, exc)
        return None


def extract_dominant_color(image_path: str) -> dict[str, str] | None:
    colors = extract_dominant_colors(image_path, max_colors=1)
    if not colors:
        return None
    color = colors[0]
    return {"label": str(color["label"]), "hex": str(color["hex"])}


def rgb_to_hsv(rgb_pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rgb = rgb_pixels.astype(float) / 255.0
    red = rgb[:, 0]
    green = rgb[:, 1]
    blue = rgb[:, 2]

    max_channel = np.max(rgb, axis=1)
    min_channel = np.min(rgb, axis=1)
    delta = max_channel - min_channel

    hue = np.zeros_like(max_channel)
    red_mask = (max_channel == red) & (delta != 0)
    green_mask = (max_channel == green) & (delta != 0)
    blue_mask = (max_channel == blue) & (delta != 0)
    hue[red_mask] = ((green[red_mask] - blue[red_mask]) / delta[red_mask]) % 6
    hue[green_mask] = ((blue[green_mask] - red[green_mask]) / delta[green_mask]) + 2
    hue[blue_mask] = ((red[blue_mask] - green[blue_mask]) / delta[blue_mask]) + 4
    hue = hue * 60

    saturation = np.where(max_channel == 0, 0, delta / max_channel)
    value = max_channel
    return hue, saturation, value


def label_visible_pixels(rgb_pixels: np.ndarray) -> np.ndarray:
    hue, saturation, value = rgb_to_hsv(rgb_pixels)
    labels = np.full(len(rgb_pixels), "grey", dtype=object)

    low_saturation = saturation < 0.18
    warm_neutral = (hue >= 32) & (hue <= 72)

    labels[(value < 0.16) & (saturation < 0.45)] = "black"
    labels[(value >= 0.16) & (value < 0.34) & (saturation < 0.25)] = "charcoal"
    labels[low_saturation & (value >= 0.34) & (value < 0.86)] = "grey"
    labels[(value >= 0.86) & (saturation < 0.12)] = "white"
    labels[(value >= 0.74) & (saturation >= 0.10) & (saturation < 0.32) & warm_neutral] = "cream"

    muted_green_neutral = (saturation < 0.24) & (hue >= 82) & (hue < 170) & (value < 0.62)
    labels[muted_green_neutral & (value < 0.36)] = "charcoal"
    labels[muted_green_neutral & (value >= 0.36)] = "grey"

    chromatic = saturation >= 0.20

    red_family = chromatic & ((hue >= 345) | (hue < 12))
    labels[red_family & (value < 0.50)] = "maroon"
    labels[red_family & (value >= 0.50)] = "red"

    orange_family = chromatic & (hue >= 12) & (hue < 35)
    labels[orange_family & (value < 0.45)] = "dark brown"
    labels[orange_family & (value >= 0.45) & (value < 0.68) & (saturation < 0.60)] = "brown"
    labels[orange_family & (value >= 0.68) & (saturation < 0.45)] = "tan"
    labels[orange_family & (value >= 0.68) & (saturation >= 0.45)] = "orange"

    yellow_brown_family = chromatic & (hue >= 35) & (hue < 65)
    labels[yellow_brown_family & (value < 0.38)] = "dark brown"
    labels[yellow_brown_family & (value >= 0.38) & (value < 0.58) & (saturation >= 0.28)] = "brown"
    labels[yellow_brown_family & (value >= 0.58) & (value < 0.78) & (saturation < 0.38)] = "beige"
    labels[yellow_brown_family & (value >= 0.58) & (value < 0.82) & (saturation >= 0.38)] = "mustard"
    labels[yellow_brown_family & (value >= 0.82) & (saturation < 0.35)] = "cream"
    labels[yellow_brown_family & (value >= 0.82) & (saturation >= 0.35)] = "yellow"

    olive_family = chromatic & (hue >= 65) & (hue < 95)
    labels[olive_family & (saturation < 0.36) & (value >= 0.42)] = "khaki"
    labels[olive_family & ~((saturation < 0.36) & (value >= 0.42))] = "olive"

    green_family = chromatic & ~muted_green_neutral & (hue >= 95) & (hue < 155)
    labels[green_family & (value < 0.42)] = "olive"
    labels[green_family & (value >= 0.42)] = "green"

    mint_family = chromatic & ~muted_green_neutral & (hue >= 155) & (hue < 185)
    labels[mint_family & (value >= 0.62) & (saturation < 0.46)] = "mint"
    labels[mint_family & ~((value >= 0.62) & (saturation < 0.46))] = "green"

    blue_family = chromatic & (hue >= 185) & (hue < 250)
    labels[blue_family & (value < 0.34)] = "navy"
    labels[blue_family & (value >= 0.34) & (value < 0.68) & (saturation < 0.58)] = "denim blue"
    labels[blue_family & (value >= 0.68) & (saturation < 0.52)] = "light blue"
    labels[blue_family & (value >= 0.34) & ~((value < 0.68) & (saturation < 0.58)) & ~((value >= 0.68) & (saturation < 0.52))] = "blue"

    purple_family = chromatic & (hue >= 250) & (hue < 315)
    labels[purple_family] = "purple"

    pink_family = chromatic & (hue >= 315) & (hue < 345)
    labels[pink_family & (value >= 0.55)] = "pink"
    labels[pink_family & (value < 0.55)] = "maroon"

    return labels


def color_confidence(percentage: float) -> float:
    return round(min(0.95, max(0.45, 0.55 + percentage)), 2)


def extract_dominant_colors(image_path: str, max_colors: int = 4) -> list[dict[str, str | float]]:
    try:
        with Image.open(image_path) as image:
            image = image.convert("RGBA")
            image.thumbnail((360, 360))
            pixels = np.array(image)
    except Exception as exc:
        logger.warning("Dominant color extraction failed for %s: %s", image_path, exc)
        return []

    alpha = pixels[:, :, 3]
    rgb_pixels = pixels[:, :, :3]
    visible_pixels = rgb_pixels[alpha > 48]

    if visible_pixels.size == 0:
        visible_pixels = rgb_pixels.reshape(-1, 3)

    if visible_pixels.size == 0:
        return []

    if len(visible_pixels) > 12000:
        step = max(len(visible_pixels) // 12000, 1)
        visible_pixels = visible_pixels[::step]

    labels = label_visible_pixels(visible_pixels)
    unique_labels, counts = np.unique(labels, return_counts=True)
    total_count = int(counts.sum())
    if total_count == 0:
        return []

    sorted_indices = np.argsort(counts)[::-1]
    colors: list[dict[str, str | float]] = []
    for sorted_index in sorted_indices:
        label = str(unique_labels[sorted_index])
        percentage = float(counts[sorted_index] / total_count)
        if percentage < 0.04:
            continue
        if percentage < 0.07 and len(colors) >= 2:
            continue

        if not colors:
            role = "primary"
        elif percentage >= 0.18:
            role = "secondary"
        else:
            role = "accent"

        colors.append(
            {
                "label": label,
                "hex": FASHION_COLORS[label],
                "percentage": round(percentage, 2),
                "role": role,
                "confidence": color_confidence(percentage),
            }
        )
        if len(colors) >= max_colors:
            break

    return colors


def infer_season(
    category: str | None,
    item_type: str | None,
    subcategory: str | None,
    color: str | None,
) -> str:
    text = " ".join(
        value.lower()
        for value in [category, item_type, subcategory]
        if value
    )
    color_label = (color or "").lower()

    if any(term in text for term in ["coat", "jacket", "sweater", "hoodie", "boot"]):
        return "Winter"
    if any(term in text for term in ["shorts", "t-shirt", "tee", "sandals"]):
        return "Summer"
    if any(term in text for term in ["shirt", "jeans", "sneakers", "trousers", "polo"]):
        return "All-Season"
    if color_label in {"olive", "brown", "tan", "khaki", "mustard", "maroon"}:
        return "Fall"
    if color_label in {"mint", "cream", "light blue", "pink", "yellow"}:
        return "Spring"
    if color_label in {"white", "beige", "orange"}:
        return "Summer"
    if color_label in {"black", "navy", "grey"}:
        return "Winter"
    return "All-Season"


def analyze_wardrobe_image(
    original_path: str,
    category: str | None = None,
    item_type: str | None = None,
    subcategory: str | None = None,
) -> VisionResult:
    segmented_path = remove_background(original_path)
    color_source_path = segmented_path or original_path
    dominant_colors = extract_dominant_colors(color_source_path)
    dominant_color = (
        {"label": str(dominant_colors[0]["label"]), "hex": str(dominant_colors[0]["hex"])}
        if dominant_colors
        else None
    )
    inferred_season = infer_season(
        category,
        item_type,
        subcategory,
        dominant_color["label"] if dominant_color else None,
    )
    return VisionResult(
        segmented_image_path=segmented_path,
        dominant_color=dominant_color,
        dominant_colors=dominant_colors,
        inferred_season=inferred_season,
    )
