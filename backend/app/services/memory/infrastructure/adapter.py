import logging
from typing import Any

logger = logging.getLogger(__name__)

class VectorDatabaseAdapter:
    """
    Hexagonal interface for vector persistence.
    """
    async def insert_vector(self, embedding_id: str, vector: list[float], metadata: dict[str, Any]):
        raise NotImplementedError()

    async def search_vectors(self, query_vector: list[float], limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError()

    async def delete_vector(self, embedding_id: str):
        raise NotImplementedError()

class PgVectorAdapter(VectorDatabaseAdapter):
    """
    Production backend using PostgreSQL pgvector.
    """
    def __init__(self, session_maker: Any):
        self.session_maker = session_maker
        logger.info("Initialized PgVectorAdapter.")

    async def insert_vector(self, embedding_id: str, vector: list[float], metadata: dict[str, Any]):
        # Simulated insertion for pgvector
        logger.info(f"PgVectorAdapter: Inserting vector {embedding_id}")

    async def search_vectors(self, query_vector: list[float], limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
        # Simulated search
        logger.info(f"PgVectorAdapter: Searching with limit {limit} and filters {filters}")
        return []

    async def delete_vector(self, embedding_id: str):
        logger.info(f"PgVectorAdapter: Deleting vector {embedding_id}")

class InMemoryVectorAdapter(VectorDatabaseAdapter):
    """
    Exclusively for unit testing.
    """
    def __init__(self):
        self._store = {}

    async def insert_vector(self, embedding_id: str, vector: list[float], metadata: dict[str, Any]):
        self._store[embedding_id] = {"vector": vector, "metadata": metadata}

    async def search_vectors(self, query_vector: list[float], limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    async def delete_vector(self, embedding_id: str):
        if embedding_id in self._store:
            del self._store[embedding_id]
