
from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings


class GeminiClient:
    """Client for Gemini text generation."""

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not configured.")

        self.model_name = settings.GEMINI_MODEL

        self.client = genai.Client(
            api_key=settings.GOOGLE_API_KEY
        )

    def generate_json(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        return response.text


@lru_cache(maxsize=1)
def get_gemini_client() -> GeminiClient:
    return GeminiClient()
