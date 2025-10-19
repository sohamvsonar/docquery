"""
OpenAI embedding generation service.
Converts text chunks into dense vector representations for semantic search.
"""

import logging
from typing import List, Dict, Any
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI's API.

    Uses text-embedding-3-small model for cost-effective, high-quality embeddings.
    Embedding dimension: 1536
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize embedding service.

        Args:
            model: OpenAI embedding model to use
        """
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.embedding_dimension = 1536  # text-embedding-3-small dimension

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        OpenAI's API supports up to 2048 texts per request, but we use smaller
        batches to avoid timeouts and handle errors gracefully.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per API call

        Returns:
            List of embedding vectors

        Raises:
            Exception: If batch embedding fails
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [text.strip() for text in texts if text and text.strip()]

        if not valid_texts:
            raise ValueError("No valid texts to embed")

        embeddings = []

        try:
            # Process in batches
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i + batch_size]

                logger.info(f"Processing embedding batch {i // batch_size + 1}: {len(batch)} texts")

                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

            logger.info(f"Generated {len(embeddings)} embeddings successfully")
            return embeddings

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this service.

        Returns:
            Embedding dimension (1536 for text-embedding-3-small)
        """
        return self.embedding_dimension


# Global instance
embedding_service = EmbeddingService()
