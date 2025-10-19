"""
Admin-only user management routes.
Allows admins to list users and create new users.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas import UserResponse, UserCreateRequest, UserListResponse
from app.auth import get_current_user, hash_password
from app.models import User

router = APIRouter(prefix="/users", tags=["Users"])


def require_admin(current_user: User = Depends(get_current_user)):
    """
    Dependency to ensure user is an admin.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if they are admin

    Raises:
        HTTPException 403: User is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access this resource"
        )
    return current_user


@router.get("", response_model=UserListResponse, status_code=status.HTTP_200_OK)
def list_users(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List all users (admin only).

    Args:
        offset: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Authenticated admin user

    Returns:
        List of users with pagination info
    """
    # Get total count
    total = db.query(User).count()

    # Get users with pagination
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return UserListResponse(
        users=users,
        total=total,
        offset=offset,
        limit=limit
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new user (admin only).

    Args:
        user_data: User creation data
        db: Database session
        current_user: Authenticated admin user

    Returns:
        Created user information

    Raises:
        HTTPException 400: Username or email already exists
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Normalize email: convert empty string to None
    email = user_data.email.strip() if user_data.email else None
    if email == "":
        email = None

    # Check if email already exists (if provided)
    if email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

    # Create new user
    new_user = User(
        username=user_data.username,
        email=email,  # Use normalized email (None if empty)
        hashed_password=hash_password(user_data.password),
        is_admin=user_data.is_admin,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get user information by ID (admin only).

    Args:
        user_id: User database ID
        db: Database session
        current_user: Authenticated admin user

    Returns:
        User information

    Raises:
        HTTPException 404: User not found
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user.

    Users can delete their own account.
    Admins can delete any user except themselves.
    Cannot delete the last admin.
    Deletes all user's documents, chunks, and query logs.

    Args:
        user_id: User database ID
        db: Database session
        current_user: Authenticated user

    Returns:
        204 No Content on success

    Raises:
        HTTPException 404: User not found
        HTTPException 403: Not authorized to delete this user
        HTTPException 400: Cannot delete the last admin
    """
    import logging
    import os
    from app.models import Document, Chunk, QueryLog

    logger = logging.getLogger(__name__)

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions: users can delete themselves, admins can delete others
    is_self_delete = user.id == current_user.id
    is_admin_delete = current_user.is_admin and user.id != current_user.id

    if not is_self_delete and not is_admin_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )

    # Cannot delete the last admin
    if user.is_admin:
        admin_count = db.query(User).filter(User.is_admin == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user"
            )

    # Get all user's documents
    documents = db.query(Document).filter(Document.owner_id == user_id).all()

    # Delete all chunks and files for each document
    for document in documents:
        # Delete chunks
        db.query(Chunk).filter(Chunk.document_id == document.id).delete()

        # Delete physical file
        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
                logger.info(f"Deleted file: {document.file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {document.file_path}: {e}")

    # Delete all documents
    db.query(Document).filter(Document.owner_id == user_id).delete()

    # Delete all query logs
    db.query(QueryLog).filter(QueryLog.user_id == user_id).delete()

    # Delete user
    db.delete(user)
    db.commit()

    logger.info(f"Deleted user {user_id} and all associated data")

    return None
