"""
SQLAlchemy ORM models for the DocQuery application.
Defines database schema for users, documents, chunks, and query logs.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON, Index
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.database import Base


class User(Base):
    """
    User model for authentication and authorization.
    Only admins can create new users (no public signup).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    documents = relationship("Document", back_populates="owner")
    queries = relationship("QueryLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"


class Document(Base):
    """
    Document model representing uploaded files.
    Stores metadata and references to the file on disk.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=True)

    # Processing status: 'pending', 'processing', 'completed', 'failed'
    status = Column(String(50), default='pending', nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Job tracking
    job_id = Column(String(100), unique=True, nullable=False, index=True)

    # Metadata
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class Chunk(Base):
    """
    Chunk model representing extracted text segments from documents.
    Stores text content, vector embeddings, and supports full-text search.
    """
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, index=True)

    # Chunk content and metadata
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    page_number = Column(Integer, nullable=True)  # For PDFs

    # Vector embedding (1536 dimensions for text-embedding-3-small)
    # Stored as PostgreSQL ARRAY for potential future PostgreSQL vector ops
    # Primary vector search uses FAISS index
    embedding = Column(ARRAY(Float), nullable=True)
    embedding_model = Column(String(100), nullable=True)
    has_embedding = Column(Boolean, default=False, nullable=False, index=True)

    # Token count for analytics
    token_count = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"


# Create GIN index for full-text search on chunk content
# This will be created via raw SQL in a migration or init script
# Index(
#     'idx_chunks_content_fts',
#     func.to_tsvector('english', Chunk.content),
#     postgresql_using='gin'
# )


class QueryLog(Base):
    """
    Query log model for tracking user queries and analytics.
    Stores query text, results, and performance metrics.
    """
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(String(100), unique=True, nullable=False, index=True)

    # Query information
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    k = Column(Integer, default=5, nullable=False)  # Number of results requested

    # Results and performance
    result_count = Column(Integer, default=0, nullable=False)
    results = Column(JSON, nullable=True)  # Store retrieved chunk IDs and scores
    response_time_ms = Column(Float, nullable=True)  # Query execution time

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="queries")

    def __repr__(self):
        return f"<QueryLog(id={self.id}, query_id='{self.query_id}', user_id={self.user_id})>"
