# DocQuery - Project Structure

This document describes the reorganized project structure for better maintainability and separation of concerns.

## Directory Structure

```
docquery/
├── backend/                 # FastAPI Backend
│   ├── app/                # Application code
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic (search, cache, embeddings, etc.)
│   │   └── tasks/          # Celery background tasks
│   ├── scripts/            # Utility scripts (init_db, create_admin)
│   ├── tests/              # Backend tests
│   ├── uploads/            # User uploaded files and FAISS indexes
│   ├── requirements.txt    # Python dependencies
│   ├── pytest.ini          # Pytest configuration
│   ├── .env                # Environment variables
│   └── Dockerfile          # Backend Docker image
│
├── frontend/               # Next.js Frontend (Phase 6)
│   ├── app/                # Next.js 14 app directory
│   ├── components/         # React components
│   ├── lib/                # Utilities and API client
│   ├── hooks/              # Custom React hooks
│   ├── store/              # Zustand state management
│   ├── public/             # Static assets
│   └── package.json        # Node dependencies
│
├── docs/                   # Documentation
│   ├── backend/            # Backend-specific docs
│   │   ├── PHASE2_COMPLETE.md
│   │   ├── PHASE3_SEARCH.md
│   │   ├── PHASE4_RAG.md
│   │   ├── PHASE5_SETUP_GUIDE.md
│   │   └── ...
│   ├── frontend/           # Frontend-specific docs (Phase 6)
│   └── architecture/       # System architecture docs
│       └── ARCHITECTURE.md
│
├── docker-compose.yml      # Multi-service Docker orchestration
├── Makefile               # Development commands
├── README.md              # Main project README
└── .gitignore             # Git ignore rules
```

## Backend Structure

### `/backend/app/`
- **`main.py`** - FastAPI application entry point
- **`auth.py`** - JWT authentication logic
- **`models.py`** - SQLAlchemy database models
- **`schemas.py`** - Pydantic request/response schemas
- **`database.py`** - Database connection and session management
- **`config.py`** - Configuration and settings
- **`redis_client.py`** - Redis connection and utilities

### `/backend/app/routers/`
API endpoint definitions:
- **`auth.py`** - Login, logout, user info
- **`documents.py`** - Document upload and management
- **`query.py`** - Search endpoints
- **`rag.py`** - RAG answer generation (streaming and non-streaming)
- **`cache.py`** - Cache management (admin only)

### `/backend/app/services/`
Business logic services:
- **`search.py`** - Hybrid search (FAISS + PostgreSQL FTS)
- **`embedding.py`** - OpenAI embedding generation
- **`vector_index.py`** - FAISS vector index management
- **`cache.py`** - Redis caching (queries, embeddings, token blacklist)
- **`rag_generator.py`** - RAG answer generation
- **`citation_tracker.py`** - Citation extraction and mapping
- **`document_processor.py`** - Document parsing and chunking

### `/backend/app/tasks/`
- **`celery_app.py`** - Celery configuration
- **`document_tasks.py`** - Background document processing

## Frontend Structure (Phase 6)

### `/frontend/app/`
Next.js 14 app directory with file-based routing:
- **`/login`** - Login page
- **`/dashboard`** - Main dashboard
- **`/documents`** - Document management
- **`/chat`** - Chat-style query interface
- **`/admin`** - Admin panel

### `/frontend/components/`
Reusable React components:
- **`ui/`** - shadcn/ui components
- **`auth/`** - Authentication components
- **`documents/`** - Document-related components
- **`chat/`** - Chat interface components
- **`layout/`** - Layout components (navbar, sidebar, etc.)

### `/frontend/lib/`
Utilities and core functionality:
- **`api.ts`** - Axios API client with interceptors
- **`auth.ts`** - Authentication utilities
- **`utils.ts`** - Helper functions

### `/frontend/store/`
Zustand state management:
- **`authStore.ts`** - Authentication state
- **`documentStore.ts`** - Document state
- **`chatStore.ts`** - Chat state

## Key Technologies

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Relational database with full-text search
- **Redis** - Caching and token blacklist
- **FAISS** - Vector similarity search
- **Celery** - Background task processing
- **OpenAI API** - Embeddings and chat completion

### Frontend (Phase 6)
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **TailwindCSS** - Utility-first CSS
- **shadcn/ui** - Beautiful UI components
- **Axios** - HTTP client
- **React Query** - Data fetching and caching
- **Zustand** - State management
- **Framer Motion** - Animations

## Running the Project

### Development (Local)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Docker (Recommended)

```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down
```

## Environment Variables

### Backend (`/backend/.env`)
```env
# Database
POSTGRES_USER=docquery_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=docquery
DATABASE_URL=postgresql://user:pass@localhost:5432/docquery

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=your-openai-key
```

### Frontend (`/frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development Workflow

1. **Backend changes**: Edit files in `/backend/app/`, tests auto-reload
2. **Frontend changes**: Edit files in `/frontend/`, hot module replacement active
3. **Database migrations**: Use Alembic (future enhancement)
4. **API testing**: Use `/docs` for Swagger UI, `/redoc` for ReDoc

## Testing

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests (after Phase 6)
cd frontend
npm test
```

## Documentation

- **Backend API**: http://localhost:8000/docs
- **Architecture**: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- **Phase Docs**: [docs/backend/](docs/backend/)

## Notes

- **Uploads**: Stored in `/backend/uploads/` with user-specific folders
- **FAISS Indexes**: Stored per-user in `/backend/uploads/indexes/`
- **Caching**: Redis caches queries (1h TTL) and embeddings (24h TTL)
- **Authentication**: JWT tokens with refresh token support

## Next Steps

- ✅ Phase 1-5: Backend complete
- 🚧 Phase 6: Frontend (in progress)
- 📋 Phase 7: Deployment and monitoring
