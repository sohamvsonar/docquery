# DocQuery – Intelligent Document Search & RAG

DocQuery is a secure, scalable document intelligence platform. It ingests files, extracts and chunks content, indexes with embeddings, and powers retrieval-augmented generation. Backend is FastAPI + Celery + PostgreSQL + Redis + FAISS. Frontend is Next.js.

## Features
- Authentication with JWT (admin flag support)
- Uploads with secure per-user storage
- Multi-modal extraction: PDF (PyMuPDF + OCR fallback), Images (Tesseract), Audio (OpenAI Whisper)
- DOC/DOCX extraction, text/markdown/HTML/CSV/JSON/XML ingestion
- Intelligent, token-aware chunking
- Background processing via Celery
- FAISS vector index + groundwork for hybrid search
- Markdown-rendered answers in chat UI (frontend)

## Tech Stack
- Backend: FastAPI, SQLAlchemy 2, Pydantic v2, Celery
- Data: PostgreSQL 15, Redis 7
- Vector Search: FAISS (IndexFlatL2)
- Frontend: Next.js 15 (App Router), React 19, Tailwind
- Containerization: Docker, Docker Compose
- Tests: Pytest

## Repository Structure
- `backend/` – FastAPI app and services
- `frontend/` – Next.js app
- `docs/` – Guides and architecture docs
  - `docs/deployment/AWS_DEPLOYMENT_GUIDE.md` – Production deployment on AWS

## Prerequisites
- Docker and Docker Compose (recommended for local dev)
- Python 3.11+ and Node 20 (only if running services without Docker)

## Quick Start (Docker Compose)
1) Clone and enter the repo
- `git clone <your-repo-url>`
- `cd docquery`

2) Copy environment file and edit
- `cp .env.example .env`
- Set at least:
  - `POSTGRES_PASSWORD`
  - `JWT_SECRET` (strong, 32+ chars)
  - `OPENAI_API_KEY` (for audio transcription and generation)

3) Start services
- `docker-compose up --build`
- Services: Postgres 5432, Redis 6379, API 8000, Celery worker

4) Create an admin user
- `docker-compose exec backend python scripts/create_admin.py`

5) Open docs (dev only)
- API docs at `http://localhost:8000/docs`

## Frontend (Local Dev)
- `cd frontend`
- `npm ci`
- Ensure `frontend/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `npm run dev` then open `http://localhost:3000`

## Supported File Types
- PDFs: `application/pdf`
- Images: `image/png`, `image/jpeg`, `image/jpg`, `image/tiff`, `image/bmp`, `image/gif`
- Audio: `audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/m4a`, `audio/ogg`, `audio/flac`
- Documents: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/msword`
- Text-like: `text/plain`, `text/markdown`, `text/html`, `text/csv`, `text/x-csv`, `application/csv`, `application/vnd.ms-excel`, `application/json`, `application/xml`, `text/xml`

Note: Some browsers upload `.csv` as `application/vnd.ms-excel`; this is supported.

## Common API Endpoints
- Upload: `POST /upload` (multipart form with `file`)
- List documents: `GET /upload?offset=&limit=&status_filter=`
- Get a document: `GET /upload/{document_id}`
- Download original: `GET /upload/{document_id}/download`
- Health: `GET /health`

Auth: Include `Authorization: Bearer <token>` for protected routes. Use the login flow from the frontend to obtain tokens.

## Testing
- All tests: `docker-compose exec backend pytest`
- Coverage: `docker-compose exec backend pytest --cov=app --cov-report=term-missing`
- Single test file: `docker-compose exec backend pytest tests/test_redis_connection.py -v`

## Deployment
- See `docs/deployment/AWS_DEPLOYMENT_GUIDE.md` for a production-ready guide covering:
  - ECS Fargate + RDS + ElastiCache + EFS + ALB (+ CloudFront)
  - Instance sizing recommendations
  - ECR build/push script
  - ECS services (API, Worker, Frontend)
  - CI/CD with GitHub Actions (tests on every push, deploy on main)

## Security Notes
- In production, set `DEBUG=false` and restrict CORS origins in `backend/app/main.py`
- Store secrets in AWS Secrets Manager or SSM; do not commit secrets
- Uploaded files are saved under per-user directories with restricted permissions

## Troubleshooting
- Upload failures: check file size limit (`max_upload_size`), supported MIME, and worker logs
- FAISS index empty: ensure Celery worker is running and that uploads complete
- CORS errors: verify `NEXT_PUBLIC_API_URL` and backend CORS settings

## License
Proprietary – internal use for DocQuery deployment unless stated otherwise.

