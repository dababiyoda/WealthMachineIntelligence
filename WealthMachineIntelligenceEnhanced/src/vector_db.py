"""Milvus vector database abstraction.

This module wraps the pymilvus client and exposes basic operations for
collection creation, inserting embeddings and performing similarity search.
It assumes that each embedding is a list of floats and that the primary
identifier is a UUID string.

If Milvus is not available, the constructor will raise an exception.  This
module does not manage indexes beyond the default configuration; users
should create indexes appropriate for their use case via Milvus CLI or UI.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any
from uuid import uuid4

from pymilvus import MilvusClient, DataType

from .config import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    COLLECTION_NAME = "ventures"
    DIMENSIONS = 768  # default embedding dimensionality

    def __init__(self) -> None:
        settings = get_settings()
        self.client = MilvusClient(host=settings.milvus_host, port=settings.milvus_port)
        logger.info("Connected to Milvus at %s:%s", settings.milvus_host, settings.milvus_port)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        if not self.client.has_collection(self.COLLECTION_NAME):
            logger.info("Creating Milvus collection '%s'", self.COLLECTION_NAME)
            schema = {
                "fields": [
                    {"name": "id", "type": DataType.VARCHAR, "max_length": 64, "is_primary": True},
                    {"name": "embedding", "type": DataType.FLOAT_VECTOR, "dim": self.DIMENSIONS},
                ],
            }
            self.client.create_collection(self.COLLECTION_NAME, schema=schema, index_params={})

    def insert(self, embedding: List[float], id: str | None = None) -> str:
        """Insert a single embedding into the collection and return the ID."""
        if id is None:
            id = str(uuid4())
        data = {"id": [id], "embedding": [embedding]}
        self.client.insert(self.COLLECTION_NAME, data)
        return id

    def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """Search the collection for the k most similar embeddings."""
        search_params = {"metric_type": "L2"}  # Euclidean distance
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=["id"],
        )
        hits = results[0]
        return [{"id": hit.get("id"), "score": hit.distance} for hit in hits]


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
