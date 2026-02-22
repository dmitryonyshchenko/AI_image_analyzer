"""
Handler: Fridge Recipe
Detects food products visible in the image, suggests one dish to cook,
and returns a recipe with ingredients and quantities.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label, build_color_map, COLOR_PALETTE

DEFAULT_COLOR = "#FF9100"


class FoodItem(BaseModel):
    label:       str    # product name, e.g. "tomato", "chicken breast"
    bbox:        list[int]
    description: str
    confidence:  float


class Ingredient(BaseModel):
    name:     str   # e.g. "tomato"
    quantity: str   # e.g. "2 pcs" / "200 g"


class AiResponse(BaseModel):
    items:        list[FoodItem]   # detected food products with bboxes
    dish_name:    str              # suggested dish to cook
    cooking_time: str              # e.g. "30 minutes"
    recipe:       str              # step-by-step cooking instructions
    ingredients:  list[Ingredient] # full ingredient list with quantities


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "Analyze this photo and identify all visible food products, ingredients, "
        "and drinks (in the fridge, on the table, or anywhere in the image).\n\n"
        f"Only include items you can identify with at least {pct}% confidence.\n\n"
        "Then, based on the detected ingredients, suggest ONE dish that can be cooked "
        "from them (you may assume basic pantry staples like salt, oil, and water are available).\n\n"
        "Return a JSON object with:\n\n"
        "items — list of detected food products with bounding boxes:\n"
        "  - label: product name (e.g. \"tomato\", \"chicken breast\", \"milk\")\n"
        "  - bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "  - description: brief description (color, quantity visible, condition)\n"
        "  - confidence: float 0.0 to 1.0\n\n"
        "dish_name    — name of the suggested dish (empty string if no food found)\n"
        "cooking_time — estimated cooking time (e.g. \"25 minutes\")\n"
        "recipe       — step-by-step cooking instructions as a single text block\n"
        "ingredients  — full ingredient list for the dish:\n"
        "  - name: ingredient name\n"
        "  - quantity: amount needed (e.g. \"2 pcs\", \"200 g\", \"1 cup\")\n\n"
        "Return empty items list and empty strings if no food is visible."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    items      = ai_raw.get("items", [])
    model_name = ai_raw.get("_model", "")

    # Each food product gets a unique color from the palette
    color_map  = build_color_map(items, COLOR_PALETTE)

    image     = open_image(original_path)
    annotated = draw_boxes(image, items, color_map, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    # ── Result table ──────────────────────────────────────────────────────────
    result_table = []

    dish_name    = ai_raw.get("dish_name", "") or "—"
    cooking_time = ai_raw.get("cooking_time", "") or "—"
    recipe       = ai_raw.get("recipe", "") or "—"
    ingredients  = ai_raw.get("ingredients", [])

    # Recipe summary at the top
    result_table += [
        {"field": "🍽 Suggested Dish", "value": dish_name},
        {"field": "⏱ Cooking Time",   "value": cooking_time},
        {"field": "📋 Recipe",         "value": recipe},
        {"field": "─── Ingredients ───", "value": ""},
    ]

    for ing in ingredients:
        result_table.append({
            "field": ing.get("name", "—"),
            "value": ing.get("quantity", "—"),
        })

    if not ingredients:
        result_table.append({"field": "Ingredients", "value": "—"})

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
