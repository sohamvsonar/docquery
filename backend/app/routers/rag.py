"""
RAG (Retrieval-Augmented Generation) routes.
Generates answers with citations using GPT-4 and retrieved context.
"""

import uuid
import time
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RAGRequest, RAGResponse, CitationItem, QueryResultItem
from app.auth import get_current_user
from app.models import User, QueryLog, Document
from app.services.search import search_service
from app.services.generator import rag_generator
from app.services.citation_tracker import citation_tracker

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = logging.getLogger(__name__)


@router.post("/answer", response_model=RAGResponse, status_code=status.HTTP_200_OK)
def generate_answer(
    rag_data: RAGRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an answer to a question using RAG (non-streaming).

    Process:
    1. Retrieve relevant context using hybrid search
    2. Format context with source references
    3. Generate answer using GPT-4 with citations
    4. Extract and validate citations
    5. Return answer with source metadata

    Args:
        rag_data: RAG request with question and parameters
        current_user: Authenticated user
        db: Database session

    Returns:
        Generated answer with citations and sources

    Raises:
        HTTPException 400: Invalid request
        HTTPException 500: Generation failed
    """
    start_time = time.time()

    # Validate question
    if not rag_data.q or not rag_data.q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )

    # Generate unique query ID
    query_id = str(uuid.uuid4())

    logger.info(
        f"RAG request {query_id} from user {current_user.id}: "
        f"'{rag_data.q[:50]}...' (model={rag_data.model}, k={rag_data.k})"
    )

    try:
        # Validate document access if document_id is provided
        if rag_data.document_id:
            document = db.query(Document).filter(Document.id == rag_data.document_id).first()

            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {rag_data.document_id} not found"
                )

            # Check if user has access to this document
            if document.owner_id != current_user.id and not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to query this document"
                )

            logger.info(f"Context-aware RAG for document {rag_data.document_id}: {document.original_filename}")

        # Step 1: Retrieve context using search (with optional document context)
        search_start = time.time()

        search_results = search_service.search(
            query=rag_data.q,
            k=rag_data.k,
            search_type=rag_data.search_type,
            alpha=rag_data.alpha,
            user_id=current_user.id,
            db=db,
            document_id=rag_data.document_id
        )

        search_time_ms = (time.time() - search_start) * 1000

        logger.info(f"Retrieved {len(search_results)} context chunks in {search_time_ms:.2f}ms")

        if not search_results:
            # No relevant documents found
            return RAGResponse(
                query_id=query_id,
                query_text=rag_data.q,
                answer="I don't have any relevant documents to answer this question. Please upload documents related to your query first.",
                citations=[],
                sources=[],
                model=rag_data.model,
                usage={},
                response_time_ms=(time.time() - start_time) * 1000,
                search_time_ms=search_time_ms,
                generation_time_ms=0
            )

        # Step 2 & 3: Generate answer with GPT-4
        generation_start = time.time()

        generation_result = rag_generator.generate(
            query=rag_data.q,
            search_results=search_results,
            model=rag_data.model,
            temperature=rag_data.temperature,
            max_tokens=rag_data.max_tokens
        )

        generation_time_ms = (time.time() - generation_start) * 1000

        answer = generation_result["answer"]

        logger.info(
            f"Generated answer: {len(answer)} chars, "
            f"{generation_result['usage'].get('total_tokens', 0)} tokens in {generation_time_ms:.2f}ms"
        )

        # Step 4: Extract and format citations
        citations_data = citation_tracker.map_citations_to_sources(answer, search_results)

        citations = [
            CitationItem(
                number=cit["number"],
                chunk_id=cit["chunk_id"],
                document_id=cit["document_id"],
                document_filename=cit["document_filename"],
                page_number=cit.get("page_number"),
                chunk_index=cit["chunk_index"],
                score=cit.get("score", 0.0),
                content_preview=cit["content_preview"]
            )
            for cit in citations_data
        ]

        # Format sources
        sources = [
            QueryResultItem(
                chunk_id=result["chunk_id"],
                document_id=result["document_id"],
                document_filename=result.get("document_filename", "Unknown"),
                content=result["content"],
                chunk_index=result["chunk_index"],
                page_number=result.get("page_number"),
                score=result["score"],
                rank=idx + 1
            )
            for idx, result in enumerate(search_results)
        ]

        # Calculate total response time
        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"RAG request {query_id} completed: "
            f"{len(citations)} citations, {response_time_ms:.2f}ms total"
        )

        # Log query for analytics
        query_log = QueryLog(
            query_id=query_id,
            user_id=current_user.id,
            query_text=rag_data.q,
            k=rag_data.k,
            result_count=len(search_results),
            results=[
                {
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "score": r["score"],
                    "rank": idx + 1
                }
                for idx, r in enumerate(search_results)
            ],
            response_time_ms=response_time_ms,
            created_at=datetime.utcnow()
        )

        db.add(query_log)
        db.commit()

        return RAGResponse(
            query_id=query_id,
            query_text=rag_data.q,
            answer=answer,
            citations=citations,
            sources=sources,
            model=generation_result["model"],
            usage=generation_result["usage"],
            response_time_ms=response_time_ms,
            search_time_ms=search_time_ms,
            generation_time_ms=generation_time_ms
        )

    except Exception as e:
        logger.error(f"RAG request {query_id} failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {str(e)}"
        )


@router.post("/answer/stream")
async def generate_answer_stream(
    rag_data: RAGRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an answer to a question using RAG with streaming.

    Returns answer chunks in real-time as they're generated.

    Response format: Server-Sent Events (SSE)
    - Each chunk is sent as `data: {json}`
    - Final message includes complete metadata

    Args:
        rag_data: RAG request with question and parameters
        current_user: Authenticated user
        db: Database session

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException 400: Invalid request
        HTTPException 500: Generation failed
    """
    import json

    # Validate question
    if not rag_data.q or not rag_data.q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )

    query_id = str(uuid.uuid4())

    logger.info(
        f"RAG streaming request {query_id} from user {current_user.id}: "
        f"'{rag_data.q[:50]}...'"
    )

    async def event_generator():
        """Generate SSE events for streaming response."""
        start_time = time.time()

        try:
            # Validate document access if document_id is provided
            if rag_data.document_id:
                document = db.query(Document).filter(Document.id == rag_data.document_id).first()

                if not document:
                    yield f"data: {json.dumps({{'type': 'error', 'message': f'Document with ID {rag_data.document_id} not found'}})}\n\n"
                    return

                # Check if user has access to this document
                if document.owner_id != current_user.id and not current_user.is_admin:
                    yield f"data: {json.dumps({{'type': 'error', 'message': 'Not authorized to query this document'}})}\n\n"
                    return

                logger.info(f"Context-aware RAG streaming for document {rag_data.document_id}: {document.original_filename}")

            # Step 1: Retrieve context (with optional document context)
            search_start = time.time()

            # Send search status
            search_msg = 'Searching document...' if rag_data.document_id else 'Searching documents...'
            yield f"data: {json.dumps({'type': 'status', 'message': search_msg})}\n\n"

            search_results = search_service.search(
                query=rag_data.q,
                k=rag_data.k,
                search_type=rag_data.search_type,
                alpha=rag_data.alpha,
                user_id=current_user.id,
                db=db,
                document_id=rag_data.document_id
            )

            search_time_ms = (time.time() - search_start) * 1000

            # Send search results metadata
            yield f"data: {json.dumps({'type': 'search_complete', 'sources_found': len(search_results), 'time_ms': search_time_ms})}\n\n"

            if not search_results:
                # Send as answer_chunk so frontend displays it
                msg = {"type": "answer_chunk", "content": "I don't have any relevant documents to answer this question. Please upload documents related to your query first."}
                yield f"data: {json.dumps(msg)}\n\n"

                # Send empty citations
                yield f"data: {json.dumps({'type': 'citations', 'query_id': query_id, 'citations': []})}\n\n"

                # Send done event
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Send sources
            sources_data = [
                {
                    "chunk_id": r["chunk_id"],
                    "document_filename": r.get("document_filename", "Unknown"),
                    "page_number": r.get("page_number")
                }
                for r in search_results
            ]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"

            # Step 2: Generate answer with streaming
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating answer...'})}\n\n"

            generation_start = time.time()
            full_answer = ""

            for chunk in rag_generator.generate_stream(
                query=rag_data.q,
                search_results=search_results,
                model=rag_data.model,
                temperature=rag_data.temperature,
                max_tokens=rag_data.max_tokens
            ):
                full_answer += chunk
                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': chunk})}\n\n"

            generation_time_ms = (time.time() - generation_start) * 1000

            # Step 3: Send citations
            citations_data = citation_tracker.map_citations_to_sources(full_answer, search_results)

            citations = [
                {
                    "number": cit["number"],
                    "document_filename": cit["document_filename"],
                    "page_number": cit.get("page_number"),
                    "content_preview": cit["content_preview"]
                }
                for cit in citations_data
            ]

            yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

            # Send completion metadata
            response_time_ms = (time.time() - start_time) * 1000

            metadata = {
                "type": "done",
                "query_id": query_id,
                "response_time_ms": response_time_ms,
                "search_time_ms": search_time_ms,
                "generation_time_ms": generation_time_ms
            }

            yield f"data: {json.dumps(metadata)}\n\n"

            logger.info(f"RAG streaming request {query_id} completed in {response_time_ms:.2f}ms")

        except Exception as e:
            logger.error(f"RAG streaming failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
