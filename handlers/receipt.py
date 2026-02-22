"""
Handler: Receipt Reading
Extracts items, prices, seller name, date/time, and total from a receipt photo.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label, build_color_map

LABEL_COLORS: dict[str, str] = {
    "header": "#45B7D1",
    "item":   "#4ECDC4",
    "total":  "#FF6B6B",
}
DEFAULT_COLOR = "#FF9100"


class LineItem(BaseModel):
    name:  str
    price: str


class ReceiptBBox(BaseModel):
    label:       str    # "header", "item", "total"
    bbox:        list[int]
    description: str
    confidence:  float


class AiResponse(BaseModel):
    objects:  list[ReceiptBBox]
    category: str       # e.g. "groceries", "fuel", "restaurant", "pharmacy"
    items:    list[LineItem]
    seller:   str
    date:     str
    time:     str
    total:    str


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "Read the receipt in this image and extract its contents.\n\n"
        f"Only include data you can read with at least {pct}% confidence.\n\n"
        "Return a JSON object with:\n\n"
        "objects — bounding boxes of key receipt sections:\n"
        "  - label: \"header\" (store name/logo), \"item\" (product line), or \"total\"\n"
        "  - bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "  - description: what is shown in this area\n"
        "  - confidence: float 0.0 to 1.0\n\n"
        "category — receipt category, one of: \"groceries\", \"fuel\", \"restaurant\", "
        "\"pharmacy\", \"electronics\", \"clothing\", \"transport\", \"utilities\", "
        "\"entertainment\", \"other\" (empty string if not a receipt)\n\n"
        "items — list of purchased products/services:\n"
        "  - name: product or service name\n"
        "  - price: price as string (e.g. \"12.99\", \"1 500\")\n\n"
        "seller — store or business name (empty string if not visible)\n"
        "date   — purchase date (empty string if not visible)\n"
        "time   — purchase time (empty string if not visible)\n"
        "total  — total amount as string (empty string if not visible)\n\n"
        "Return empty lists and empty strings if the receipt is not readable."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    objects    = ai_raw.get("objects", [])
    items      = ai_raw.get("items", [])
    model_name = ai_raw.get("_model", "")

    image     = open_image(original_path)
    annotated = draw_boxes(image, objects, LABEL_COLORS, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    category = ai_raw.get("category", "") or "—"

    result_table = [
        {"field": "🏷 Category", "value": category.capitalize()},
        {"field": "─── Items ───", "value": ""},
    ]
    for it in items:
        result_table.append({"field": it.get("name", "—"), "value": it.get("price", "—")})

    # Summary section
    result_table += [
        {"field": "─── Summary ───", "value": ""},
        {"field": "Seller",         "value": ai_raw.get("seller", "") or "—"},
        {"field": "Date",           "value": ai_raw.get("date",   "") or "—"},
        {"field": "Time",           "value": ai_raw.get("time",   "") or "—"},
        {"field": "Total",          "value": ai_raw.get("total",  "") or "—"},
    ]

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
