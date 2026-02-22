# AI Image Analyzer

A local web app that sends photos to **Google Gemini** and displays annotated results — colored bounding boxes on the image plus a structured result table.

## Quick Start

### 1. Get a free Gemini API key

Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey), sign in with Google, and click **Create API key**. The free tier is sufficient.

### 2. Configure the key

```bash
cp .env.example .env
```

Open `.env` in a **text editor** and replace `your_api_key_here` with your actual key.

> **Security warning:** Never paste your API key into chat with AI assistants, GitHub issues, or any other message. Google's scanners automatically detect and revoke keys found in public or shared text. Always add the key directly to `.env` in a text editor — your editor does not transmit the value anywhere.

### 3. Install and run

```bash
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

> If the key is not configured the app will show a setup page with instructions automatically.

---

## Scenarios

The active scenario is set in `scenarios.py`:

```python
ACTIVE_SCENARIO = "vehicles"   # or "license_plate" or "homework"
```

| Scenario | What it detects | Result table |
|---|---|---|
| `vehicles` | Pedestrians & cars | Counts |
| `license_plate` | Vehicles & plates | Make / model / color / plate number |
| `homework` | Correct & incorrect answers | Counts + grade |

---

## Adding a new scenario

1. Create `handlers/my_scenario.py` with a `process()` function — see any existing handler for the contract.
2. Add an entry to `SCENARIOS` in `scenarios.py`.
3. Set `ACTIVE_SCENARIO = "my_scenario"`.

---

## Storage

Each processed image adds three files to a daily folder under `storage/`:

```
storage/
└── 20260221/
    ├── 20260221_143022_abc1def2ef34.jpg            # original
    ├── 20260221_143022_abc1def2ef34_annotated.jpg  # with bounding boxes
    └── 20260221_143022_abc1def2ef34.json           # AI response + metadata
```

Storage contents are gitignored.

---

## Deploying to a hosted environment

Set `GEMINI_API_KEY` as an **environment variable** in your hosting dashboard (Render, Railway, Fly.io, etc.). Do **not** commit `.env` — it is already in `.gitignore`.
