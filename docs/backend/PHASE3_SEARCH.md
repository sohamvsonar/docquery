# Phase 3: Embeddings & Vector Search

## Overview

Phase 3 implements semantic search capabilities using OpenAI embeddings and FAISS vector indexing, combined with PostgreSQL full-text search for hybrid retrieval.

## Features

### 1. Vector Embeddings
- **OpenAI text-embedding-3-small**: Cost-effective, high-quality embeddings (1536 dimensions)
- **Batch processing**: Efficient embedding generation for multiple chunks
- **Automatic embedding**: Generated during document processing

### 2. Vector Search (FAISS)
- **Exact similarity search**: Using FAISS IndexFlatL2
- **Persistent storage**: Index saved to disk with chunk ID mapping
- **Fast k-NN retrieval**: Efficient nearest neighbor search

### 3. Full-Text Search (PostgreSQL)
- **GIN index**: PostgreSQL full-text search with `tsvector`
- **BM25-like ranking**: Using `ts_rank` for relevance scoring
- **Keyword matching**: Complement semantic search with exact matching

### 4. Hybrid Search
- **Reciprocal Rank Fusion (RRF)**: Combines vector and full-text results
- **Configurable weighting**: Alpha parameter (0-1) controls vector vs. keyword balance
- **User access control**: Results filtered by document ownership

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Endpoint (/query)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Search Service                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Vector     │  │  Full-Text   │  │   Hybrid     │      │
│  │   Search     │  │   Search     │  │  (RRF Fusion)│      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐
│  Embedding      │  │  PostgreSQL     │  │  Result     │
│  Service        │  │  FTS Index      │  │  Fusion     │
│  (OpenAI API)   │  │  (GIN)          │  │  (RRF)      │
└────────┬────────┘  └─────────────────┘  └─────────────┘
         │
         ▼
┌─────────────────┐
│  FAISS Index    │
│  (Vector Store) │
└─────────────────┘
```

## Components

### 1. Embedding Service (`app/services/embedding.py`)

Generates vector embeddings using OpenAI's API:

```python
from app.services.embedding import embedding_service

# Single text embedding
embedding = embedding_service.embed_text("What is machine learning?")
# Returns: List[float] of length 1536

# Batch embedding (more efficient)
texts = ["Text 1", "Text 2", "Text 3"]
embeddings = embedding_service.embed_batch(texts, batch_size=100)
# Returns: List[List[float]]
```

**Features:**
- Batch processing (up to 100 texts per API call)
- Error handling with retries
- Dimension: 1536 (text-embedding-3-small)

### 2. Vector Index Manager (`app/services/vector_index.py`)

Manages FAISS index for similarity search:

```python
from app.services.vector_index import vector_index

# Add vectors to index
embeddings = [[0.1, 0.2, ...], [0.3, 0.4, ...]]  # 1536-dim vectors
chunk_ids = [1, 2]
vector_index.add_vectors(embeddings, chunk_ids)

# Save index to disk
vector_index.save_index()

# Search for similar vectors
query_embedding = [0.15, 0.25, ...]
results = vector_index.search(query_embedding, k=10)
# Returns: [(chunk_id, distance), ...]
```

**Features:**
- Exact L2 distance search (IndexFlatL2)
- Persistent storage (index + chunk ID mapping)
- Thread-safe operations
- Index statistics and management

**Index Location:**
- Index file: `uploads/indexes/faiss_index.bin`
- Mapping file: `uploads/indexes/chunk_mapping.pkl`

### 3. Search Service (`app/services/search.py`)

Unified search interface with three modes:

#### Vector Search
Semantic similarity using embeddings:
```python
from app.services.search import search_service

results = search_service.vector_search(
    query="machine learning algorithms",
    k=10,
    db=db_session
)
```

#### Full-Text Search
Keyword-based search using PostgreSQL FTS:
```python
results = search_service.fulltext_search(
    query="machine learning",
    k=10,
    db=db_session
)
```

#### Hybrid Search (Recommended)
Combines both methods using RRF:
```python
results = search_service.hybrid_search(
    query="machine learning",
    k=10,
    alpha=0.5,  # 0.5 = equal weight for vector and fulltext
    db=db_session
)
```

**Alpha Parameter:**
- `alpha=1.0`: Vector search only
- `alpha=0.5`: Equal weighting (recommended)
- `alpha=0.0`: Full-text search only

### 4. Query Endpoint (`POST /query`)

Main search API endpoint:

**Request:**
```json
{
  "q": "What are the key features of Python?",
  "k": 5,
  "search_type": "hybrid",
  "alpha": 0.5
}
```

**Response:**
```json
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "query_text": "What are the key features of Python?",
  "results": [
    {
      "chunk_id": 42,
      "document_id": 7,
      "document_filename": "python_guide.pdf",
      "content": "Python is a high-level programming language...",
      "chunk_index": 3,
      "page_number": 2,
      "score": 0.89,
      "rank": 1
    }
  ],
  "result_count": 5,
  "response_time_ms": 234.5
}
```

**Parameters:**
- `q` (required): Query text (1-1000 chars)
- `k` (optional): Number of results (1-50, default: 5)
- `search_type` (optional): "vector", "fulltext", or "hybrid" (default: "hybrid")
- `alpha` (optional): Vector weight 0-1 (default: 0.5)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies for Phase 3:
- `faiss-cpu==1.9.0` - FAISS vector search library
- `numpy==1.26.4` - Numerical operations for vectors

### 2. Initialize Database Schema

The `Chunk` model has been updated with new columns:
- `embedding`: ARRAY of floats (1536 dimensions)
- `embedding_model`: Model name ("text-embedding-3-small")
- `has_embedding`: Boolean flag
- `token_count`: Chunk size in tokens

**Recreate database schema:**
```bash
python scripts/init_db.py
```

Or migrate existing database:
```sql
ALTER TABLE chunks ADD COLUMN embedding FLOAT[];
ALTER TABLE chunks ADD COLUMN embedding_model VARCHAR(100);
ALTER TABLE chunks ADD COLUMN has_embedding BOOLEAN DEFAULT FALSE;
ALTER TABLE chunks ADD COLUMN token_count INTEGER;
```

### 3. Create Full-Text Search Index

```bash
python scripts/add_fts_index.py
```

This creates a GIN index on `chunks.content` for fast full-text search.

**Manual SQL:**
```sql
CREATE INDEX idx_chunks_content_fts
ON chunks
USING gin(to_tsvector('english', content));
```

### 4. Set OpenAI API Key

Ensure your `.env` file has the OpenAI API key:
```env
OPENAI_API_KEY=sk-...
```

### 5. Process Documents

When you upload documents, the processing pipeline now:
1. Extracts text (PDF/OCR/Audio/Text)
2. Chunks text intelligently
3. **Generates embeddings** (new)
4. **Stores embeddings in database** (new)
5. **Adds vectors to FAISS index** (new)

**Watch Celery worker logs:**
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

You should see:
```
Generating embeddings for 15 chunks
Adding 15 embeddings to FAISS index
Successfully processed document 1: 15 chunks created, 15 embeddings generated
```

## Usage Examples

### Example 1: Basic Hybrid Search

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "machine learning algorithms",
    "k": 5
  }'
```

### Example 2: Vector Search Only

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "deep neural networks",
    "k": 10,
    "search_type": "vector"
  }'
```

### Example 3: Full-Text Search Only

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "Python programming",
    "k": 5,
    "search_type": "fulltext"
  }'
```

### Example 4: Hybrid Search with Custom Weighting

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "natural language processing",
    "k": 10,
    "search_type": "hybrid",
    "alpha": 0.7
  }'
```
(alpha=0.7 favors vector search over keyword search)

## Performance Considerations

### Embedding Generation
- **Cost**: ~$0.00002 per 1K tokens (text-embedding-3-small)
- **Speed**: ~1000 texts/minute in batches of 100
- **Recommendation**: Process documents in background (Celery)

### Vector Search
- **FAISS IndexFlatL2**: Exact search, best for < 1M vectors
- **Speed**: Sub-millisecond for 10K vectors, ~10ms for 1M vectors
- **Memory**: ~6MB per 1000 vectors (1536 dimensions)

### Full-Text Search
- **PostgreSQL GIN index**: Fast for keyword queries
- **Speed**: ~10-50ms depending on corpus size
- **Recommendation**: Use for exact keyword matching

### Hybrid Search
- **Typical latency**: 200-500ms (embedding generation + 2x search + fusion)
- **Recommendation**: Use for best quality results

## Scaling Recommendations

### For 100K+ Documents:

1. **Use IVF index** for faster approximate search:
   ```python
   # Replace IndexFlatL2 with IndexIVFFlat
   nlist = 100  # Number of clusters
   quantizer = faiss.IndexFlatL2(dimension)
   index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
   ```

2. **Add Redis caching** for frequent queries:
   ```python
   # Cache query embeddings for 1 hour
   redis.setex(f"embedding:{query_hash}", 3600, embedding)
   ```

3. **Implement async embedding** with queuing:
   ```python
   # Queue embedding jobs instead of synchronous generation
   ```

4. **Consider pgvector** for PostgreSQL-native vector search:
   ```sql
   CREATE EXTENSION vector;
   ALTER TABLE chunks ADD COLUMN embedding vector(1536);
   CREATE INDEX ON chunks USING ivfflat (embedding);
   ```

## Troubleshooting

### Issue: "FAISS index is empty"

**Solution:** Process at least one document first. Check Celery worker logs for errors.

```bash
# Check index stats
python -c "from app.services.vector_index import vector_index; print(vector_index.get_stats())"
```

### Issue: Full-text search returns no results

**Solution:** Ensure FTS index is created:

```bash
python scripts/add_fts_index.py
```

Verify:
```sql
SELECT * FROM pg_indexes WHERE indexname = 'idx_chunks_content_fts';
```

### Issue: OpenAI API errors

**Possible causes:**
- Invalid API key
- Rate limiting
- Network issues

**Solution:** Check `.env` file and API key validity. Monitor Celery logs for detailed error messages.

### Issue: Out of memory with large documents

**Solution:** Reduce batch size for embedding generation:

```python
# In app/tasks/document_tasks.py
embeddings = embedding_service.embed_batch(chunk_texts, batch_size=50)  # Reduce from 100
```

## Query Logging & Analytics

All queries are logged to the `query_logs` table:

```sql
SELECT
    query_id,
    query_text,
    result_count,
    response_time_ms,
    created_at
FROM query_logs
ORDER BY created_at DESC
LIMIT 10;
```

**Analytics queries:**

Most common searches:
```sql
SELECT query_text, COUNT(*) as count
FROM query_logs
GROUP BY query_text
ORDER BY count DESC
LIMIT 10;
```

Average response time:
```sql
SELECT AVG(response_time_ms) as avg_response_time
FROM query_logs;
```

## Security

### Access Control
- Users can only search their own documents (unless admin)
- Implemented in `SearchService._filter_by_user_access()`
- Document ownership checked at query time

### Data Privacy
- Embeddings sent to OpenAI API (consider privacy implications)
- For sensitive data, use local embedding models (sentence-transformers)

## Future Enhancements

Phase 4+ could include:
- **HyDE (Hypothetical Document Embeddings)**: Generate hypothetical answers before search
- **Cross-encoder re-ranking**: Re-rank top results with better model
- **Query expansion**: Enhance queries with synonyms
- **Multi-modal search**: Search across text, images, and audio
- **Contextual chunking**: Preserve document structure in chunks
- **Incremental updates**: Update index without full rebuild

## API Documentation

Full API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run search tests:
```bash
pytest tests/test_search.py -v
```

Test coverage includes:
- Embedding service (mocked OpenAI calls)
- Vector index operations
- Search service (vector, fulltext, hybrid)
- Access control filtering
