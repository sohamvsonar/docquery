"""
Query routes for document search and retrieval.
Implements hybrid search (FAISS + PostgreSQL FTS) with query logging.
"""

import uuid
import time
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import QueryRequest, QueryResponse, QueryResultItem
from app.auth import get_current_user
from app.models import User, QueryLog, Document
from app.services.search import search_service

router = APIRouter(prefix="/query", tags=["Query"])
logger = logging.getLogger(__name__)


@router.post("", response_model=QueryResponse, status_code=status.HTTP_200_OK)
def query_documents(
    query_data: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query documents using hybrid search.

    Combines:
    - FAISS semantic search (vector similarity)
    - PostgreSQL full-text search (BM25-like keyword matching)
    - Reciprocal Rank Fusion (RRF) for result merging

    Supports three search modes:
    - "hybrid" (default): Combines vector + full-text search
    - "vector": Semantic search only
    - "fulltext": Keyword search only

    Args:
        query_data: Query request with:
            - q: Query text (required)
            - k: Number of results (default: 5)
            - search_type: "hybrid", "vector", or "fulltext" (default: "hybrid")
            - alpha: Vector weight for hybrid search 0-1 (default: 0.5)
        current_user: Authenticated user
        db: Database session

    Returns:
        Search results with chunk content, document info, and relevance scores

    Raises:
        HTTPException 400: Invalid query
    """
    start_time = time.time()

    # Validate query
    if not query_data.q or not query_data.q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query text cannot be empty"
        )

    # Generate unique query ID
    query_id = str(uuid.uuid4())

    logger.info(
        f"Query {query_id} from user {current_user.id}: "
        f"'{query_data.q[:50]}...' (type={query_data.search_type}, k={query_data.k})"
    )

    try:
        # Validate document access if document_id is provided
        if query_data.document_id:
            document = db.query(Document).filter(Document.id == query_data.document_id).first()

            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {query_data.document_id} not found"
                )

            # Check if user has access to this document
            if document.owner_id != current_user.id and not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to query this document"
                )

            logger.info(f"Context-aware query for document {query_data.document_id}: {document.original_filename}")

        # Perform search (with optional document context)
        search_results = search_service.search(
            query=query_data.q,
            k=query_data.k,
            search_type=query_data.search_type,
            alpha=query_data.alpha,
            user_id=current_user.id,
            db=db,
            document_id=query_data.document_id
        )

        # Convert to response format
        results = []
        result_metadata = []

        for rank, result in enumerate(search_results, start=1):
            results.append(QueryResultItem(
                chunk_id=result["chunk_id"],
                document_id=result["document_id"],
                document_filename=result.get("document_filename", "Unknown"),
                content=result["content"],
                chunk_index=result["chunk_index"],
                page_number=result.get("page_number"),
                score=result["score"],
                rank=rank
            ))

            # Store metadata for query log
            result_metadata.append({
                "chunk_id": result["chunk_id"],
                "document_id": result["document_id"],
                "score": result["score"],
                "rank": rank,
                "search_type": result.get("search_type")
            })

        result_count = len(results)

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Query {query_id} completed: {result_count} results in {response_time_ms:.2f}ms"
        )

        # Log query for analytics
        query_log = QueryLog(
            query_id=query_id,
            user_id=current_user.id,
            query_text=query_data.q,
            k=query_data.k,
            result_count=result_count,
            results=result_metadata,
            response_time_ms=response_time_ms,
            created_at=datetime.utcnow()
        )

        db.add(query_log)
        db.commit()

        return QueryResponse(
            query_id=query_id,
            query_text=query_data.q,
            results=results,
            result_count=result_count,
            response_time_ms=response_time_ms
        )

    except Exception as e:
        logger.error(f"Query {query_id} failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
