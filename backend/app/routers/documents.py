"""
Document upload and management routes.
Handles file uploads, storage, and metadata persistence.
"""

import os
import uuid
import logging
import mimetypes
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UploadResponse, DocumentResponse, ChunkResponse, DocumentListResponse
from app.auth import get_current_user
from app.models import User, Document, Chunk
from app.config import settings
from app.tasks.document_tasks import process_document_task

router = APIRouter(prefix="/upload", tags=["Documents"])


def detect_mime_type(filename: str, content_type: Optional[str] = None) -> str:
    """
    Detect MIME type from filename with fallback to content_type.

    Args:
        filename: Original filename
        content_type: Content-Type from upload (may be incorrect)

    Returns:
        Detected MIME type string
    """
    # Normalize browser-provided MIME types that are often incorrect
    mime_type_overrides = {
        'application/vnd.ms-excel': 'text/csv',  # Excel files are often sent as CSV
    }

    # If browser sent a known incorrect MIME type, check file extension
    if content_type in mime_type_overrides:
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.csv':
            content_type = mime_type_overrides[content_type]

    # Try to detect from filename extension first
    mime_type, _ = mimetypes.guess_type(filename)

    if not mime_type or mime_type == 'application/octet-stream':
        # Use extension mapping for common file types
        ext = os.path.splitext(filename)[1].lower()
        ext_to_mime = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            '.gif': 'image/gif',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/m4a',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.xml': 'text/xml'
        }
        mime_type = ext_to_mime.get(ext)

    # Fallback to browser-provided content_type if still not detected
    if not mime_type and content_type and content_type != 'application/octet-stream':
        mime_type = content_type

    # Final fallback
    return mime_type or 'application/octet-stream'


def save_upload_file(upload_file: UploadFile, destination: str) -> int:
    """
    Save an uploaded file to disk.

    Args:
        upload_file: FastAPI UploadFile object
        destination: Destination file path

    Returns:
        File size in bytes
    """
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    file_size = 0
    with open(destination, "wb") as buffer:
        while True:
            chunk = upload_file.file.read(8192)  # Read in 8KB chunks
            if not chunk:
                break
            file_size += len(chunk)
            buffer.write(chunk)

    return file_size


@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document for processing.

    Accepts PDF, DOCX, image, audio, and text files. The file is saved to disk and a database
    record is created. Processing (OCR, extraction, embedding) will be done
    asynchronously in background tasks.

    Args:
        file: Uploaded file
        current_user: Authenticated user
        db: Database session

    Returns:
        Job information with job_id and status

    Raises:
        HTTPException 400: Invalid file
        HTTPException 413: File too large
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    # Check file size (read first chunk to estimate)
    # Note: For production, implement proper streaming size check
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size} bytes"
        )

    # Generate unique job_id and filename
    job_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{job_id}{file_extension}"

    # Create user-specific directory for secure file storage
    # Structure: /app/uploads/user_{user_id}/
    user_upload_dir = os.path.join(settings.upload_dir, f"user_{current_user.id}")
    os.makedirs(user_upload_dir, exist_ok=True)

    # Set directory permissions (owner read/write/execute only)
    os.chmod(user_upload_dir, 0o700)

    # Save file to disk in user-specific directory
    file_path = os.path.join(user_upload_dir, unique_filename)

    try:
        actual_size = save_upload_file(file, file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Detect MIME type from filename (more reliable than browser content_type)
    detected_mime_type = detect_mime_type(file.filename, file.content_type)

    # Create database record
    document = Document(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=actual_size,
        mime_type=detected_mime_type,
        status="pending",
        job_id=job_id,
        owner_id=current_user.id,
        created_at=datetime.utcnow()
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # Trigger background processing task
    try:
        process_document_task.delay(document.id)
        logger = logging.getLogger(__name__)
        logger.info(f"Queued document {document.id} for processing")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to queue document for processing: {e}")
        # Don't fail the upload, document can be reprocessed later

    return UploadResponse(
        job_id=job_id,
        document_id=document.id,
        filename=unique_filename,
        original_filename=file.filename,
        status="pending",
        file_size=actual_size,
        message="File uploaded successfully. Processing will begin shortly."
    )


@router.get("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get document information by ID.

    Args:
        document_id: Document database ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Document information

    Raises:
        HTTPException 404: Document not found
        HTTPException 403: Not authorized to access document
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check authorization (users can only access their own documents unless admin)
    if document.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )

    return document


@router.get("", response_model=DocumentListResponse, status_code=status.HTTP_200_OK)
def list_documents(
    offset: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List documents for the current user.

    Args:
        offset: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Optional status filter (pending, processing, completed, failed)
        current_user: Authenticated user
        db: Database session

    Returns:
        List of documents with pagination info
    """
    # Build query
    query = db.query(Document)

    # Filter by owner (admins can see all)
    if not current_user.is_admin:
        query = query.filter(Document.owner_id == current_user.id)

    # Filter by status if provided
    if status_filter:
        query = query.filter(Document.status == status_filter)

    # Get total count
    total = query.count()

    # Apply pagination and get results
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()

    return DocumentListResponse(
        documents=documents,
        total=total,
        offset=offset,
        limit=limit
    )


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse], status_code=status.HTTP_200_OK)
def get_document_chunks(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all chunks for a document.

    Args:
        document_id: Document database ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of document chunks

    Raises:
        HTTPException 404: Document not found
        HTTPException 403: Not authorized
    """
    # Check document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )

    # Get chunks
    chunks = db.query(Chunk).filter(
        Chunk.document_id == document_id
    ).order_by(Chunk.chunk_index).all()

    return chunks


@router.get("/{document_id}/download", status_code=status.HTTP_200_OK)
def download_original_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download the original uploaded file.

    **Security:** Only the document owner or admins can download files.
    Files are stored in user-specific directories with restricted permissions.

    Args:
        document_id: Document database ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Original file as download

    Raises:
        HTTPException 404: Document not found or file missing
        HTTPException 403: Not authorized to access this document
    """
    # Check document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Security check: Only owner or admin can download
    if document.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )

    # Verify file exists on disk
    if not os.path.exists(document.file_path):
        logger = logging.getLogger(__name__)
        logger.error(f"File not found on disk: {document.file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )

    # Return file as download
    return FileResponse(
        path=document.file_path,
        media_type=document.mime_type or "application/octet-stream",
        filename=document.original_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename}"'
        }
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its associated data.

    Deletes:
    - Document database record
    - All associated chunks
    - Physical file from disk
    - Embeddings from FAISS index

    Args:
        document_id: Document database ID
        current_user: Authenticated user
        db: Database session

    Returns:
        204 No Content on success

    Raises:
        HTTPException 404: Document not found
        HTTPException 403: Not authorized to delete this document
    """
    # Check document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Security check: Only owner or admin can delete
    if document.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document"
        )

    logger = logging.getLogger(__name__)

    # Delete physical file from disk
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
            logger.info(f"Deleted file: {document.file_path}")
    except Exception as e:
        logger.error(f"Failed to delete file {document.file_path}: {e}")
        # Continue with database deletion even if file deletion fails

    # Delete all chunks for this document
    try:
        chunks_deleted = db.query(Chunk).filter(Chunk.document_id == document_id).delete()
        logger.info(f"Deleted {chunks_deleted} chunks for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to delete chunks: {e}")

    # Delete document from FAISS index
    # Note: This requires updating the FAISS index, which we'll handle separately
    # For now, we'll just log it
    logger.info(f"TODO: Remove document {document_id} from FAISS index")

    # Delete document record
    db.delete(document)
    db.commit()

    logger.info(f"Document {document_id} deleted successfully by user {current_user.id}")

    return None  # 204 No Content
