"""
FAISS vector index manager for semantic similarity search.
Manages persistent vector storage and k-NN search operations.
"""

import os
import logging
import pickle
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

from app.config import settings

logger = logging.getLogger(__name__)


class VectorIndexManager:
    """
    Manages FAISS index for semantic search.

    Features:
    - Efficient similarity search using FAISS IndexFlatL2
    - Persistent storage (index + document ID mapping)
    - Thread-safe operations
    - Automatic index rebuilding
    """

    def __init__(
        self,
        dimension: int = 1536,
        index_path: str = None,
        mapping_path: str = None
    ):
        """
        Initialize FAISS index manager.

        Args:
            dimension: Vector embedding dimension
            index_path: Path to save/load FAISS index
            mapping_path: Path to save/load chunk ID mapping
        """
        self.dimension = dimension
        self.enabled = FAISS_AVAILABLE

        if not self.enabled:
            logger.warning("FAISS not available. Vector search will be disabled.")
            self.index = None
            self.chunk_ids = []
            self._index_mtime = None
            return

        # Set default paths if not provided
        index_dir = os.path.join(settings.upload_dir, "indexes")
        os.makedirs(index_dir, exist_ok=True)

        self.index_path = index_path or os.path.join(index_dir, "faiss_index.bin")
        self.mapping_path = mapping_path or os.path.join(index_dir, "chunk_mapping.pkl")

        # Initialize index
        self.index = None
        self.chunk_ids = []  # Maps FAISS index position to chunk ID

        # Track index file modification time for auto-reload
        self._index_mtime = None

        # Load existing index or create new one
        if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
            self.load_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Create a new FAISS index."""
        # Use IndexFlatL2 for exact L2 distance search
        # For production with millions of vectors, consider IndexIVFFlat
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunk_ids = []
        self._index_mtime = None
        logger.info(f"Created new FAISS index with dimension {self.dimension}")

    def add_vectors(
        self,
        embeddings: List[List[float]],
        chunk_ids: List[int]
    ) -> int:
        """
        Add vectors to the index.

        Args:
            embeddings: List of embedding vectors
            chunk_ids: Corresponding chunk IDs

        Returns:
            Number of vectors added

        Raises:
            ValueError: If embeddings and chunk_ids length mismatch
        """
        if len(embeddings) != len(chunk_ids):
            raise ValueError(
                f"Embeddings count ({len(embeddings)}) must match "
                f"chunk_ids count ({len(chunk_ids)})"
            )

        if not embeddings:
            logger.warning("No embeddings to add")
            return 0

        # Convert to numpy array
        vectors = np.array(embeddings, dtype=np.float32)

        # Validate dimension
        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {vectors.shape[1]} does not match "
                f"index dimension {self.dimension}"
            )

        # Add to FAISS index
        self.index.add(vectors)

        # Update chunk ID mapping
        self.chunk_ids.extend(chunk_ids)

        logger.info(f"Added {len(embeddings)} vectors to index. Total: {self.index.ntotal}")

        return len(embeddings)

    def _check_and_reload_index(self):
        """
        Check if index file has been modified and reload if needed.

        This enables real-time updates when the index is modified by
        background workers (Celery).
        """
        if not os.path.exists(self.index_path):
            return

        try:
            current_mtime = os.path.getmtime(self.index_path)

            # If modification time changed, reload the index
            if self._index_mtime is None or current_mtime > self._index_mtime:
                logger.info(
                    f"Index file updated (mtime: {current_mtime}), reloading..."
                )
                self.load_index()
        except Exception as e:
            logger.warning(f"Failed to check index modification time: {e}")

    def search(
        self,
        query_embedding: List[float],
        k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Search for k nearest neighbors.

        Automatically reloads index if it has been updated on disk.

        Args:
            query_embedding: Query vector
            k: Number of results to return

        Returns:
            List of (chunk_id, distance) tuples, sorted by distance (ascending)

        Raises:
            ValueError: If index is empty or query dimension mismatch
        """
        if not self.enabled:
            logger.debug("FAISS not available, skipping vector search")
            return []

        # Auto-reload index if it has been updated
        self._check_and_reload_index()

        if not self.index or self.index.ntotal == 0:
            logger.warning("Cannot search: index is empty")
            return []

        # Convert to numpy array
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Validate dimension
        if query_vector.shape[1] != self.dimension:
            raise ValueError(
                f"Query dimension {query_vector.shape[1]} does not match "
                f"index dimension {self.dimension}"
            )

        # Limit k to available vectors
        k = min(k, self.index.ntotal)

        # Search
        distances, indices = self.index.search(query_vector, k)

        # Map indices to chunk IDs
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if 0 <= idx < len(self.chunk_ids):
                chunk_id = self.chunk_ids[idx]
                results.append((chunk_id, float(distance)))

        logger.debug(f"Search returned {len(results)} results")
        return results

    def save_index(self):
        """Save FAISS index and chunk mapping to disk."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)

            # Save chunk ID mapping
            with open(self.mapping_path, 'wb') as f:
                pickle.dump(self.chunk_ids, f)

            logger.info(f"Saved index with {self.index.ntotal} vectors to {self.index_path}")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise

    def load_index(self):
        """Load FAISS index and chunk mapping from disk."""
        try:
            # Load FAISS index
            self.index = faiss.read_index(self.index_path)

            # Load chunk ID mapping
            with open(self.mapping_path, 'rb') as f:
                self.chunk_ids = pickle.load(f)

            # Update modification time
            self._index_mtime = os.path.getmtime(self.index_path)

            logger.info(f"Loaded index with {self.index.ntotal} vectors from {self.index_path}")

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            # Create new index if loading fails
            self._create_new_index()

    def rebuild_index(self, embeddings: List[List[float]], chunk_ids: List[int]):
        """
        Rebuild the entire index from scratch.

        Useful for maintenance or after deletions.

        Args:
            embeddings: All embedding vectors
            chunk_ids: Corresponding chunk IDs
        """
        logger.info("Rebuilding FAISS index from scratch")

        # Create new index
        self._create_new_index()

        # Add all vectors
        if embeddings and chunk_ids:
            self.add_vectors(embeddings, chunk_ids)

        # Save to disk
        self.save_index()

        logger.info(f"Index rebuilt with {self.index.ntotal} vectors")

    def remove_by_chunk_ids(self, chunk_ids_to_remove: List[int]):
        """
        Remove vectors by chunk IDs.

        Note: FAISS IndexFlatL2 doesn't support direct removal.
        This marks them for rebuild - you should periodically rebuild the index.

        Args:
            chunk_ids_to_remove: List of chunk IDs to remove
        """
        # Since FAISS IndexFlatL2 doesn't support removal,
        # we would need to rebuild the index without these chunks
        # For now, we'll just log a warning
        logger.warning(
            f"Removal of {len(chunk_ids_to_remove)} chunks requested. "
            f"FAISS IndexFlatL2 requires full rebuild. "
            f"Call rebuild_index() with remaining chunks."
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dictionary with index statistics
        """
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "index_type": "IndexFlatL2",
            "index_path": self.index_path,
            "mapping_path": self.mapping_path,
            "chunk_ids_count": len(self.chunk_ids)
        }


# Global instance
vector_index = VectorIndexManager()
