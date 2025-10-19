# DocQuery Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Start the Services

```bash
docker-compose up --build
```

Wait for all services to start:
- `docquery_postgres` - Database ready
- `docquery_redis` - Cache ready
- `docquery_backend` - API server running
- `docquery_celery_worker` - Background worker ready

### Step 2: Create Admin User

In a new terminal:

```bash
docker-compose exec backend python scripts/create_admin.py
```

Enter:
- Username: `admin`
- Email: `admin@example.com` (or leave blank)
- Password: `Admin123!` (choose a strong password)

### Step 3: Test the API

#### Get an Access Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!"}'
```

Copy the `access_token` from the response.

#### Check Your User Info

```bash
export TOKEN="your-access-token-here"

curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

#### Upload a Document

```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@README.md"
```

**NEW in Phase 2:** Document will be processed automatically in the background!

#### Check Document Status

```bash
# Get document by ID (use the document_id from upload response)
curl -X GET http://localhost:8000/upload/1 \
  -H "Authorization: Bearer $TOKEN"
```

Look for `"status": "completed"` to know when processing is done.

#### View Extracted Chunks

```bash
curl -X GET http://localhost:8000/upload/1/chunks \
  -H "Authorization: Bearer $TOKEN"
```

You'll see the intelligently chunked text extracted from your document!

#### Query Documents

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"q": "What is DocQuery?", "k": 5}'
```

*Note: Search results coming in Phase 3!*

## 🎉 You're Ready!

Your DocQuery instance is running! Visit:
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## 📖 Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Check [docs/PHASE2_COMPLETE.md](docs/PHASE2_COMPLETE.md) for Phase 2 features
3. Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand the design
4. Run tests: `docker-compose exec backend pytest`
5. Explore the API documentation at http://localhost:8000/docs

## 🎬 Try Different File Types

**Phase 2 now supports:**
- PDFs (with automatic OCR for scanned pages)
- Images (PNG, JPG, TIFF, etc.)
- Audio files (MP3, WAV, M4A, etc.)

```bash
# Upload a PDF
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"

# Upload an image
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@screenshot.png"

# Upload audio
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@recording.mp3"
```

## 🛑 Stop the Services

```bash
docker-compose down
```

To remove all data (database, uploads):

```bash
docker-compose down -v
rm -rf uploads/*
```
