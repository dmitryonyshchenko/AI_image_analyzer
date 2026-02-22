"""
AI client dispatcher.
Selects the active backend based on the AI_PROVIDER environment variable
and delegates all calls to it.

Supported backends (ai_backends/<name>.py, each must expose call()):
  gemini_api  — Google Gemini via google-genai SDK (default, enforced JSON schema)

To add a new backend:
  1. Create ai_backends/my_provider.py with a call() function matching the signature below.
  2. Set AI_PROVIDER=my_provider in .env.
"""
import os
import importlib

from dotenv import load_dotenv

load_dotenv()


def call_ai(image_path: str, prompt: str, response_schema) -> dict:
    """Send an image + prompt to the active AI backend and return parsed JSON.

    Args:
        image_path:      Local path to the image file.
        prompt:          Text prompt describing what to extract.
        response_schema: Pydantic model class for structured output.

    Returns:
        Parsed JSON response as a dict.
    """
    load_dotenv(override=True)  # re-read .env so changes apply without server restart
    provider = os.environ.get("AI_PROVIDER", "gemini_api")
    try:
        backend = importlib.import_module(f"ai_backends.{provider}")
    except ModuleNotFoundError:
        raise RuntimeError(
            f"AI backend '{provider}' not found. "
            f"Create ai_backends/{provider}.py or change AI_PROVIDER in .env."
        )
    return backend.call(image_path, prompt, response_schema)
