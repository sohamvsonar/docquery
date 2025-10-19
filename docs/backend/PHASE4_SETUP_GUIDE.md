# Phase 4 Setup Guide - RAG Generation

## Quick Start

Phase 4 adds answer generation with citations using GPT-4. **No new dependencies required** - uses the same OpenAI package from Phase 3!

## Prerequisites

- ✅ Phase 3 completed (embeddings & search working)
- ✅ OpenAI API key configured
- ✅ Documents uploaded and processed
- ✅ FastAPI server running
- ✅ Celery worker running

## Step-by-Step Setup

### 1. Verify OpenAI API Key

Check your `.env` file:
```env
OPENAI_API_KEY=sk-...your-key-here...
```

The same key used for embeddings works for GPT-4!

### 2. Restart FastAPI Server

The RAG endpoints are automatically available after restart:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see in logs:
```
INFO: Application startup complete.
```

### 3. Test RAG Endpoint

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

#### Test Basic RAG Query

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What is DocQuery?",
    "k": 5
  }'
```

**Expected response:**
```json
{
  "query_id": "550e8400-...",
  "query_text": "What is DocQuery?",
  "answer": "DocQuery is a document intelligence system that enables semantic search and question answering across your documents [1]. It combines document processing, vector embeddings, and GPT-4 to provide accurate answers with citations [2].",
  "citations": [
    {
      "number": 1,
      "chunk_id": 3,
      "document_filename": "README.md",
      "page_number": null,
      "content_preview": "DocQuery is a document intelligence system..."
    },
    {
      "number": 2,
      "chunk_id": 5,
      "document_filename": "README.md",
      "page_number": null,
      "content_preview": "It combines document processing..."
    }
  ],
  "sources": [...],
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 523,
    "completion_tokens": 87,
    "total_tokens": 610
  },
  "response_time_ms": 2341.5
}
```

#### Test Streaming

```bash
curl -X POST http://localhost:8000/rag/answer/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "How does the system work?",
    "k": 5
  }' \
  --no-buffer
```

You should see real-time events:
```
data: {"type":"status","message":"Searching documents..."}

data: {"type":"search_complete","sources_found":5,"time_ms":234.5}

data: {"type":"answer_chunk","content":"The "}

data: {"type":"answer_chunk","content":"system "}

data: {"type":"answer_chunk","content":"works "}

...

data: {"type":"done","query_id":"...","response_time_ms":2500.0}
```

## Verification Checklist

- [ ] FastAPI server running with RAG endpoints
- [ ] OpenAI API key configured
- [ ] Test query returns answer with citations
- [ ] Streaming works (real-time chunks)
- [ ] Citations include valid source metadata
- [ ] Response includes token usage stats

## Available Endpoints

### 1. POST /rag/answer (Non-streaming)

Returns complete answer with citations in one response.

**When to use:** Simple integrations, batch processing, mobile apps

### 2. POST /rag/answer/stream (Streaming)

Streams answer chunks in real-time using Server-Sent Events.

**When to use:** Web UIs, chatbots, interactive applications

## Configuration Options

### Model Selection

**gpt-4o-mini** (Default - Recommended):
- Fast: 1-2 seconds
- Cost: ~$0.0003 per request
- Quality: Excellent for most questions

**gpt-4o**:
- Slower: 3-5 seconds
- Cost: ~$0.0045 per request
- Quality: Best for complex reasoning

**gpt-4-turbo**:
- Fast: 2-3 seconds
- Cost: ~$0.015 per request
- Quality: Great for long documents

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "Your question",
    "model": "gpt-4o"
  }'
```

### Temperature Control

**Low temperature (0.1-0.3)** - Factual, deterministic:
```json
{
  "temperature": 0.2
}
```

**Medium temperature (0.5-0.7)** - Balanced:
```json
{
  "temperature": 0.5
}
```

**High temperature (0.8-1.5)** - Creative, diverse:
```json
{
  "temperature": 1.0
}
```

### Context Size

**Few chunks (3-5)** - Fast, focused:
```json
{
  "k": 3
}
```

**Medium chunks (5-10)** - Balanced (default):
```json
{
  "k": 5
}
```

**Many chunks (10-20)** - Comprehensive:
```json
{
  "k": 15
}
```

## Example Use Cases

### Use Case 1: Technical Documentation Q&A

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "How do I configure the database connection?",
    "k": 5,
    "temperature": 0.2,
    "search_type": "hybrid"
  }'
```

### Use Case 2: Research Paper Analysis

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What are the main findings of this research?",
    "k": 10,
    "temperature": 0.3,
    "model": "gpt-4o",
    "max_tokens": 1500
  }'
```

### Use Case 3: Policy Document Search

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What is the policy on remote work?",
    "k": 5,
    "search_type": "fulltext",
    "temperature": 0.1
  }'
```

## Troubleshooting

### Issue: "I don't have any relevant documents"

**Cause:** No documents uploaded or search found no matches.

**Solution:**
1. Check documents are uploaded: `GET /upload`
2. Verify documents processed: Look for `"status": "completed"`
3. Try broader question: "What topics are covered?" instead of specific query
4. Check user permissions (only see own documents unless admin)

### Issue: Slow response (>10 seconds)

**Cause:** Too many chunks or long generation.

**Solution:**
```json
{
  "k": 3,                // Reduce chunks
  "max_tokens": 500,     // Limit response length
  "model": "gpt-4o-mini" // Use faster model
}
```

### Issue: Citations missing [1], [2]

**Rare issue** - GPT-4 is very reliable at following citation instructions.

**If it happens:**
```json
{
  "temperature": 0.1,    // More deterministic
  "model": "gpt-4o"      // Higher quality model
}
```

### Issue: OpenAI API error "insufficient_quota"

**Cause:** No OpenAI API credits.

**Solution:**
1. Check usage: https://platform.openai.com/usage
2. Add credits: https://platform.openai.com/settings/organization/billing

### Issue: OpenAI API error "rate_limit_exceeded"

**Cause:** Too many requests per minute.

**Solution:**
1. Wait 60 seconds and retry
2. Upgrade API tier: https://platform.openai.com/settings/organization/limits
3. Implement request queuing

## What's New in Phase 4?

### Files Added

- `app/services/generator.py` - GPT-4 generation with streaming
- `app/services/citation_tracker.py` - Citation extraction and validation
- `app/routers/rag.py` - RAG endpoints
- `tests/test_rag.py` - RAG tests
- `docs/PHASE4_RAG.md` - Detailed documentation

### Files Updated

- `app/main.py` - Added RAG router
- `app/schemas.py` - Added RAG request/response schemas

### New Capabilities

✅ **Answer generation** with GPT-4
✅ **Citation tracking** [1], [2], etc.
✅ **Streaming responses** with SSE
✅ **Source validation** and metadata
✅ **Multi-model support** (gpt-4o-mini, gpt-4o, gpt-4-turbo)
✅ **Token usage tracking** for cost monitoring

## API Documentation

View interactive docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Look for:
- `POST /rag/answer` - Non-streaming RAG
- `POST /rag/answer/stream` - Streaming RAG

## Cost Estimation

### GPT-4o-mini (Recommended)

**Per request** (avg 1000 prompt tokens, 200 completion tokens):
- Input cost: 1000 tokens × $0.15 / 1M = $0.00015
- Output cost: 200 tokens × $0.60 / 1M = $0.00012
- **Total: $0.00027 per request**

**Monthly usage examples:**
- 100 queries/day = $8.10/month
- 1,000 queries/day = $81/month
- 10,000 queries/day = $810/month

### GPT-4o

**Per request**:
- Input cost: 1000 × $2.50 / 1M = $0.0025
- Output cost: 200 × $10.00 / 1M = $0.002
- **Total: $0.0045 per request**

**Monthly usage:**
- 100 queries/day = $13.50/month
- 1,000 queries/day = $135/month

**Recommendation:** Use gpt-4o-mini for most queries. Reserve gpt-4o for complex questions.

## Next Steps

With Phase 4 complete, you now have:
- ✅ Document upload and processing
- ✅ Multi-modal extraction (PDF, images, audio, text)
- ✅ Vector embeddings and FAISS search
- ✅ Full-text search (PostgreSQL)
- ✅ Hybrid retrieval (RRF fusion)
- ✅ **RAG answer generation with GPT-4**
- ✅ **Citation tracking and validation**
- ✅ **Streaming support**

**Your system is now a complete Document Intelligence Platform!**

## Support

- **Detailed Phase 4 Docs**: [docs/PHASE4_RAG.md](docs/PHASE4_RAG.md)
- **Phase 3 Search Docs**: [docs/PHASE3_SEARCH.md](docs/PHASE3_SEARCH.md)
- **API Documentation**: http://localhost:8000/docs
- **Security Guide**: [docs/SECURE_FILE_STORAGE.md](docs/SECURE_FILE_STORAGE.md)
