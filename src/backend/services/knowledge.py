from agno.knowledge.embedder.azure_openai import AzureOpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb.lance_db import LanceDb
from agno.vectordb.search import SearchType
from loguru import logger

from core.config import settings


class KnowledgeService:
    """Connects to an existing LanceDB knowledge base for RAG retrieval.

    The knowledge base must be created first by running:
        uv run python -m scripts.ingest_knowledge
    """

    def __init__(self):
        self.knowledge: Knowledge | None = None

    def _get_embedder(self) -> AzureOpenAIEmbedder:
        return AzureOpenAIEmbedder(
            azure_endpoint=settings.azure_openai_embed_endpoint,
            api_key=settings.azure_openai_embed_api_key,
            azure_deployment=settings.azure_openai_embed_deployment,
            dimensions=settings.azure_openai_embed_dimensions,
        )

    async def initialize(self) -> None:
        """Connect to the existing LanceDB knowledge base."""
        embedder = self._get_embedder()
        vectorstore = LanceDb(
            table_name="knowledge",
            uri=settings.lancedb_path,
            embedder=embedder,
            search_type=SearchType.hybrid,
        )

        if not vectorstore.exists():
            logger.warning(
                "Knowledge base table not found at {} — run "
                "'uv run python -m scripts.ingest_knowledge' to create it",
                settings.lancedb_path,
            )
            return

        self.knowledge = Knowledge(vector_db=vectorstore, max_results=5)
        logger.info("Connected to RAG knowledge base")

    def get_knowledge(self) -> Knowledge | None:
        """Return the Knowledge instance for use with Agno agents."""
        return self.knowledge


# Singleton instance
knowledge_service = KnowledgeService()
