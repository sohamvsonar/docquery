# DocQuery - Internal Knowledge + Query Center

**DocQuery** is an efficient, secure, and scalable Document Intelligence / Internal Knowledge Center built with FastAPI. It supports document ingestion, multi-modal extraction, vector indexing with hybrid retrieval, and RAG-style generation with citation tracking.

## 🎯 Project Status

**Version:** 0.2.0 (Document Processing Complete!)

**Phase 2 Complete!** DocQuery now includes full document processing capabilities:

- ✅ FastAPI project structure with Docker support
- ✅ PostgreSQL database with SQLAlchemy ORM
- ✅ Redis integration for caching, rate limiting, and task queue
- ✅ JWT-based authentication (admin-only user provisioning)
- ✅ **OCR text extraction (Tesseract) for images**
- ✅ **PDF text extraction (PyMuPDF) with OCR fallback**
- ✅ **Audio transcription (OpenAI Whisper API)**
- ✅ **Intelligent text chunking (token-aware, sentence-preserving)**
- ✅ **Background task processing (Celery)**
- ✅ **Document status tracking and chunk storage**
- ✅ Unit tests for processing services

### What's Next (Incremental Roadmap)

**Phase 3: Embeddings & Search** (Next):
- 🔄 OpenAI embeddings generation for chunks
- 🔄 FAISS vector index creation
- 🔄 Semantic search via FAISS
- 🔄 PostgreSQL full-text search (BM25)
- 🔄 Hybrid retrieval combining both
- 🔄 HyDE query expansion
- 🔄 Cross-encoder re-ranking

**Phase 4+:**
- 🔄 GPT-4 RAG generation with streaming
- 🔄 Citation tracking
- 🔄 React frontend
- 🔄 Production deployment guide

## 🏗️ Architecture Overview

```
┌─────────────┐
│   Client    │
└─────┬───────┘
      │
      ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend                │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   Auth      │  │   Upload/Query  │  │
│  │  (JWT)      │  │   Endpoints     │  │
│  └─────────────┘  └─────────────────┘  │
└──────┬──────────────────┬───────────────┘
       │                  │
       ▼                  ▼
┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │    Redis     │
│  (Metadata)  │   │  (Cache/RL)  │
└──────────────┘   └──────────────┘
```

### Technology Stack

- **Backend:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 15
- **Cache/Broker:** Redis 7
- **Authentication:** JWT with bcrypt password hashing
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic v2
- **Testing:** Pytest
- **Document Processing:** PyMuPDF, Tesseract OCR, OpenAI Whisper
- **Text Chunking:** tiktoken, NLTK
- **Background Tasks:** Celery
- **Containerization:** Docker + Docker Compose

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development without Docker)
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd docquery
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

**Important:** Edit `.env` and set secure values for:
- `JWT_SECRET` - A strong secret key (min 32 characters)
- `POSTGRES_PASSWORD` - PostgreSQL database password
- `OPENAI_API_KEY` - Your OpenAI API key (required for future features)

### 3. Start the Services

```bash
docker-compose up --build
```

This will start:
- PostgreSQL database on port `5432`
- Redis cache/broker on port `6379`
- FastAPI backend on port `8000`
- Celery worker for background processing

Wait for the startup messages from all services

### 4. Create an Admin User

Open a new terminal and run:

```bash
docker-compose exec backend python scripts/create_admin.py
```

Follow the prompts to create your first admin user:
- Username (min 3 characters)
- Email (optional)
- Password (min 8 characters)

### 5. Access the API

- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Root:** http://localhost:8000/

## 📖 API Usage Guide

### Authentication

#### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Get Current User Info

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <your-access-token>"
```

### Document Upload

```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer <your-access-token>" \
  -F "file=@/path/to/document.pdf"
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": 1,
  "filename": "550e8400-e29b-41d4-a716-446655440000.pdf",
  "original_filename": "document.pdf",
  "status": "pending",
  "file_size": 1048576,
  "message": "File uploaded successfully. Processing will begin shortly."
}
```

### Query Documents

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer <your-access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What is the main topic?",
    "k": 5
  }'
```

Response (currently returns empty results - search will be implemented in Phase 3):
```json
{
  "query_id": "650e8400-e29b-41d4-a716-446655440001",
  "query_text": "What is the main topic?",
  "results": [],
  "result_count": 0,
  "response_time_ms": 12.5
}
```

### Get Document Chunks (NEW!)

```bash
curl -X GET http://localhost:8000/upload/1/chunks \
  -H "Authorization: Bearer <your-access-token>"
```

Response:
```json
[
  {
    "id": 1,
    "document_id": 1,
    "content": "This is the first extracted chunk...",
    "chunk_index": 0,
    "page_number": 1,
    "has_embedding": false,
    "created_at": "2025-01-15T10:30:00"
  }
]
```

### List Documents (NEW!)

```bash
curl -X GET "http://localhost:8000/upload?offset=0&limit=10&status_filter=completed" \
  -H "Authorization: Bearer <your-access-token>"
```

Response:
```json
{
  "documents": [...],
  "total": 25,
  "offset": 0,
  "limit": 10
}
```

### Download Original File (NEW! - SECURE)

```bash
curl -X GET http://localhost:8000/upload/1/download \
  -H "Authorization: Bearer <your-access-token>" \
  -o downloaded_file.pdf
```

**Security:**
- Only the document owner or admins can download files
- Files are stored in user-specific directories with restricted permissions
- See [docs/SECURE_FILE_STORAGE.md](docs/SECURE_FILE_STORAGE.md) for details

## 🧪 Running Tests

### Run All Tests

```bash
docker-compose exec backend pytest
```

### Run Tests with Coverage

```bash
docker-compose exec backend pytest --cov=app --cov-report=html
```

### Run Specific Test File

```bash
docker-compose exec backend pytest tests/test_auth.py -v
```

## 🛠️ Development

### Project Structure

```
docquery/
├── app/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Settings and configuration
│   ├── database.py           # Database connection and session
│   ├── models.py             # SQLAlchemy ORM models
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── auth.py               # Authentication utilities
│   ├── redis_client.py       # Redis utilities
│   ├── routers/              # API route handlers
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── documents.py      # Document upload endpoints
│   │   └── query.py          # Query endpoints
│   ├── services/             # Document processing services (NEW!)
│   │   ├── ocr.py            # Tesseract OCR
│   │   ├── pdf_extractor.py  # PyMuPDF extraction
│   │   ├── audio_transcription.py  # Whisper API
│   │   ├── chunker.py        # Intelligent chunking
│   │   └── document_processor.py  # Processing orchestrator
│   └── tasks/                # Background tasks (NEW!)
│       ├── celery_app.py     # Celery configuration
│       └── document_tasks.py # Processing tasks
├── scripts/
│   ├── init_db.py            # Database initialization
│   └── create_admin.py       # Admin user creation
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth.py          # Auth unit tests
│   ├── test_api.py           # API integration tests
│   └── test_document_processing.py  # Processing tests (NEW!)
├── uploads/                  # Uploaded files (created at runtime)
├── .env.example              # Example environment variables
├── .gitignore                # Git ignore rules
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker image definition
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

### Running Locally Without Docker

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and Redis** (ensure they're running and update `.env` with connection details)

3. **Initialize database:**
   ```bash
   python scripts/init_db.py
   ```

4. **Create admin user:**
   ```bash
   python scripts/create_admin.py
   ```

5. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

### Code Quality

Format code with Black:
```bash
black app/ tests/
```

Lint with Ruff:
```bash
ruff check app/ tests/
```

## 🔒 Security Features

- **Password Hashing:** bcrypt with automatic salt generation
- **JWT Authentication:** Secure token-based authentication
- **Rate Limiting:** Login rate limiting (5 attempts per minute per IP)
- **Admin-Only Provisioning:** No public user signup - only admins can create users
- **Input Validation:** Pydantic schemas for all request/response data
- **User-Isolated File Storage:** Each user has their own directory with restricted permissions (0o700)
- **Access Control:** Multi-layer authorization (JWT → Database → Filesystem)
- **Original File Preservation:** Uploaded files stored securely and never modified
- **HTTPS Ready:** Configure reverse proxy (nginx) for production HTTPS

See [docs/SECURE_FILE_STORAGE.md](docs/SECURE_FILE_STORAGE.md) for detailed security implementation.

## 🗄️ Database Schema

### Users Table
- `id` - Primary key
- `username` - Unique username
- `email` - Email (optional)
- `hashed_password` - Bcrypt hashed password
- `is_admin` - Admin flag
- `is_active` - Active status
- `created_at` - Creation timestamp

### Documents Table
- `id` - Primary key
- `filename` - Stored filename (UUID-based)
- `original_filename` - Original uploaded filename
- `file_path` - Full file path on disk
- `file_size` - File size in bytes
- `mime_type` - Content type
- `status` - Processing status (pending/processing/completed/failed)
- `job_id` - Unique job identifier
- `owner_id` - Foreign key to users
- `created_at` - Upload timestamp
- `processed_at` - Processing completion timestamp

### Chunks Table (**NOW POPULATED!**)
- `id` - Primary key
- `document_id` - Foreign key to documents
- `content` - Text content (extracted and chunked)
- `chunk_index` - Order within document
- `page_number` - Page number (for PDFs)
- `has_embedding` - Embedding status flag (ready for Phase 3)

### Query Logs Table
- `id` - Primary key
- `query_id` - Unique query identifier
- `user_id` - Foreign key to users
- `query_text` - User query
- `k` - Number of results requested
- `result_count` - Actual results returned
- `results` - JSON of results metadata
- `response_time_ms` - Query execution time

## 🐛 Troubleshooting

### Database Connection Errors

If you see database connection errors:
```bash
# Restart the services
docker-compose down
docker-compose up --build
```

### Redis Connection Errors

Redis failures are non-critical and logged as warnings. The app will continue to function but without caching/rate-limiting.

### Permission Errors on Uploads

Ensure the uploads directory has proper permissions:
```bash
mkdir -p uploads
chmod 777 uploads  # For development only
```

### Port Already in Use

If ports 8000, 5432, or 6379 are already in use:
- Stop conflicting services, OR
- Edit `docker-compose.yml` to use different host ports

## 📝 Design Decisions & Next Steps

### Phase 2 Completed ✅

1. **Background Processing:** Celery worker processes documents asynchronously after upload. Status tracked in database (pending → processing → completed/failed).

2. **Multi-Modal Extraction:** Supports PDFs (PyMuPDF + OCR fallback), images (Tesseract OCR), and audio (Whisper API).

3. **Intelligent Chunking:** Token-aware chunking with sentence boundary preservation. Configurable size/overlap, page metadata tracking.

4. **Chunk Storage:** All extracted chunks stored in database with page numbers and indexing. Ready for embedding generation.

See [docs/PHASE2_COMPLETE.md](docs/PHASE2_COMPLETE.md) for complete Phase 2 documentation.

### Next: Phase 3 - Embeddings & Search

**Phase 3 will add:**
- OpenAI embedding generation for all chunks
- FAISS vector index for semantic search
- PostgreSQL full-text search (BM25)
- Hybrid retrieval combining both approaches
- HyDE query expansion for better results
- Cross-encoder re-ranking
- Updated `/query` endpoint with real results

**Phase 4: RAG Generation**
- Integrate OpenAI GPT-4 for answer generation
- Implement citation tracking with chunk references
- Add streaming response support
- Cache results in Redis for performance


---

**Built with ❤️ using FastAPI, PostgreSQL, Redis, and OpenAI**
