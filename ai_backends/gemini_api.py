"""
AI backend: Google Gemini
Uses gemini-2.5-flash-lite with structured JSON output.
Requires GEMINI_API_KEY in environment.
"""
import os
import json

from google import genai
from google.genai import types


def call(image_path: str, prompt: str, response_schema) -> dict:
    """Send an image + prompt to Gemini and return the parsed JSON response.

    Args:
        image_path:      Local path to the image file.
        prompt:          Text prompt to send alongside the image.
        response_schema: Pydantic model class used as the structured output schema.

    Returns:
        Parsed JSON response as a dict.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    ext = image_path.rsplit(".", 1)[-1].lower()
    mime_map = {
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "png":  "image/png",
        "webp": "image/webp",
    }
    mime_type = mime_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                max_output_tokens=16384,
            ),
        )
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            retry = ""
            try:
                data = json.loads(msg[msg.index("{"):])
                details = data.get("error", {}).get("details", [])
                for d in details:
                    if d.get("@type", "").endswith("RetryInfo"):
                        retry = f" Retry after: {d['retryDelay']}."
            except Exception:
                pass
            raise RuntimeError(
                f"Gemini API quota exceeded — free tier limit reached.{retry} "
                "Generate a new key at https://aistudio.google.com/apikey "
                "or wait and try again."
            )
        raise

    # Prefer response.parsed (SDK-parsed Pydantic object) — avoids json.loads issues
    # with thinking-mode tokens or truncated responses from long outputs.
    try:
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            result = parsed.model_dump()
        else:
            result = json.loads(response.text)
    except Exception as parse_err:
        # Last resort: try to extract only the JSON part from response.text
        raw_text = ""
        try:
            raw_text = response.text or ""
            start = raw_text.index("{")
            end   = raw_text.rindex("}") + 1
            result = json.loads(raw_text[start:end])
        except Exception:
            # Include a snippet of the raw response so we can see what Gemini returned
            snippet = raw_text[:2000] if raw_text else "(empty)"
            raise RuntimeError(
                f"AI returned a response that could not be parsed as JSON. "
                f"(Detail: {parse_err})\n\n"
                f"--- RAW RESPONSE (first 2000 chars) ---\n{snippet}"
            )

    result["_model"] = "gemini-2.5-flash-lite"
    return result
