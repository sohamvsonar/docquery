# Phase 3 Setup Guide - Quick Start

## Prerequisites
- Phase 2 completed and working
- OpenAI API key with access to embeddings API
- PostgreSQL and Redis running
- Python environment activated

## Step-by-Step Setup

### 1. Install New Dependencies

```bash
pip install -r requirements.txt
```

This adds:
- `faiss-cpu` - Vector search library
- `numpy` - Numerical operations

### 2. Update Database Schema

The `Chunk` model has new columns for embeddings. You have two options:

#### Option A: Fresh Database (Recommended for testing)
```bash
# Drop and recreate all tables
python scripts/init_db.py
```

#### Option B: Migrate Existing Database
```sql
-- Connect to PostgreSQL
psql -U docquery_user -d docquery

-- Add new columns
ALTER TABLE chunks ADD COLUMN embedding FLOAT[];
ALTER TABLE chunks ADD COLUMN embedding_model VARCHAR(100);
ALTER TABLE chunks ADD COLUMN has_embedding BOOLEAN DEFAULT FALSE;
ALTER TABLE chunks ADD COLUMN token_count INTEGER;
```

### 3. Create Full-Text Search Index

```bash
python scripts/add_fts_index.py
```

Expected output:
```
Adding full-text search index to chunks table...
✓ Full-text search index created successfully

Index details:
  Schema: public
  Table: chunks
  Index: idx_chunks_content_fts
  Definition: CREATE INDEX idx_chunks_content_fts ON public.chunks USING gin (to_tsvector('english'::regconfig, content))
```

### 4. Verify OpenAI API Key

Check your `.env` file:
```env
OPENAI_API_KEY=sk-...your-key-here...
```

Test the API key:
```bash
python -c "from app.services.embedding import embedding_service; print('API Key OK' if embedding_service else 'API Key Error')"
```

### 5. Start Services

**Terminal 1 - FastAPI Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

### 6. Create Admin User (if needed)

```bash
python scripts/create_admin.py
```

### 7. Test the System

#### Get Access Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

Save the token:
```bash
export TOKEN="your_access_token_here"
```

#### Upload a Test Document
```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@README.md"
```

**Watch the Celery worker terminal** - you should see:
```
Processing document 1: README.md
Generating embeddings for 10 chunks
Adding 10 embeddings to FAISS index
Successfully processed document 1: 10 chunks created, 10 embeddings generated
```

#### Check Document Status
```bash
curl -X GET "http://localhost:8000/upload/1" \
  -H "Authorization: Bearer $TOKEN"
```

Look for `"status": "completed"` and `"processed_at": "2025-..."`.

#### Test Vector Search
```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What is DocQuery?",
    "k": 5,
    "search_type": "vector"
  }'
```

#### Test Full-Text Search
```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "document",
    "k": 5,
    "search_type": "fulltext"
  }'
```

#### Test Hybrid Search (Recommended)
```bash
curl -X POST http://localhost:8000/query ^
  -H "Authorization: Bearer $TOKEN" ^
  -H "Content-Type: application/json" ^
  -d '{
    "q": "What is LSTM?",
    "k": 10,
    "search_type": "hybrid",
    "alpha": 0.5
  }'
```

Expected response:
```json
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "query_text": "How does the system work?",
  "results": [
    {
      "chunk_id": 3,
      "document_id": 1,
      "document_filename": "README.md",
      "content": "DocQuery is a document intelligence system...",
      "chunk_index": 2,
      "page_number": null,
      "score": 0.87,
      "rank": 1
    }
  ],
  "result_count": 10,
  "response_time_ms": 234.5
}
```

## Verification Checklist

- [ ] Dependencies installed (`faiss-cpu`, `numpy`)
- [ ] Database schema updated (new `embedding` column)
- [ ] Full-text search index created (`idx_chunks_content_fts`)
- [ ] OpenAI API key configured
- [ ] FastAPI server running
- [ ] Celery worker running
- [ ] Test document uploaded successfully
- [ ] Embeddings generated (check Celery logs)
- [ ] Vector search returns results
- [ ] Full-text search returns results
- [ ] Hybrid search returns results

## Troubleshooting

### "FAISS index is empty" error
**Cause:** No documents processed yet with embeddings.

**Solution:** Upload a document and wait for processing to complete.

### "No results found" from search
**Cause:**
1. No documents uploaded, or
2. Documents still processing, or
3. Query doesn't match content

**Solution:**
```bash
# Check document status
curl -X GET "http://localhost:8000/upload" -H "Authorization: Bearer $TOKEN"

# Look for "status": "completed"
```

### Full-text search fails
**Cause:** FTS index not created.

**Solution:**
```bash
python scripts/add_fts_index.py
```

### OpenAI API errors
**Cause:** Invalid or missing API key.

**Solution:** Check `.env` file and verify the key at https://platform.openai.com/api-keys

### Celery worker shows errors
**Common errors:**

1. **"OpenAI API key not found"**
   - Set `OPENAI_API_KEY` in `.env`
   - Restart Celery worker

2. **"Database connection error"**
   - Check PostgreSQL is running
   - Verify `DATABASE_URL` in `.env`

3. **"Import error: No module named 'faiss'"**
   - Install dependencies: `pip install -r requirements.txt`
   - Restart Celery worker

## What's Different in Phase 3?

### Document Processing Pipeline

**Phase 2:**
```
Upload → Extract Text → Chunk → Store in DB
```

**Phase 3:**
```
Upload → Extract Text → Chunk → Generate Embeddings → Store in DB + FAISS Index
```

### New Files Created

- `app/services/embedding.py` - OpenAI embedding service
- `app/services/vector_index.py` - FAISS index manager
- `app/services/search.py` - Hybrid search service
- `app/routers/query.py` - Updated with real search
- `scripts/add_fts_index.py` - FTS index creation
- `tests/test_search.py` - Search functionality tests
- `docs/PHASE3_SEARCH.md` - Detailed documentation

### Updated Files

- `app/models.py` - Added embedding columns to Chunk
- `app/schemas.py` - Updated QueryRequest/QueryResultItem
- `app/tasks/document_tasks.py` - Added embedding generation
- `requirements.txt` - Added faiss-cpu and numpy

## Performance Expectations

### Document Processing
- **Text files**: 5-10 seconds per document
- **PDFs**: 10-30 seconds depending on size
- **Embedding generation**: ~1 second per 10 chunks

### Search Performance
- **Vector search**: 10-50ms (depends on index size)
- **Full-text search**: 10-50ms (depends on corpus size)
- **Hybrid search**: 200-500ms (includes embedding generation)

## Next Steps

With Phase 3 complete, you now have:
- ✅ Document upload and processing
- ✅ Multi-modal extraction (PDF, images, audio, text)
- ✅ Intelligent chunking
- ✅ Vector embeddings (OpenAI)
- ✅ FAISS vector search
- ✅ PostgreSQL full-text search
- ✅ Hybrid search with RRF fusion
- ✅ Query logging and analytics

**Ready for production-like usage!**

For advanced features (Phase 4+), see [PHASE3_SEARCH.md](docs/PHASE3_SEARCH.md) "Future Enhancements" section.

## Support

- **API Documentation**: http://localhost:8000/docs
- **Detailed Phase 3 Docs**: [docs/PHASE3_SEARCH.md](docs/PHASE3_SEARCH.md)
- **Security Guide**: [docs/SECURE_FILE_STORAGE.md](docs/SECURE_FILE_STORAGE.md)
- **Local Testing**: [LOCAL_TESTING_NO_DOCKER.md](LOCAL_TESTING_NO_DOCKER.md)
