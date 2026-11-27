
from typing import Any

import chromadb

from app.core.config import get_settings


class VectorStoreService:
    """ChromaDB client for insurance knowledge retrieval."""

    def __init__(self):
        settings = get_settings()

        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )

        self.collection_name = settings.CHROMA_COLLECTION

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "Insurance Rater knowledge base",
                "hnsw:space": "cosine",
            },
            # Embeddings are supplied by our embedding service.
            embedding_function=None,
        )

    def heartbeat(self) -> int:
        """Check ChromaDB availability."""

        return self.client.heartbeat()

    def count(self) -> int:
        """Return the number of stored chunks."""

        return self.collection.count()

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Insert document chunks and their embeddings."""

        if not ids:
            raise ValueError("At least one document ID is required.")

        if not (len(ids) == len(documents) == len(embeddings)):
            raise ValueError(
                "IDs, documents and embeddings must have equal lengths."
            )

        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError(
                "Metadata count must match the document count."
            )

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Search for semantically similar document chunks."""

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

    def delete_documents(self, ids: list[str]) -> None:
        """Delete document chunks by their IDs."""

        if ids:
            self.collection.delete(ids=ids)
