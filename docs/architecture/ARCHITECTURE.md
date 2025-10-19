# DocQuery Architecture Design Document

## Overview

DocQuery is designed as a modular, scalable document intelligence system with a clear separation of concerns. This document outlines the architectural decisions and explains how different components will evolve.

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│                 (Web UI, CLI, API Clients)                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Auth   │  │  Upload  │  │  Query   │  │  Admin   │   │
│  │ Endpoints│  │ Endpoints│  │Endpoints │  │ Endpoints│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
┌─────────────────┐  ┌──────────────┐  ┌─────────────┐
│   PostgreSQL    │  │    Redis     │  │   FAISS     │
│   (Metadata)    │  │ (Cache/Jobs) │  │  (Vectors)  │
└─────────────────┘  └──────────────┘  └─────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Background Workers                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   OCR/Text   │  │  Embedding   │  │   Indexing   │     │
│  │  Extraction  │  │  Generation  │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌──────────────┐
                    │  OpenAI API  │
                    │  (Embeddings │
                    │   & GPT-4)   │
                    └──────────────┘
```

## Current Implementation (v0.1.0)

### Implemented Features

1. **FastAPI Application Structure**
   - Clean separation of concerns with routers, models, schemas
   - Configuration management via Pydantic Settings
   - Environment-based configuration

2. **Authentication System**
   - JWT-based authentication with access and refresh tokens
   - Bcrypt password hashing
   - Admin-only user provisioning
   - Rate-limited login endpoint

3. **Database Layer**
   - SQLAlchemy ORM models for Users, Documents, Chunks, QueryLogs
   - PostgreSQL for metadata storage
   - Database session management with dependency injection

4. **Document Upload**
   - File upload with size validation
   - Persistent storage to disk
   - Metadata tracking in database
   - Job ID generation for async processing tracking

5. **Query Endpoint**
   - Query logging for analytics
   - Response time tracking
   - Skeleton for search results

6. **Redis Integration**
   - Rate limiting implementation
   - Ready for caching and job queue

## Incremental Development Plan

### Phase 2: Document Processing (Next Step)

**Objective:** Extract text and metadata from uploaded documents

**Components to Add:**
- `app/services/ocr.py` - OCR service using Tesseract
- `app/services/pdf_extractor.py` - PDF text extraction with PyMuPDF
- `app/services/chunker.py` - Intelligent text chunking
- `app/tasks/` - Background task processing

**Workflow:**
1. File uploaded → saved to disk with `status='pending'`
2. Background task triggered
3. Extract text (OCR or direct extraction)
4. Chunk text intelligently (size, overlaps, sentence boundaries)
5. Store chunks in database with `status='processing'`
6. Update document `status='completed'`

**Technologies:**
- Tesseract OCR for images
- PyMuPDF (fitz) for PDF text extraction
- Custom chunking algorithm (token-aware, sentence-boundary-aware)
- Whisper for audio to text.

### Phase 3: Embeddings & Vector Indexing

**Objective:** Generate embeddings and build searchable vector index

**Components to Add:**
- `app/services/embedding_service.py` - OpenAI embeddings API wrapper
- `app/services/faiss_index.py` - FAISS index management
- Background jobs for embedding generation

**Workflow:**
1. Chunks created → trigger embedding job
2. Batch chunks for embedding (OpenAI API efficiency)
3. Generate embeddings via OpenAI API
4. Store vectors in FAISS index
5. Update chunks with `has_embedding=True`

**Technologies:**
- OpenAI Embeddings API (text-embedding-3-large)
- FAISS for vector similarity search
- Persistent FAISS index on disk

### Phase 4: Hybrid Search & Retrieval

**Objective:** Implement semantic + keyword search with re-ranking

**Components to Add:**
- `app/services/search_service.py` - Hybrid search orchestration
- `app/services/bm25_search.py` - PostgreSQL full-text search
- `app/services/reranker.py` - Cross-encoder re-ranking
- `app/services/hyde.py` - Hypothetical Document Embeddings

**Workflow:**
1. User query received
2. Optional: HyDE expansion (generate hypothetical answer → embed)
3. FAISS semantic search (top-k1 results)
4. PostgreSQL BM25 search (top-k2 results)
5. Merge and deduplicate results
6. Re-rank with cross-encoder model
7. Return top-k final results with citations

**Technologies:**
- FAISS for semantic search
- PostgreSQL `tsvector` for BM25-style search
- Cross-encoder model (sentence-transformers)
- HyDE technique for query expansion

### Phase 5: RAG Generation

**Objective:** Generate answers with citations using GPT-4

**Components to Add:**
- `app/services/generator.py` - GPT-4 generation service
- `app/services/citation_tracker.py` - Citation extraction
- Streaming response support

**Workflow:**
1. Search results retrieved (with citations)
2. Format context with source references
3. Call GPT-4 with context and query
4. Stream response to client
5. Extract and validate citations
6. Return response with source pointers

**Technologies:**
- OpenAI GPT-4 API with streaming
- Citation extraction logic
- Source reference formatting

### Phase 6: Caching & Performance

**Objective:** Optimize performance with intelligent caching

**Components to Add:**
- Query result caching in Redis
- Embedding caching
- Token blacklisting for logout

**Strategies:**
- Cache search results by query hash
- TTL-based invalidation
- Cache embeddings for common queries

### Phase 7: Frontend

**Objective:** Build user-friendly web interface

**Components:**
- React SPA with Vite
- Authentication flow (login, token refresh)
- Document upload interface
- Chat-style query interface
- Admin panel for user management

### Phase 8: Production Deployment

**Objective:** Production-ready deployment on AWS

**Components:**
- Multi-stage Docker builds
- Nginx reverse proxy with HTTPS
- AWS EC2 for compute
- AWS RDS for PostgreSQL
- AWS ElastiCache for Redis
- AWS S3 for file storage
- CloudWatch for monitoring

## Design Principles

### 1. Modularity
- Each service has a single responsibility
- Services are loosely coupled via interfaces
- Easy to swap implementations (e.g., different embedding providers)

### 2. Scalability
- Stateless API design
- Background job processing for heavy tasks
- Horizontal scaling via container orchestration
- FAISS on-disk for large vector indices

### 3. Security
- No public signup (admin provisioning only)
- JWT authentication with short-lived tokens
- Rate limiting on sensitive endpoints
- Password hashing with bcrypt
- Input validation with Pydantic

### 4. Testability
- Dependency injection for easy mocking
- Separate database for tests (in-memory SQLite)
- Unit tests for business logic
- Integration tests for API endpoints

### 5. Maintainability
- Clear code structure with type hints
- Comprehensive docstrings
- Meaningful commit messages
- Incremental development with clear steps

## Database Design Evolution

### Current Schema (v0.1.0)

**Users**
- Core authentication data
- Admin flag for access control

**Documents**
- File metadata and storage info
- Processing status tracking
- Job ID for async processing

**Chunks**
- Skeleton for future text chunks
- Will store extracted text segments

**QueryLogs**
- Analytics and performance tracking
- Query history

### Future Enhancements

**Phase 2 Additions:**
- `Chunk.content` - Extracted text
- `Chunk.page_number` - Source page
- `Chunk.chunk_index` - Order within document

**Phase 3 Additions:**
- `Chunk.embedding_model` - Model used for embedding
- `Chunk.has_embedding` - Processing status
- External FAISS index file

**Phase 4 Additions:**
- PostgreSQL `tsvector` column for full-text search
- GIN index for fast text search

**Phase 5 Additions:**
- `QueryLog.results` - Expanded to include citation info
- Generation metadata tracking

## API Design Principles

### RESTful Routes
- `/auth/login` - Authentication
- `/auth/me` - Current user info
- `/upload` - Document upload
- `/documents/{id}` - Document retrieval
- `/query` - Search and query

### Future Routes
- `/admin/users` - User management (admin only)
- `/documents` - List documents
- `/documents/{id}/chunks` - View document chunks
- `/queries/{id}` - Query history

### Response Patterns
- Consistent error responses with `detail` field
- Pydantic schemas for type safety
- HTTP status codes following REST conventions

## Caching Strategy

### Cache Layers

1. **Query Result Cache**
   - Key: Hash of query + parameters
   - TTL: 1 hour
   - Invalidation: On document updates

2. **Embedding Cache**
   - Key: Hash of text
   - TTL: Never (embeddings don't change)
   - Storage: Redis

3. **Rate Limit Cache**
   - Key: `login:{ip_address}`
   - TTL: 1 minute
   - Reset on successful login

## Monitoring & Observability

### Metrics to Track (Future)
- Query latency (p50, p95, p99)
- Upload processing time
- Error rates by endpoint
- Active users
- Document processing queue depth

### Logging
- Structured logging with JSON format
- Log levels: DEBUG (dev), INFO (prod)
- Request/response logging
- Error tracing with stack traces

## Security Considerations

### Current Measures
- JWT with HS256 algorithm
- Bcrypt password hashing
- Rate limiting on login
- Input validation with Pydantic
- SQL injection prevention (SQLAlchemy ORM)

### Future Enhancements
- Token blacklisting on logout
- HTTPS enforcement in production
- CORS configuration for production
- API rate limiting (global)
- Audit logging for admin actions
- File type validation and malware scanning

## Conclusion

DocQuery is designed to be built incrementally, with each phase adding meaningful functionality while maintaining code quality and security. The architecture supports scaling from a single-server deployment to a distributed system with microservices if needed.

Next step: **Phase 2 - Document Processing**
