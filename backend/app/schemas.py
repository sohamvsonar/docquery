"""
Pydantic schemas for request validation and response serialization.
Provides type-safe data validation and automatic API documentation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Request schema for user login."""
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    password: str = Field(..., min_length=8, description="Password")


class TokenResponse(BaseModel):
    """Response schema for successful authentication."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class UserResponse(BaseModel):
    """Response schema for user information."""
    id: int
    username: str
    email: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateRequest(BaseModel):
    """Request schema for creating a new user (admin only)."""
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    email: Optional[str] = Field(None, description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    is_admin: bool = Field(default=False, description="Admin privileges")


class UserListResponse(BaseModel):
    """Response schema for list of users."""
    users: List[UserResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Document Upload Schemas
# ============================================================================

class UploadResponse(BaseModel):
    """Response schema for file upload."""
    job_id: str = Field(..., description="Unique job identifier")
    document_id: int = Field(..., description="Document database ID")
    filename: str = Field(..., description="Stored filename")
    original_filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    file_size: int = Field(..., description="File size in bytes")
    message: str = Field(..., description="Status message")


class DocumentResponse(BaseModel):
    """Response schema for document information."""
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: Optional[str] = None
    status: str
    job_id: str
    owner_id: int
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChunkResponse(BaseModel):
    """Response schema for a document chunk."""
    id: int
    document_id: int
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    has_embedding: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Response schema for list of documents."""
    documents: List[DocumentResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Query Schemas
# ============================================================================

class QueryRequest(BaseModel):
    """Request schema for document query."""
    q: str = Field(..., min_length=1, max_length=1000, description="Query text")
    k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    search_type: str = Field(
        default="hybrid",
        description="Search type: 'vector', 'fulltext', or 'hybrid'"
    )
    alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for vector search in hybrid mode (0=fulltext only, 1=vector only)"
    )


class QueryResultItem(BaseModel):
    """Schema for a single query result item."""
    chunk_id: int = Field(..., description="Chunk identifier")
    document_id: int = Field(..., description="Source document ID")
    document_filename: str = Field(..., description="Source document filename")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Chunk index in document")
    page_number: Optional[int] = Field(None, description="Page number (if applicable)")
    score: float = Field(..., description="Relevance score")
    rank: int = Field(..., description="Result rank position")


class QueryResponse(BaseModel):
    """Response schema for query results."""
    query_id: str = Field(..., description="Unique query identifier")
    query_text: str = Field(..., description="Original query text")
    results: List[QueryResultItem] = Field(default=[], description="Search results")
    result_count: int = Field(..., description="Number of results returned")
    response_time_ms: Optional[float] = Field(None, description="Query execution time")


# ============================================================================
# RAG (Retrieval-Augmented Generation) Schemas
# ============================================================================

class RAGRequest(BaseModel):
    """Request schema for RAG answer generation."""
    q: str = Field(..., min_length=1, max_length=1000, description="Question to answer")
    k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")
    search_type: str = Field(
        default="hybrid",
        description="Search type: 'vector', 'fulltext', or 'hybrid'"
    )
    alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for vector search in hybrid mode"
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model: 'gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0=deterministic, 2=creative)"
    )
    max_tokens: int = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Maximum tokens in response"
    )
    stream: bool = Field(
        default=False,
        description="Enable streaming response"
    )


class CitationItem(BaseModel):
    """Schema for a single citation."""
    number: int = Field(..., description="Citation number [1], [2], etc.")
    chunk_id: int = Field(..., description="Referenced chunk ID")
    document_id: int = Field(..., description="Referenced document ID")
    document_filename: str = Field(..., description="Source document filename")
    page_number: Optional[int] = Field(None, description="Page number if available")
    chunk_index: int = Field(..., description="Chunk index in document")
    score: float = Field(..., description="Relevance score of this source")
    content_preview: str = Field(..., description="Preview of source content")


class RAGResponse(BaseModel):
    """Response schema for RAG answer generation."""
    query_id: str = Field(..., description="Unique query identifier")
    query_text: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer with citations")
    citations: List[CitationItem] = Field(default=[], description="List of citations used")
    sources: List[QueryResultItem] = Field(default=[], description="Retrieved source chunks")
    model: str = Field(..., description="Model used for generation")
    usage: Dict[str, int] = Field(default={}, description="Token usage statistics")
    response_time_ms: Optional[float] = Field(None, description="Total response time")
    search_time_ms: Optional[float] = Field(None, description="Search time")
    generation_time_ms: Optional[float] = Field(None, description="Generation time")


# ============================================================================
# Error Response Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response schema."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")


# ============================================================================
# Health Check Schema
# ============================================================================

class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Current server time")
    database: str = Field(..., description="Database connection status")
    redis: str = Field(..., description="Redis connection status")
