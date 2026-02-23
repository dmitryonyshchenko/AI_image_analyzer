import os
import uuid
import base64
import tempfile
import traceback
import importlib
from datetime import datetime

from flask import Flask, request, render_template, Response
from dotenv import load_dotenv
from PIL import Image as PILImage

from scenarios import SCENARIOS, ACTIVE_SCENARIO
from image_metadata import extract_metadata
from site_config import SITE_CONFIG

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Only static file serving bypasses the API-key check
_NO_KEY_ALLOWED = {"static", "robots_txt"}

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ERROR_LOG          = "last_error.log"


# ── Inject site config into every template automatically ──────────────────────
@app.context_processor
def inject_globals():
    return {"site": SITE_CONFIG}


@app.before_request
def require_api_key():
    if request.endpoint in _NO_KEY_ALLOWED:
        return
    # Ruler and other no-AI scenarios work without a key
    if request.method == "POST" and request.endpoint == "upload":
        scenario = request.form.get("scenario", "")
        if SCENARIOS.get(scenario, {}).get("send_image_to_ai", True) is False:
            return
    if not os.environ.get("GEMINI_API_KEY"):
        return render_template("setup.html"), 503


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log_error(context: str, exc: Exception) -> None:
    """Write the last error with timestamp to last_error.log (no user data)."""
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {context}\n\n")
        if exc.__traceback__:
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
        else:
            f.write(f"{type(exc).__name__}: {exc}\n")


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower()


def _make_stem() -> str:
    dt  = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:12]
    return f"{dt}_{uid}"


def _get_handler(scenario_key: str):
    handler_name = SCENARIOS[scenario_key]["handler"]
    return importlib.import_module(f"handlers.{handler_name}")


def _run_preprocessors(image_path: str, preprocessor_names: list) -> None:
    """Run image through preprocessor pipeline in-place (save result to same path)."""
    if not preprocessor_names:
        return
    from image_processor import open_image, save_image
    image = open_image(image_path)
    for name in preprocessor_names:
        mod   = importlib.import_module(f"preprocessors.{name}")
        image = mod.process(image)
    save_image(image, image_path)


def _to_b64(path: str) -> str | None:
    """Read a file and return its base64-encoded contents, or None on failure."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/robots.txt")
def robots_txt():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")


@app.route("/")
def index():
    return render_template("index.html", scenarios=SCENARIOS, active_scenario=ACTIVE_SCENARIO)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")
    if not file or not file.filename:
        return render_template("error.html", message="No file received."), 400
    if not _allowed(file.filename):
        return render_template(
            "error.html",
            message="Unsupported file type. Please upload a JPG, PNG or WEBP image.",
        ), 400

    ext  = _ext(file.filename)
    stem = _make_stem()

    scenario_key = request.form.get("scenario", ACTIVE_SCENARIO)
    if scenario_key not in SCENARIOS:
        return render_template("error.html", message=f"Unknown scenario: {scenario_key}"), 400

    scenario_cfg = SCENARIOS[scenario_key]
    handler      = _get_handler(scenario_key)

    # Process inside a temporary directory — nothing is kept on disk afterwards
    with tempfile.TemporaryDirectory() as tmpdir:
        original_path = os.path.join(tmpdir, f"{stem}.{ext}")
        file.save(original_path)

        # Validate the file is actually an image
        try:
            img_test = PILImage.open(original_path)
            img_test.verify()  # raises on corrupt / non-image files
        except Exception:
            return render_template(
                "error.html",
                message="The uploaded file does not appear to be a valid image.",
            ), 400

        # Extract EXIF metadata BEFORE any preprocessing (resize loses EXIF)
        meta_info = extract_metadata(original_path)

        # Run preprocessors (e.g. resize) in-place on the temp file
        _run_preprocessors(original_path, scenario_cfg.get("preprocessors", []))

        try:
            result = handler.process(
                original_path=original_path,
                job_dir=tmpdir,
                stem=stem,
                ext=ext,
                config=scenario_cfg,
            )
        except Exception as e:
            _log_error(f"scenario={scenario_key}", e)
            return render_template("error.html", message=f"Processing failed: {e}"), 500

        if result.get("error"):
            _log_error(f"scenario={scenario_key}", RuntimeError(result["error"]))
            return render_template("error.html", message=result["error"]), 500

        # Encode annotated image (or fallback to original) as base64 while temp dir exists
        ann_path = result.get("annotated_path")
        if ann_path and os.path.exists(ann_path):
            image_b64  = _to_b64(ann_path)
            show_image = scenario_cfg.get("show_annotated_image", True)
        elif os.path.exists(original_path) and scenario_cfg.get("show_annotated_image", True):
            image_b64  = _to_b64(original_path)
            show_image = True
        else:
            image_b64  = None
            show_image = False

        # MIME type for the data: URL
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}
        img_mime = mime_map.get(ext, "jpeg")

        # Build result table
        result_table = list(result.get("result_table") or [])

        # Append metadata rows (always at the end, visually highlighted)
        if meta_info.get("location"):
            result_table.append({
                "field": "📍 Photo location",
                "value": meta_info["location"],
                "type":  "metadata",
            })
        if meta_info.get("datetime"):
            result_table.append({
                "field": "📷 Photo date/time",
                "value": meta_info["datetime"],
                "type":  "metadata",
            })

    # Temp directory cleaned up; render using in-memory data only
    return render_template(
        "result.html",
        image_b64=image_b64,
        img_mime=img_mime,
        show_image=show_image,
        scenario_key=scenario_key,
        scenario=scenario_cfg,
        result_table=result_table if result_table else None,
    )


if __name__ == "__main__":
    print("Starting on http://localhost:5000")
    app.run(debug=True, port=5000)
