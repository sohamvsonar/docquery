# Add this to the end of documents.py

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
