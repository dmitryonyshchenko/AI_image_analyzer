# ─────────────────────────────────────────────────────────────────────────────
#  Scenario registry
#
#  Each scenario maps to a handler module in handlers/.
#  Scenarios are displayed on the upload page in the order they appear here.
#
#  Per-scenario config fields:
#    handler              — module name in handlers/ (e.g. "vehicles")
#    name                 — short title shown on the scenario card
#    description          — one-line description shown on the scenario card
#    confidence_threshold — minimum confidence (0–1) passed to the AI prompt
#    show_annotated_image — display the annotated image on the result page
#    show_result_table    — display the result table on the result page
#    constant_text        — static text shown between image and table (optional)
#    send_image_to_ai     — whether this scenario uses AI (False = no API call)
#    preprocessors        — ordered list of preprocessor module names to run
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_PREPROCESSORS = ["resize"]

_DEFAULT_FLAGS = {
    "confidence_threshold": 0.70,
    "show_annotated_image": True,
    "show_result_table":    True,
    "constant_text":        "",
    "send_image_to_ai":     True,
    "preprocessors":        _DEFAULT_PREPROCESSORS,
}

SCENARIOS: dict[str, dict] = {

    "vehicles": {
        **_DEFAULT_FLAGS,
        "handler":     "vehicles",
        "name":        "Fridge Recipe",
        "description": "Photo your fridge or table — AI spots the ingredients and suggests a dish with a full recipe.",
    },

    "car": {
        **_DEFAULT_FLAGS,
        "handler":     "car",
        "name":        "Car Valuation",
        "description": "Identify the car, read the plate, detect violations, and get an estimated market value in USD.",
    },

    "objects": {
        **_DEFAULT_FLAGS,
        "handler":     "objects",
        "name":        "Object Detection",
        "description": "Detect and label all large objects in the image.",
    },

    "person": {
        **_DEFAULT_FLAGS,
        "handler":     "person",
        "name":        "Person Description",
        "description": "Describe the main person: gender, age, hair, eyes, build, and skin tone.",
    },

    "instruments": {
        **_DEFAULT_FLAGS,
        "handler":     "instruments",
        "name":        "Instrument Reading",
        "description": "Read values from gauges, meters, speedometers, and dashboards.",
    },

    "receipt": {
        **_DEFAULT_FLAGS,
        "handler":     "receipt",
        "name":        "Receipt Reading",
        "description": "Extract category, items, prices, seller, date/time, and total from a receipt.",
    },

    "satellite": {
        **_DEFAULT_FLAGS,
        "handler":     "satellite",
        "name":        "Satellite Image Analysis",
        "description": "Analyze aerial or satellite imagery: landscape, area type, classification, and notable objects.",
    },

    "medicine": {
        **_DEFAULT_FLAGS,
        "handler":     "medicine",
        "name":        "Medicine Check",
        "description": "Photo a medicine pack — get the drug name, purpose, dosage, warnings, and price estimate.",
    },

    "ruler": {
        **_DEFAULT_FLAGS,
        "handler":              "ruler",
        "name":                 "Measure Length (cm)",
        "description":          "Upload a photo — AI will measure the object length in centimetres.",
        "show_annotated_image": False,
        "show_result_table":    False,
        "send_image_to_ai":     False,
        "preprocessors":        [],
        "constant_text": (
            "😄 This is a joke — I was just curious how many people would try to measure "
            "something with AI. Please use a ruler for actual measurements!"
        ),
    },

}

# ── Default scenario shown on the upload page ────────────────────────────────
ACTIVE_SCENARIO = "vehicles"
