
from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings


class EmbeddingService:
    MODEL_NAME = "gemini-embedding-001"
    OUTPUT_DIMENSIONALITY = 768

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not configured.")

        self.client = genai.Client(
            api_key=settings.GOOGLE_API_KEY
        )

    def embed_documents(
        self,
        documents: list[str],
    ) -> list[list[float]]:
        if not documents:
            return []

        response = self.client.models.embed_content(
            model=self.MODEL_NAME,
            contents=documents,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self.OUTPUT_DIMENSIONALITY,
            ),
        )

        if not response.embeddings:
            raise RuntimeError("Gemini returned no document embeddings.")

        embeddings = [
            embedding.values
            for embedding in response.embeddings
        ]

        if any(vector is None for vector in embeddings):
            raise RuntimeError("Gemini returned an empty embedding vector.")

        return [list(vector) for vector in embeddings]

    def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise ValueError("Query cannot be empty.")

        response = self.client.models.embed_content(
            model=self.MODEL_NAME,
            contents=query,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self.OUTPUT_DIMENSIONALITY,
            ),
        )

        if not response.embeddings or not response.embeddings[0].values:
            raise RuntimeError("Gemini returned no query embedding.")

        return list(response.embeddings[0].values)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
