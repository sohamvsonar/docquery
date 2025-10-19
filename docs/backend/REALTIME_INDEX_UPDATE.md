# Real-Time FAISS Index Updates

## Problem

When uploading a new document, the RAG query would return "I don't have information in the provided documents" until the FastAPI server was restarted.

## Root Cause

**The Issue:**
1. FastAPI server loads FAISS index into memory at startup
2. When a new document is uploaded, Celery worker processes it:
   - Generates embeddings
   - Adds vectors to index
   - Saves index to disk
3. FastAPI server still has **old index in memory**
4. RAG queries use the old in-memory index → new documents not found
5. Restart FastAPI → loads fresh index from disk → documents found ✓

**Why This Happened:**
The `VectorIndexManager` is a global singleton (`vector_index = VectorIndexManager()`) that's created when the module is imported. Each process (FastAPI server, Celery worker) has its own separate Python process and memory space.

```
┌─────────────────────────────────────────────────────────┐
│                      Before Fix                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  FastAPI Process              Celery Worker Process     │
│  ┌──────────────┐             ┌──────────────┐         │
│  │ FAISS Index  │             │ FAISS Index  │         │
│  │ (in memory)  │             │ (in memory)  │         │
│  │              │             │              │         │
│  │ 10 vectors   │             │ 10 vectors   │         │
│  └──────────────┘             └──────┬───────┘         │
│         │                            │                  │
│         │                            │ Add new vectors  │
│         │                            ▼                  │
│         │                     ┌──────────────┐         │
│         │                     │ 15 vectors   │         │
│         │                     └──────┬───────┘         │
│         │                            │                  │
│         │                            │ Save to disk     │
│         │                            ▼                  │
│         │                     ┌──────────────┐         │
│         │                     │  Disk File   │         │
│         │                     │  15 vectors  │         │
│         │                     └──────────────┘         │
│         │                                               │
│  Query uses old index (10 vectors) ✗                   │
│  New documents not found!                               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Solution

Implemented **automatic index reloading** by checking if the index file has been modified before each search operation.

### How It Works

1. Track index file modification time (`mtime`)
2. Before each search, check if index file has been updated
3. If updated, reload index from disk
4. Use fresh index for search

```python
def _check_and_reload_index(self):
    """Check if index file has been modified and reload if needed."""
    if not os.path.exists(self.index_path):
        return

    current_mtime = os.path.getmtime(self.index_path)

    # If modification time changed, reload the index
    if self._index_mtime is None or current_mtime > self._index_mtime:
        logger.info("Index file updated, reloading...")
        self.load_index()

def search(self, query_embedding, k=10):
    """Search with automatic index reload."""
    # Auto-reload if index updated
    self._check_and_reload_index()

    # Perform search
    # ...
```

### After Fix

```
┌─────────────────────────────────────────────────────────┐
│                       After Fix                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  FastAPI Process              Celery Worker Process     │
│  ┌──────────────┐             ┌──────────────┐         │
│  │ FAISS Index  │             │ FAISS Index  │         │
│  │ (in memory)  │             │ (in memory)  │         │
│  │ 10 vectors   │             │ 10 vectors   │         │
│  └──────────────┘             └──────┬───────┘         │
│         │                            │                  │
│         │                            │ Add new vectors  │
│         │                            ▼                  │
│         │                     ┌──────────────┐         │
│         │                     │ 15 vectors   │         │
│         │                     └──────┬───────┘         │
│         │                            │                  │
│         │                            │ Save to disk     │
│         │                            ▼                  │
│         │                     ┌──────────────┐         │
│         │◄────────────────────│  Disk File   │         │
│         │  Reload if modified │  15 vectors  │         │
│         │                     └──────────────┘         │
│         │                                               │
│  Query checks mtime → Reloads index → 15 vectors ✓     │
│  New documents found immediately!                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Changes Made

### File: `app/services/vector_index.py`

**1. Added `_index_mtime` tracking:**
```python
def __init__(self, ...):
    # ...
    # Track index file modification time for auto-reload
    self._index_mtime = None
```

**2. Update mtime when loading:**
```python
def load_index(self):
    # ... load index ...

    # Update modification time
    self._index_mtime = os.path.getmtime(self.index_path)
```

**3. Added auto-reload check:**
```python
def _check_and_reload_index(self):
    """Check if index file has been modified and reload if needed."""
    if not os.path.exists(self.index_path):
        return

    try:
        current_mtime = os.path.getmtime(self.index_path)

        # If modification time changed, reload the index
        if self._index_mtime is None or current_mtime > self._index_mtime:
            logger.info(f"Index file updated (mtime: {current_mtime}), reloading...")
            self.load_index()
    except Exception as e:
        logger.warning(f"Failed to check index modification time: {e}")
```

**4. Call reload check before search:**
```python
def search(self, query_embedding, k=10):
    """Search with automatic index reload."""
    # Auto-reload index if it has been updated
    self._check_and_reload_index()

    # ... perform search ...
```

## Performance Impact

**Index Reload Cost:**
- File stat check (`os.path.getmtime`): ~0.1-1 ms
- Index reload (if needed): ~10-100 ms depending on index size

**When Reload Happens:**
- Only when index file is actually modified
- Typically once per document upload
- Not on every query (only first query after update)

**Example Timeline:**
```
Time 0ms:   Upload document
Time 1000ms: Celery processes document
Time 5000ms: Celery saves index to disk
Time 5001ms: First query after upload
             - Check mtime: 0.5ms
             - Reload index: 50ms
             - Perform search: 20ms
             - Total: ~70ms
Time 5100ms: Second query
             - Check mtime: 0.5ms (no reload needed)
             - Perform search: 20ms
             - Total: ~20ms
```

**Trade-off:** Small overhead (~0.5ms per query) for real-time updates. Worth it!

## Testing

### Test Real-Time Updates

1. **Start services:**
```bash
# Terminal 1
uvicorn app.main:app --reload

# Terminal 2
celery -A app.tasks.celery_app worker --loglevel=info
```

2. **Upload a document:**
```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"
```

3. **Wait for processing:**
Watch Celery logs for:
```
Successfully processed document 1: 10 chunks created, 10 embeddings generated
```

4. **Query immediately** (no restart needed):
```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"q": "What is in test.pdf?", "k": 5}'
```

5. **Check FastAPI logs:**
You should see:
```
Index file updated (mtime: 1234567890.123), reloading...
Loaded index with 10 vectors from uploads/indexes/faiss_index.bin
```

**Result:** Answer with citations from the newly uploaded document ✓

## Alternative Solutions (Not Implemented)

### 1. Shared Memory Index
Use shared memory between processes (e.g., `multiprocessing.shared_memory`).

**Pros:** Zero reload cost
**Cons:** Complex, platform-specific, memory management issues

### 2. Redis/Memcached for Index
Store index in Redis.

**Pros:** Distributed, scalable
**Cons:** Network overhead, serialization cost, FAISS doesn't natively support this

### 3. Index Service (Separate Process)
Run FAISS index as a separate service with gRPC/HTTP API.

**Pros:** Single source of truth, microservice architecture
**Cons:** Added complexity, network latency, deployment overhead

### 4. Celery Result Backend
Use Celery result backend to notify FastAPI when index updated.

**Pros:** Event-driven, no polling
**Cons:** Complex, requires message broker integration

**Why We Chose File Modification Check:**
- ✅ Simple and reliable
- ✅ No additional dependencies
- ✅ Works across all platforms
- ✅ Low overhead (~0.5ms)
- ✅ No complex inter-process communication
- ✅ Easy to understand and maintain

## Monitoring

### Check Index Reload Frequency

Look for these log messages in FastAPI logs:
```
Index file updated (mtime: ...), reloading...
Loaded index with N vectors from uploads/indexes/faiss_index.bin
```

### If You See Frequent Reloads

**Symptom:** Index reloading on every query

**Cause:** Index file being continuously modified (shouldn't happen normally)

**Debug:**
```bash
# Check index file modification time
stat uploads/indexes/faiss_index.bin

# Watch for changes
watch -n 1 stat uploads/indexes/faiss_index.bin
```

**Fix:** Check Celery worker - it should only save index after document processing, not continuously.

## Future Enhancements

For very high-traffic deployments (1000+ queries/second), consider:

1. **Cache reload check**: Only check mtime every N seconds instead of every query
2. **Background reload thread**: Reload index in background without blocking queries
3. **Index versioning**: Use version numbers instead of mtime
4. **Distributed index service**: Separate FAISS service with load balancing

For most use cases, the current solution is sufficient and performs well.

## Summary

✅ **Problem:** New documents not found until server restart
✅ **Cause:** Stale in-memory FAISS index
✅ **Solution:** Auto-reload index before search if file modified
✅ **Impact:** ~0.5ms overhead per query, real-time updates
✅ **Result:** No restart needed, documents searchable immediately after upload
