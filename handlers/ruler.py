"""
Handler: Ruler (joke)
Does not call AI, does not process the image.
Returns an empty result so app.py has something to display.
The constant_text from scenarios.py is shown to the user instead.
"""


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    return {
        "annotated_path": None,
        "error":          None,
        "result_table":   None,
        "ai_raw":         {},
        "prompt":         "",
    }
