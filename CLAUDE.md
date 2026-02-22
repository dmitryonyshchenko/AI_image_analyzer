# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## API Key Security — read this first

**Never ask the user to paste their API key into chat.** Google's automated scanners monitor public channels (GitHub, chat logs, AI sessions) and immediately revoke any key they detect. A key shared in chat is a compromised key.

**If the user shares a key in the conversation:** treat it as already invalid — do not attempt to use it. Tell the user:
1. The key was exposed and is likely already revoked.
2. Revoke it manually at https://aistudio.google.com/apikey just in case.
3. Generate a new key there.
4. Add it **directly** to `.env` in a text editor — never paste it into chat.

The correct setup procedure is below.

## Setup

`GEMINI_API_KEY` must be set before the app will work. If it is missing, the app shows a setup page automatically.

```bash
cp .env.example .env   # then open .env in a text editor and fill in GEMINI_API_KEY
```

Get a free key at https://aistudio.google.com/apikey (sign in with Google → Create API key).
Add it to `.env` directly in your editor — never paste it into a chat or commit it to git.

## Commands

```bash
pip install -r requirements.txt   # install dependencies
python app.py                     # start dev server → http://localhost:5000
```

## Architecture

`app.py` (Flask) receives an image upload, processes it entirely in memory / temp files,
and returns the result page directly in the POST response. **No user images or data are
stored on disk** — the `storage/` directory no longer exists.

### Data flow

```
POST /upload
  ↓
Validate file format (extension + Pillow verify)
  ↓
Extract EXIF metadata (GPS, date) from original — image_metadata.py
  ↓
Run preprocessor pipeline (e.g. resize) — preprocessors/{name}.py
  ↓
Call handler.process() — handlers/{name}.py
  ↓
Handler calls call_ai() — ai_client.py → ai_backends/{provider}.py
  ↓
Handler draws bounding boxes + model label — image_processor.py
  ↓
Annotated image read into base64
  ↓
Temp directory auto-deleted; result.html rendered with inline base64 image
```

### Scenario system

`scenarios.py` is the registry. Each entry maps to a handler module in `handlers/` and
carries per-scenario configuration. `ACTIVE_SCENARIO` sets the default.

**Per-scenario config keys:**
- `handler` — module name in `handlers/`
- `name` / `description` — shown on the upload card
- `confidence_threshold` — minimum AI confidence (0–1), passed to the prompt
- `show_annotated_image` — display annotated image on result page
- `show_result_table` — display result table on result page
- `constant_text` — static text shown between image and table
- `send_image_to_ai` — False = handler does not call AI (e.g. ruler joke)
- `preprocessors` — ordered list of preprocessor modules to run before AI

### Handler contract

Every handler exposes one function:

```python
def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    # Returns:
    # {
    #   "annotated_path": str | None,   # path to annotated image in job_dir (temp)
    #   "error":          str | None,   # error message or None
    #   "result_table":   list[{"field": str, "value": str, "type"?: str}] | None,
    #   "ai_raw":         dict,         # raw backend response (includes "_model" key)
    #   "prompt":         str,          # prompt that was sent to AI
    # }
```

`job_dir` is a `tempfile.TemporaryDirectory` — use it for scratch files only.
`config` contains the per-scenario settings from `scenarios.py`.

### Preprocessor contract

Each `preprocessors/{name}.py` must expose:

```python
def process(image: PIL.Image.Image) -> PIL.Image.Image:
    ...  # return transformed image; original may be modified or replaced
```

Preprocessors are run in-place (saved back to `original_path`) before the handler is called.
EXIF metadata is extracted **before** preprocessors run to avoid data loss from resize.

### AI backend system

`ai_client.py` is a thin dispatcher. It reads `AI_PROVIDER` from env (default `gemini_api`),
imports `ai_backends/{provider}.py`, and calls its `call()` function.

```python
def call(image_path: str, prompt: str, response_schema) -> dict:
    ...  # returns parsed JSON dict; must add "_model" key to the returned dict
```

Currently implemented:
- `ai_backends/gemini_api.py` — Google Gemini via `google-genai` SDK, enforced JSON schema

### Shared utilities

- `ai_client.py` — `call_ai(image_path, prompt, pydantic_schema) → dict`
- `image_processor.py`:
  - `open_image`, `save_image`
  - `draw_boxes(image, items, label_colors, default_color)` — items may have `confidence` field
  - `draw_model_label(image, model_name)` — stamp model name at bottom-right
  - `build_color_map(items, palette)` — assign palette colours to unique labels
  - `COLOR_PALETTE` — list of 10 hex colours for dynamic class colouring
- `image_metadata.py` — `extract_metadata(path) → dict` (GPS + datetime from EXIF)
- `site_config.py` — `SITE_CONFIG` dict, footer text for all pages

### Bounding box format

Gemini returns `[y_min, x_min, y_max, x_max]` with values 0–1000 (normalized).
`draw_boxes()` converts them to pixel coordinates using the actual image size.

### Result table rows

```python
{"field": "Label", "value": "Value"}            # normal row
{"field": "Label", "value": "Value", "type": "metadata"}  # highlighted metadata row (gray bg, always last)
```

## Adding a new scenario

1. Create `handlers/my_scenario.py` — implement `process(original_path, job_dir, stem, ext, config) -> dict`.
2. Add an entry to `SCENARIOS` in `scenarios.py` (position in dict = display order).
3. Optionally set `ACTIVE_SCENARIO = "my_scenario"` in `scenarios.py`.

## Centralizing site text

Edit `site_config.py` → `SITE_CONFIG` dict. The context processor in `app.py` injects
`site` into every template automatically — no per-route changes needed.
