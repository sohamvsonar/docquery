"""
Hybrid search service combining vector (FAISS) and full-text (PostgreSQL) search.
Implements retrieval with reciprocal rank fusion (RRF) for combining results.
"""

import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.services.embedding import embedding_service
from app.services.vector_index import vector_index
from app.services.cache import cache_service

logger = logging.getLogger(__name__)


class SearchService:
    """
    Hybrid search combining semantic (FAISS) and lexical (PostgreSQL FTS) search.

    Search strategies:
    - Vector search: Semantic similarity using embeddings
    - Full-text search: Keyword matching with BM25-like ranking
    - Hybrid: Combine both using Reciprocal Rank Fusion (RRF)

    Features caching for performance optimization.
    """

    def __init__(self):
        """Initialize search service."""
        self.embedding_service = embedding_service
        self.vector_index = vector_index
        self.cache = cache_service

    def vector_search(
        self,
        query: str,
        k: int = 10,
        db: Session = None,
        user_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using FAISS vector index.

        Args:
            query: Search query text
            k: Number of results to return
            db: Database session
            user_id: Optional user ID to filter results by ownership

        Returns:
            List of search results with chunk info and scores
        """
        if not query or not query.strip():
            return []

        try:
            # Check embedding cache first
            query_embedding = self.cache.get_embedding_cache(query)

            if query_embedding is None:
                # Generate embedding for query
                logger.info(f"Generating embedding for query: {query[:50]}...")
                query_embedding = self.embedding_service.embed_text(query)

                # Cache the embedding
                self.cache.set_embedding_cache(query, query_embedding)
            else:
                logger.info(f"Using cached embedding for query: {query[:50]}...")

            # Search FAISS index
            logger.info(f"Searching FAISS index for top {k} results")
            faiss_results = self.vector_index.search(query_embedding, k=k)

            if not faiss_results:
                logger.info("No results found in FAISS index")
                return []

            # Get chunk IDs and distances
            chunk_ids = [chunk_id for chunk_id, _ in faiss_results]
            distances = {chunk_id: distance for chunk_id, distance in faiss_results}

            # Fetch chunk details from database
            if db:
                # Build query for chunks
                chunks_query = db.query(Chunk).filter(Chunk.id.in_(chunk_ids))

                # Filter by user ownership if user_id provided and not admin
                if user_id:
                    from app.models import User
                    user = db.query(User).filter(User.id == user_id).first()

                    # Only filter for non-admin users
                    if user and not user.is_admin:
                        chunks_query = chunks_query.join(Document).filter(Document.owner_id == user_id)

                chunks = chunks_query.all()

                # Build results with chunk info
                results = []
                for chunk in chunks:
                    distance = distances[chunk.id]
                    # Convert L2 distance to similarity score (0-1 range)
                    # Lower distance = higher similarity
                    similarity = 1 / (1 + distance)

                    results.append({
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "score": similarity,
                        "distance": distance,
                        "search_type": "vector"
                    })

                # Sort by similarity (highest first)
                results.sort(key=lambda x: x["score"], reverse=True)

                logger.info(f"Vector search returned {len(results)} results")
                return results
            else:
                # Return just chunk IDs and scores if no DB session
                return [
                    {
                        "chunk_id": chunk_id,
                        "score": 1 / (1 + distance),
                        "distance": distance,
                        "search_type": "vector"
                    }
                    for chunk_id, distance in faiss_results
                ]

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return []

    def fulltext_search(
        self,
        query: str,
        k: int = 10,
        db: Session = None,
        user_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        Perform full-text search using PostgreSQL FTS.

        Uses ts_rank for relevance scoring with BM25-like behavior.

        Args:
            query: Search query text
            k: Number of results to return
            db: Database session (required)
            user_id: Optional user ID to filter results by ownership

        Returns:
            List of search results with chunk info and scores
        """
        if not db:
            logger.error("Database session required for full-text search")
            return []

        if not query or not query.strip():
            return []

        try:
            # Use the query as-is, plainto_tsquery handles it properly
            logger.info(f"Performing full-text search for: {query}")

            # Check if we need to filter by user ownership
            if user_id:
                from app.models import User
                user = db.query(User).filter(User.id == user_id).first()

                # Filter for non-admin users
                if user and not user.is_admin:
                    # PostgreSQL full-text search query WITH user filtering
                    search_sql = text("""
                        SELECT
                            c.id,
                            c.document_id,
                            c.content,
                            c.chunk_index,
                            c.page_number,
                            ts_rank(to_tsvector(c.content), plainto_tsquery(:query)) as rank
                        FROM chunks c
                        INNER JOIN documents d ON c.document_id = d.id
                        WHERE to_tsvector(c.content) @@ plainto_tsquery(:query)
                          AND d.owner_id = :user_id
                        ORDER BY rank DESC
                        LIMIT :limit;
                    """)

                    result = db.execute(search_sql, {
                        "query": query.strip(),
                        "user_id": user_id,
                        "limit": k
                    })
                else:
                    # Admin - no filtering needed
                    search_sql = text("""
                        SELECT
                            c.id,
                            c.document_id,
                            c.content,
                            c.chunk_index,
                            c.page_number,
                            ts_rank(to_tsvector(c.content), plainto_tsquery(:query)) as rank
                        FROM chunks c
                        WHERE to_tsvector(c.content) @@ plainto_tsquery(:query)
                        ORDER BY rank DESC
                        LIMIT :limit;
                    """)

                    result = db.execute(search_sql, {"query": query.strip(), "limit": k})
            else:
                # No user_id provided - search all chunks
                search_sql = text("""
                    SELECT
                        c.id,
                        c.document_id,
                        c.content,
                        c.chunk_index,
                        c.page_number,
                        ts_rank(to_tsvector(c.content), plainto_tsquery(:query)) as rank
                    FROM chunks c
                    WHERE to_tsvector(c.content) @@ plainto_tsquery(:query)
                    ORDER BY rank DESC
                    LIMIT :limit;
                """)

                result = db.execute(search_sql, {"query": query.strip(), "limit": k})

            rows = result.fetchall()

            results = []
            for row in rows:
                results.append({
                    "chunk_id": row[0],
                    "document_id": row[1],
                    "content": row[2],
                    "chunk_index": row[3],
                    "page_number": row[4],
                    "score": float(row[5]),
                    "search_type": "fulltext"
                })

            logger.info(f"Full-text search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Full-text search failed: {e}", exc_info=True)
            return []

    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        alpha: float = 0.5,
        db: Session = None,
        user_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search using Reciprocal Rank Fusion (RRF).

        Combines vector and full-text search results using RRF algorithm.

        Args:
            query: Search query text
            k: Number of results to return
            alpha: Weight for vector search (0-1, higher = more vector weight)
            db: Database session
            user_id: Optional user ID to filter results by ownership

        Returns:
            List of search results ranked by RRF score
        """
        if not db:
            logger.error("Database session required for hybrid search")
            return []

        # Fetch more results from each method for better fusion
        fetch_k = k * 2

        # Perform both searches with user filtering
        vector_results = self.vector_search(query, k=fetch_k, db=db, user_id=user_id)
        fulltext_results = self.fulltext_search(query, k=fetch_k, db=db, user_id=user_id)

        logger.info(
            f"Hybrid search: {len(vector_results)} vector results, "
            f"{len(fulltext_results)} full-text results"
        )

        # Reciprocal Rank Fusion (RRF)
        # Score = alpha * (1 / (rank_vector + 60)) + (1 - alpha) * (1 / (rank_fulltext + 60))
        # Constant 60 is standard in RRF
        rrf_scores = {}

        # Process vector results
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result["chunk_id"]
            rrf_scores[chunk_id] = {
                "chunk_id": chunk_id,
                "content": result["content"],
                "document_id": result["document_id"],
                "chunk_index": result["chunk_index"],
                "page_number": result["page_number"],
                "vector_score": result["score"],
                "vector_rank": rank,
                "fulltext_score": 0,
                "fulltext_rank": None,
                "rrf_score": alpha * (1 / (rank + 60))
            }

        # Process full-text results
        for rank, result in enumerate(fulltext_results, start=1):
            chunk_id = result["chunk_id"]

            if chunk_id in rrf_scores:
                # Chunk appears in both results
                rrf_scores[chunk_id]["fulltext_score"] = result["score"]
                rrf_scores[chunk_id]["fulltext_rank"] = rank
                rrf_scores[chunk_id]["rrf_score"] += (1 - alpha) * (1 / (rank + 60))
            else:
                # Chunk only in full-text results
                rrf_scores[chunk_id] = {
                    "chunk_id": chunk_id,
                    "content": result["content"],
                    "document_id": result["document_id"],
                    "chunk_index": result["chunk_index"],
                    "page_number": result["page_number"],
                    "vector_score": 0,
                    "vector_rank": None,
                    "fulltext_score": result["score"],
                    "fulltext_rank": rank,
                    "rrf_score": (1 - alpha) * (1 / (rank + 60))
                }

        # If no results from RRF fusion, fallback to fulltext only
        if not rrf_scores:
            logger.warning("No results from hybrid search, falling back to fulltext only")
            if fulltext_results:
                return fulltext_results[:k]
            return []

        # Sort by RRF score and return top k
        results = sorted(rrf_scores.values(), key=lambda x: x["rrf_score"], reverse=True)[:k]

        logger.info(f"Hybrid search returned {len(results)} results after RRF fusion")

        # Add search type and final score
        for result in results:
            result["search_type"] = "hybrid"
            result["score"] = result["rrf_score"]

        return results

    def search(
        self,
        query: str,
        k: int = 10,
        search_type: str = "hybrid",
        alpha: float = 0.5,
        user_id: int = None,
        db: Session = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Main search interface supporting multiple search types with caching.

        Args:
            query: Search query text
            k: Number of results to return
            search_type: "vector", "fulltext", or "hybrid"
            alpha: Weight for vector search in hybrid mode (0-1)
            user_id: Optional user ID for access control
            db: Database session
            use_cache: Whether to use query cache (default: True)

        Returns:
            List of search results
        """
        if not query or not query.strip():
            return []

        logger.info(f"Search request: query='{query[:50]}...', type={search_type}, k={k}")

        # Check query cache first (if enabled and user_id provided)
        if use_cache and user_id is not None:
            cached_results = self.cache.get_query_cache(
                query=query,
                k=k,
                search_type=search_type,
                alpha=alpha,
                user_id=user_id
            )

            if cached_results is not None:
                logger.info(f"Returning {len(cached_results)} cached results")
                return cached_results

        # Perform search based on type (user filtering is done within each search method)
        if search_type == "vector":
            results = self.vector_search(query, k=k, db=db, user_id=user_id)
        elif search_type == "fulltext":
            results = self.fulltext_search(query, k=k, db=db, user_id=user_id)
        elif search_type == "hybrid":
            results = self.hybrid_search(query, k=k, alpha=alpha, db=db, user_id=user_id)
        else:
            logger.error(f"Unknown search type: {search_type}")
            return []

        # User access control is now done within individual search methods
        # No need for additional filtering here

        # Enrich results with document metadata
        if db:
            results = self._enrich_with_document_info(results, db)

        # Cache the results (if enabled and user_id provided)
        if use_cache and user_id is not None and results:
            self.cache.set_query_cache(
                query=query,
                k=k,
                search_type=search_type,
                alpha=alpha,
                user_id=user_id,
                results=results
            )

        return results

    def _filter_by_user_access(
        self,
        results: List[Dict[str, Any]],
        user_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Filter results based on user access (only own documents unless admin).

        Args:
            results: Search results
            user_id: User ID
            db: Database session

        Returns:
            Filtered results
        """
        from app.models import User

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return []

        # Admins can see all results
        if user.is_admin:
            return results

        # Filter to only user's documents
        document_ids = [r["document_id"] for r in results]
        user_docs = db.query(Document.id).filter(
            Document.id.in_(document_ids),
            Document.owner_id == user_id
        ).all()

        user_doc_ids = {doc.id for doc in user_docs}

        filtered_results = [r for r in results if r["document_id"] in user_doc_ids]

        logger.info(
            f"Filtered {len(results)} results to {len(filtered_results)} "
            f"based on user {user_id} access"
        )

        return filtered_results

    def _enrich_with_document_info(
        self,
        results: List[Dict[str, Any]],
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Add document metadata to search results.

        Args:
            results: Search results
            db: Database session

        Returns:
            Enriched results
        """
        if not results:
            return results

        # Get unique document IDs
        document_ids = list(set(r["document_id"] for r in results))

        # Fetch document metadata
        documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
        doc_map = {doc.id: doc for doc in documents}

        # Enrich results
        for result in results:
            doc = doc_map.get(result["document_id"])
            if doc:
                result["document_filename"] = doc.original_filename
                result["document_owner_id"] = doc.owner_id

        return results


# Global instance
search_service = SearchService()
