"""
Celery tasks for document processing.
Handles asynchronous extraction, chunking, embedding, and indexing of document content.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Document, Chunk
from app.services.document_processor import document_processor
from app.services.embedding import embedding_service
from app.services.vector_index import vector_index
from app.services.cache import cache_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_document")
def process_document_task(self, document_id: int) -> Dict[str, Any]:
    """
    Background task to process an uploaded document.

    Steps:
    1. Load document from database
    2. Extract text (PDF/OCR/Audio)
    3. Chunk text intelligently
    4. Generate embeddings for chunks
    5. Add embeddings to FAISS index
    6. Save chunks to database
    7. Update document status

    Args:
        document_id: Database ID of the document to process

    Returns:
        Dictionary with processing results
    """
    db = SessionLocal()
    result = {
        "document_id": document_id,
        "success": False,
        "chunks_created": 0,
        "embeddings_generated": 0,
        "error": None
    }

    try:
        # Load document from database
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(f"Processing document {document_id}: {document.original_filename}")

        # Update status to processing
        document.status = "processing"
        db.commit()

        # Step 1-3: Process document (extract, chunk)
        processing_result = document_processor.process_document(
            file_path=document.file_path,
            mime_type=document.mime_type
        )

        if not processing_result["success"]:
            raise Exception(processing_result.get("error", "Processing failed"))

        # Step 4: Generate embeddings for all chunks
        chunk_texts = [chunk_data["content"] for chunk_data in processing_result["chunks"]]

        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks")
        embeddings = embedding_service.embed_batch(chunk_texts)

        # Step 5-6: Store chunks in database with embeddings
        chunks_created = 0
        chunk_ids = []
        chunk_embeddings = []

        for chunk_data, embedding in zip(processing_result["chunks"], embeddings):
            chunk = Chunk(
                document_id=document.id,
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data.get("page_number"),
                embedding=embedding,
                embedding_model="text-embedding-3-small",
                has_embedding=True,
                token_count=chunk_data.get("token_count")
            )
            db.add(chunk)
            db.flush()  # Get chunk ID before commit

            chunk_ids.append(chunk.id)
            chunk_embeddings.append(embedding)
            chunks_created += 1

        db.commit()

        # Step 7: Add embeddings to FAISS index
        logger.info(f"Adding {len(chunk_embeddings)} embeddings to FAISS index")
        vector_index.add_vectors(chunk_embeddings, chunk_ids)
        vector_index.save_index()

        # Step 8: Invalidate query cache (new document added)
        # Only invalidate caches for the document owner
        cache_invalidated = cache_service.invalidate_query_cache(f"*{document.owner_id}*")
        logger.info(f"Invalidated {cache_invalidated} cached queries after document upload")

        # Update document status
        document.status = "completed"
        document.processed_at = datetime.utcnow()
        document.error_message = None

        db.commit()

        result["success"] = True
        result["chunks_created"] = chunks_created
        result["embeddings_generated"] = len(embeddings)

        logger.info(
            f"Successfully processed document {document_id}: "
            f"{chunks_created} chunks created, {len(embeddings)} embeddings generated"
        )

    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}", exc_info=True)

        # Update document status to failed
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                document.error_message = str(e)
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {db_error}")

        result["error"] = str(e)
        db.rollback()

    finally:
        db.close()

    return result


@celery_app.task(name="cleanup_failed_documents")
def cleanup_failed_documents_task() -> Dict[str, Any]:
    """
    Periodic task to clean up old failed documents.

    Returns:
        Dictionary with cleanup results
    """
    db = SessionLocal()
    result = {
        "cleaned_up": 0,
        "error": None
    }

    try:
        from datetime import timedelta

        # Find failed documents older than 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        failed_docs = db.query(Document).filter(
            Document.status == "failed",
            Document.created_at < cutoff_date
        ).all()

        for doc in failed_docs:
            # Optionally delete the file
            # os.remove(doc.file_path)

            # Delete document (cascades to chunks)
            db.delete(doc)
            result["cleaned_up"] += 1

        db.commit()

        logger.info(f"Cleaned up {result['cleaned_up']} failed documents")

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        result["error"] = str(e)
        db.rollback()

    finally:
        db.close()

    return result
