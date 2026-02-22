"""
Handler: Medicine Check
Identifies a medicine from its packaging photo: name, purpose,
dosage, instructions, warnings, and estimated price.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label

LABEL_COLORS: dict[str, str] = {
    "package": "#9B59B6",
    "label":   "#3498DB",
    "barcode": "#95A5A6",
}
DEFAULT_COLOR = "#FF9100"


class MedicineBBox(BaseModel):
    label:       str    # "package", "label", "barcode"
    bbox:        list[int]
    description: str
    confidence:  float


class MedicineInfo(BaseModel):
    name:           str   # brand / trade name
    generic_name:   str   # active ingredient / INN
    category:       str   # e.g. "antibiotic", "painkiller", "antihypertensive"
    purpose:        str   # what the drug is used for
    dosage:         str   # typical dose and frequency
    instructions:   str   # how to take (with/without food, duration, etc.)
    warnings:       str   # key contraindications / side effects
    price_estimate: str   # approximate retail price range (local currency or USD)


class AiResponse(BaseModel):
    objects:  list[MedicineBBox]
    medicine: MedicineInfo


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "Analyze this image and identify the medicine or pharmaceutical product shown.\n\n"
        f"Only proceed if you can identify the product with at least {pct}% confidence.\n\n"
        "Return a JSON object with:\n\n"
        "objects — bounding boxes of key areas:\n"
        "  - label: \"package\" (box/blister/bottle), \"label\" (text area), "
        "or \"barcode\"\n"
        "  - bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "  - description: brief description of the area\n"
        "  - confidence: float 0.0 to 1.0\n\n"
        "medicine — detailed information:\n"
        "  - name: brand / trade name (e.g. \"Nurofen\", \"Augmentin\")\n"
        "  - generic_name: active ingredient or INN "
        "(e.g. \"ibuprofen\", \"amoxicillin + clavulanic acid\")\n"
        "  - category: drug class "
        "(e.g. \"NSAID painkiller\", \"antibiotic\", \"antihypertensive\", "
        "\"antihistamine\", \"probiotic\")\n"
        "  - purpose: what this medicine is used to treat (2–3 sentences)\n"
        "  - dosage: standard dosage for an adult "
        "(e.g. \"400 mg every 6–8 hours, max 1200 mg/day\")\n"
        "  - instructions: how to take it "
        "(e.g. \"take with food\", \"do not crush\", \"complete the full course\")\n"
        "  - warnings: most important warnings / contraindications / side effects "
        "(2–3 key points)\n"
        "  - price_estimate: approximate retail price range "
        "(e.g. \"$5–$12 USD\" or \"50–120 PLN\"); "
        "use USD if the country is unknown\n\n"
        "Return empty objects list and empty medicine strings if no medicine is visible."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    objects    = ai_raw.get("objects", [])
    medicine   = ai_raw.get("medicine", {})
    model_name = ai_raw.get("_model", "")

    image     = open_image(original_path)
    annotated = draw_boxes(image, objects, LABEL_COLORS, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    m = medicine if isinstance(medicine, dict) else {}

    result_table = [
        {"field": "💊 Name",              "value": m.get("name",           "") or "—"},
        {"field": "🧪 Active ingredient", "value": m.get("generic_name",   "") or "—"},
        {"field": "📂 Category",          "value": m.get("category",       "") or "—"},
        {"field": "🩺 Used for",          "value": m.get("purpose",        "") or "—"},
        {"field": "📏 Dosage",            "value": m.get("dosage",         "") or "—"},
        {"field": "📋 Instructions",      "value": m.get("instructions",   "") or "—"},
        {"field": "⚠ Warnings",          "value": m.get("warnings",       "") or "—"},
        {"field": "💰 Price estimate",    "value": m.get("price_estimate", "") or "—"},
    ]

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
