from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class TaxonomyItem:
    label: str
    group: str
    category: str
    type: str
    subcategory: str
    prompts: tuple[str, ...]


TAXONOMY: tuple[TaxonomyItem, ...] = (
    TaxonomyItem(
        label="T-Shirt",
        group="Tops",
        category="Tops",
        type="T-Shirt",
        subcategory="T-Shirt",
        prompts=(
            "a photo of a plain t-shirt",
            "a photo of a short sleeve tee",
            "a product photo of a casual t-shirt",
        ),
    ),
    TaxonomyItem(
        label="Shirt",
        group="Tops",
        category="Tops",
        type="Shirt",
        subcategory="Shirt",
        prompts=(
            "a photo of a button-up shirt",
            "a photo of a collared shirt",
            "a product photo of a casual shirt",
        ),
    ),
    TaxonomyItem(
        label="Polo Shirt",
        group="Tops",
        category="Tops",
        type="Polo Shirt",
        subcategory="Polo Shirt",
        prompts=(
            "a photo of a polo shirt",
            "a photo of a short sleeve collared polo shirt",
            "a product photo of a polo shirt",
        ),
    ),
    TaxonomyItem(
        label="Sweater",
        group="Tops",
        category="Tops",
        type="Sweater",
        subcategory="Sweater",
        prompts=(
            "a photo of a knitted sweater",
            "a photo of a warm pullover sweater",
            "a product photo of a sweater",
        ),
    ),
    TaxonomyItem(
        label="Hoodie",
        group="Outerwear",
        category="Tops",
        type="Hoodie",
        subcategory="Hoodie",
        prompts=(
            "a photo of a hoodie",
            "a photo of a hooded sweatshirt",
            "a product photo of a casual hoodie",
        ),
    ),
    TaxonomyItem(
        label="Jacket",
        group="Outerwear",
        category="Outerwear",
        type="Jacket",
        subcategory="Jacket",
        prompts=(
            "a photo of a jacket",
            "a photo of a casual outerwear jacket",
            "a product photo of a jacket",
        ),
    ),
    TaxonomyItem(
        label="Coat",
        group="Outerwear",
        category="Outerwear",
        type="Coat",
        subcategory="Coat",
        prompts=(
            "a photo of a winter coat",
            "a photo of a long outerwear coat",
            "a product photo of a coat",
        ),
    ),
    TaxonomyItem(
        label="Blazer",
        group="Outerwear",
        category="Outerwear",
        type="Blazer",
        subcategory="Blazer",
        prompts=(
            "a photo of a formal blazer",
            "a photo of a tailored suit blazer",
            "a product photo of a blazer",
        ),
    ),
    TaxonomyItem(
        label="Jeans",
        group="Bottoms",
        category="Bottoms",
        type="Jeans",
        subcategory="Jeans",
        prompts=(
            "a photo of a pair of jeans",
            "a product photo of denim jeans",
            "a photo of casual blue jeans",
        ),
    ),
    TaxonomyItem(
        label="Trousers",
        group="Bottoms",
        category="Bottoms",
        type="Trousers",
        subcategory="Trousers",
        prompts=(
            "a photo of a pair of trousers",
            "a product photo of formal trousers",
            "a photo of dress pants",
        ),
    ),
    TaxonomyItem(
        label="Shorts",
        group="Bottoms",
        category="Bottoms",
        type="Shorts",
        subcategory="Shorts",
        prompts=(
            "a photo of a pair of shorts",
            "a product photo of casual shorts",
            "a photo of summer shorts",
        ),
    ),
    TaxonomyItem(
        label="Skirt",
        group="Bottoms",
        category="Bottoms",
        type="Skirt",
        subcategory="Skirt",
        prompts=(
            "a photo of a skirt",
            "a product photo of a skirt",
            "a photo of a casual skirt",
        ),
    ),
    TaxonomyItem(
        label="Dress",
        group="Dresses",
        category="Dresses",
        type="Dress",
        subcategory="Dress",
        prompts=(
            "a photo of a dress",
            "a product photo of a formal dress",
            "a photo of a one-piece dress",
        ),
    ),
    TaxonomyItem(
        label="Sneakers",
        group="Shoes",
        category="Footwear",
        type="Sneakers",
        subcategory="Sneakers",
        prompts=(
            "a photo of a pair of sneakers",
            "a product photo of athletic sneakers",
            "a photo of casual trainers shoes",
        ),
    ),
    TaxonomyItem(
        label="Boots",
        group="Shoes",
        category="Footwear",
        type="Boots",
        subcategory="Boots",
        prompts=(
            "a photo of a pair of boots",
            "a product photo of leather boots",
            "a photo of winter boots",
        ),
    ),
    TaxonomyItem(
        label="Loafers",
        group="Shoes",
        category="Footwear",
        type="Loafers",
        subcategory="Loafers",
        prompts=(
            "a photo of a pair of loafers",
            "a product photo of leather loafers",
            "a photo of slip-on dress shoes",
        ),
    ),
    TaxonomyItem(
        label="Sandals",
        group="Shoes",
        category="Footwear",
        type="Sandals",
        subcategory="Sandals",
        prompts=(
            "a photo of a pair of sandals",
            "a product photo of summer sandals",
            "a photo of open-toe sandals",
        ),
    ),
    TaxonomyItem(
        label="Formal Shoes",
        group="Shoes",
        category="Footwear",
        type="Formal Shoes",
        subcategory="Formal Shoes",
        prompts=(
            "a photo of a pair of formal shoes",
            "a product photo of black dress shoes",
            "a photo of polished leather formal shoes",
        ),
    ),
    TaxonomyItem(
        label="Kurta",
        group="Eastern",
        category="Tops",
        type="Kurta",
        subcategory="Kurta",
        prompts=(
            "a photo of a kurta",
            "a product photo of a traditional kurta",
            "a photo of a long eastern tunic kurta",
        ),
    ),
    TaxonomyItem(
        label="Shalwar Kameez",
        group="Eastern",
        category="Other",
        type="Shalwar Kameez",
        subcategory="Shalwar Kameez",
        prompts=(
            "a photo of a shalwar kameez",
            "a product photo of a traditional shalwar kameez",
            "a photo of an eastern shalwar kameez outfit",
        ),
    ),
    TaxonomyItem(
        label="Saree",
        group="Eastern",
        category="Dresses",
        type="Saree",
        subcategory="Saree",
        prompts=(
            "a photo of a saree",
            "a product photo of a traditional saree",
            "a photo of an eastern draped saree",
        ),
    ),
    TaxonomyItem(
        label="Waistcoat",
        group="Eastern",
        category="Outerwear",
        type="Waistcoat",
        subcategory="Waistcoat",
        prompts=(
            "a photo of a waistcoat",
            "a product photo of a formal waistcoat",
            "a photo of a sleeveless eastern waistcoat",
        ),
    ),
)

TAXONOMY_BY_LABEL = {item.label.lower(): item for item in TAXONOMY}
DEFAULT_TAXONOMY_ITEM = TAXONOMY_BY_LABEL["shirt"]
FILENAME_ALIASES: tuple[tuple[set[str], str], ...] = (
    ({"dress", "shoes"}, "Formal Shoes"),
    ({"tee"}, "T-Shirt"),
    ({"tshirt"}, "T-Shirt"),
    ({"pants"}, "Trousers"),
    ({"trainers"}, "Sneakers"),
    ({"shoes"}, "Sneakers"),
)


def get_taxonomy_item(label: str | None) -> TaxonomyItem:
    if not label:
        return DEFAULT_TAXONOMY_ITEM
    return TAXONOMY_BY_LABEL.get(label.lower(), DEFAULT_TAXONOMY_ITEM)


def prompt_entries() -> list[tuple[TaxonomyItem, str]]:
    return [(item, prompt) for item in TAXONOMY for prompt in item.prompts]


def taxonomy_item_from_filename(image_path: str) -> TaxonomyItem | None:
    stem = Path(image_path).stem.lower()
    tokens = set(re.findall(r"[a-z0-9]+", stem))
    if not tokens:
        return None

    for alias_tokens, label in FILENAME_ALIASES:
        if alias_tokens.issubset(tokens):
            return get_taxonomy_item(label)

    for item in sorted(TAXONOMY, key=lambda taxonomy_item: len(taxonomy_item.label), reverse=True):
        label_tokens = set(re.findall(r"[a-z0-9]+", item.label.lower()))
        if label_tokens and label_tokens.issubset(tokens):
            return item

    return None


def title_case(value: str) -> str:
    special_cases = {
        "t-shirt": "T-Shirt",
        "tshirt": "T-Shirt",
        "polo shirt": "Polo Shirt",
        "shalwar kameez": "Shalwar Kameez",
        "formal shoes": "Formal Shoes",
        "animal print": "Animal Print",
        "polka dot": "Polka Dot",
        "denim wash": "Denim Wash",
    }
    normalized = value.strip().lower()
    if normalized in special_cases:
        return special_cases[normalized]
    return " ".join(part.capitalize() for part in value.split())


def normalized_color_for_name(
    color_label: str | None,
    item_type: str,
    pattern_tags: list[str] | None = None,
) -> str | None:
    if not color_label or color_label.startswith("#"):
        return None
    patterns = set(pattern_tags or [])
    if color_label == "denim blue" and item_type != "Jeans" and "denim wash" not in patterns:
        return "blue"
    if color_label == "mint" and item_type == "Jeans":
        return "light blue"
    return color_label


def color_percentage(color: dict) -> float:
    try:
        return float(color.get("percentage", 0))
    except (TypeError, ValueError):
        return 0.0


def color_family(label: str) -> str:
    if label in {"light blue", "blue", "denim blue", "mint"}:
        return "blue"
    if label in {"grey", "charcoal"}:
        return "grey"
    if label in {"dark brown", "brown", "maroon"}:
        return "brown"
    if label in {"white", "cream"}:
        return "white"
    if label in {"olive", "green", "khaki"}:
        return "green"
    return label


def preferred_family_label(labels: list[str], item_type: str) -> str:
    label_set = set(labels)
    if label_set <= {"light blue", "blue", "denim blue", "mint"}:
        if item_type == "Jeans":
            if "denim blue" in label_set:
                return "denim blue"
            return "light blue"
        if "light blue" in label_set:
            return "light blue"
        return next(label for label in labels if label in label_set)
    if label_set <= {"grey", "charcoal"}:
        return "charcoal" if "charcoal" in label_set and labels[0] == "charcoal" else "grey"
    if label_set <= {"dark brown", "brown", "maroon"}:
        if "dark brown" in label_set:
            return "dark brown"
        return labels[0]
    if label_set <= {"white", "cream"}:
        return "white" if "white" in label_set else "cream"
    if label_set <= {"olive", "green", "khaki"}:
        return labels[0]
    return labels[0]


def merge_color_families_for_name(
    dominant_colors: list[dict] | None,
    item_type: str,
    pattern_tags: list[str] | None = None,
) -> list[dict]:
    if not dominant_colors:
        return []

    groups: list[dict] = []
    for color in dominant_colors:
        label = normalized_color_for_name(
            str(color.get("label", "")),
            item_type,
            pattern_tags,
        )
        if not label:
            continue
        family = color_family(label)
        percentage = color_percentage(color)
        existing = next((group for group in groups if group["family"] == family), None)
        if existing:
            existing["percentage"] += percentage
            existing["labels"].append(label)
            if percentage > existing["max_percentage"]:
                existing["max_percentage"] = percentage
                existing["primary_label"] = label
            continue
        groups.append(
            {
                "family": family,
                "percentage": percentage,
                "max_percentage": percentage,
                "primary_label": label,
                "labels": [label],
            }
        )

    calibrated: list[dict] = []
    for group in groups:
        labels = [group["primary_label"], *[label for label in group["labels"] if label != group["primary_label"]]]
        calibrated.append(
            {
                "label": preferred_family_label(labels, item_type),
                "family": group["family"],
                "percentage": round(group["percentage"], 2),
            }
        )

    calibrated.sort(key=lambda color: color["percentage"], reverse=True)

    if item_type == "Jeans":
        blue_index = next(
            (
                index
                for index, color in enumerate(calibrated)
                if color["family"] == "blue" and color["percentage"] >= 0.18
            ),
            None,
        )
        if blue_index is not None:
            blue_color = calibrated.pop(blue_index)
            calibrated.insert(0, blue_color)

    return calibrated


def should_include_secondary_color(primary: dict, secondary: dict, item_type: str) -> bool:
    if primary["family"] == secondary["family"]:
        return False
    if item_type == "Jeans" and primary["family"] == "blue" and secondary["family"] in {"grey", "black", "white"}:
        return False

    secondary_percentage = float(secondary["percentage"])
    primary_percentage = float(primary["percentage"])
    high_contrast_pair = {primary["family"], secondary["family"]} in (
        {"white", "black"},
        {"white", "grey"},
        {"black", "grey"},
    )

    if secondary["family"] in {"black", "white"} and secondary_percentage < 0.28:
        return False
    if primary_percentage >= 0.68 and secondary_percentage < 0.32:
        return False
    if high_contrast_pair and secondary_percentage >= 0.26:
        return True
    return secondary_percentage >= 0.32


def color_phrase(
    dominant_colors: list[dict] | None,
    fallback_color: str | None,
    item_type: str,
    pattern_tags: list[str] | None = None,
) -> str | None:
    usable_colors: list[str] = []
    calibrated_colors = merge_color_families_for_name(dominant_colors, item_type, pattern_tags)
    if calibrated_colors:
        primary = calibrated_colors[0]
        usable_colors.append(str(primary["label"]))
        if len(calibrated_colors) > 1 and should_include_secondary_color(primary, calibrated_colors[1], item_type):
            usable_colors.append(str(calibrated_colors[1]["label"]))

    if not usable_colors:
        label = normalized_color_for_name(fallback_color, item_type, pattern_tags)
        if label:
            usable_colors.append(label)

    if not usable_colors:
        return None
    if len(usable_colors) == 1:
        return title_case(usable_colors[0])
    return f"{title_case(usable_colors[0])} and {title_case(usable_colors[1])}"


def generate_item_name(
    color_label: str | None,
    item_type: str,
    dominant_colors: list[dict] | None = None,
    pattern_tags: list[str] | None = None,
) -> str:
    patterns = [tag for tag in (pattern_tags or []) if tag and tag != "solid"]
    phrase = color_phrase(dominant_colors, color_label, item_type, patterns)
    item_type_title = title_case(item_type)

    graphic_pattern = next((tag for tag in patterns if tag in {"graphic", "logo"}), None)
    if graphic_pattern:
        main_phrase = color_phrase(
            dominant_colors[:1] if dominant_colors else None,
            color_label,
            item_type,
            patterns,
        )
        graphic_color = None
        if dominant_colors and len(dominant_colors) > 1:
            graphic_color = normalized_color_for_name(
                str(dominant_colors[1].get("label", "")),
                item_type,
                patterns,
            )
        graphic_description = (
            f"{title_case(graphic_color)} {title_case(graphic_pattern)}"
            if graphic_color
            else title_case(graphic_pattern)
        )
        return f"{main_phrase} {item_type_title} with {graphic_description}" if main_phrase else f"{item_type_title} with {graphic_description}"

    name_pattern = next(
        (
            tag
            for tag in patterns
            if tag
            in {
                "striped",
                "plaid",
                "checked",
                "floral",
                "polka dot",
                "colorblock",
                "geometric",
                "animal print",
                "camouflage",
                "denim wash",
                "embroidered",
                "textured",
            }
        ),
        None,
    )
    if name_pattern == "colorblock" and phrase and " and " in phrase:
        name_pattern = None
    pattern_phrase = f"{title_case(name_pattern)} " if name_pattern else ""
    return f"{phrase} {pattern_phrase}{item_type_title}".strip() if phrase else f"{pattern_phrase}{item_type_title}".strip()
