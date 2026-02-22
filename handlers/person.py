"""
Handler: Person Description
Identifies the main person in the image and describes their visible characteristics.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label

LABEL_COLORS: dict[str, str] = {"person": "#00C853"}
DEFAULT_COLOR = "#FF9100"


class PersonBox(BaseModel):
    label:      str    # "person"
    bbox:       list[int]
    confidence: float


class PersonAttributes(BaseModel):
    gender:           str
    age_estimate:     str   # e.g. "25–35 years old"
    hair_color:       str
    eye_color:        str   # may be "not visible"
    height_estimate:  str   # e.g. "average, ~175 cm"
    weight_estimate:  str   # e.g. "medium build, ~75 kg"
    skin_tone:        str


class AiResponse(BaseModel):
    person:     PersonBox
    attributes: PersonAttributes


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "Find the MAIN person in the image and describe their visible characteristics.\n\n"
        f"Only proceed if you can identify the person with at least {pct}% confidence.\n\n"
        "Return a JSON object with:\n\n"
        "person:\n"
        "  - label: \"person\"\n"
        "  - bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "  - confidence: float 0.0 to 1.0\n\n"
        "attributes:\n"
        "  - gender: \"male\", \"female\", or \"unknown\"\n"
        "  - age_estimate: estimated age range (e.g. \"25–35 years old\")\n"
        "  - hair_color: visible hair color or \"not visible\"\n"
        "  - eye_color: visible eye color or \"not visible\"\n"
        "  - height_estimate: approximate height description (e.g. \"average build, ~175 cm\")\n"
        "  - weight_estimate: approximate build (e.g. \"medium build, ~75 kg\")\n"
        "  - skin_tone: skin tone description\n\n"
        "If no person is visible, return empty bbox [] and empty attribute strings."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    person_box = ai_raw.get("person", {})
    attrs      = ai_raw.get("attributes", {})
    model_name = ai_raw.get("_model", "")

    items = []
    if isinstance(person_box, dict) and len(person_box.get("bbox", [])) == 4:
        items = [{
            "label":       "person",
            "bbox":        person_box["bbox"],
            "confidence":  person_box.get("confidence", 0.0),
            "description": "Main person",
        }]

    image     = open_image(original_path)
    annotated = draw_boxes(image, items, LABEL_COLORS, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    if isinstance(attrs, dict):
        result_table = [
            {"field": "Gender",    "value": attrs.get("gender",          "") or "—"},
            {"field": "Age",       "value": attrs.get("age_estimate",    "") or "—"},
            {"field": "Hair",      "value": attrs.get("hair_color",      "") or "—"},
            {"field": "Eyes",      "value": attrs.get("eye_color",       "") or "—"},
            {"field": "Height",    "value": attrs.get("height_estimate", "") or "—"},
            {"field": "Build",     "value": attrs.get("weight_estimate", "") or "—"},
            {"field": "Skin tone", "value": attrs.get("skin_tone",       "") or "—"},
        ]
    else:
        result_table = [{"field": "Result", "value": "No person detected"}]

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
