### Phase 4: RAG (Retrieval-Augmented Generation)

## Overview

Phase 4 implements RAG answer generation using GPT-4, combining retrieval from Phase 3 with language model generation to produce accurate, cited answers to user questions.

## Features

### 1. Answer Generation with Citations
- **GPT-4 integration**: Uses OpenAI's GPT-4o-mini (or GPT-4o/GPT-4-turbo)
- **Citation tracking**: Automatically extracts and validates [1], [2], etc. citations
- **Context-aware**: Answers based only on retrieved documents
- **Configurable parameters**: Temperature, max tokens, model selection

### 2. Streaming Support
- **Real-time responses**: Stream answer chunks as they're generated
- **Server-Sent Events (SSE)**: Standard streaming protocol
- **Progress updates**: Search status, sources, answer chunks, citations
- **Better UX**: Users see partial answers immediately

### 3. Citation Management
- **Automatic extraction**: Find citation markers in generated text
- **Validation**: Ensure citations reference valid sources
- **Metadata mapping**: Link citations to source documents
- **Multiple formats**: Markdown, HTML, plain text

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Endpoint (/rag/answer)                │
└───────────────────────┬─────────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│  Search Service  │        │  RAG Generator   │
│  (Phase 3)       │        │  (GPT-4)         │
└────────┬─────────┘        └────────┬─────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│ Retrieved Chunks │───────>│  Format Context  │
│ (Top-k Results)  │        │  with Citations  │
└──────────────────┘        └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │  GPT-4 Generate  │
                            │  Answer + [1][2] │
                            └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ Citation Tracker │
                            │ Extract & Validate│
                            └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │  Final Response  │
                            │  Answer + Sources│
                            └──────────────────┘
```

## Components

### 1. RAG Generator (`app/services/generator.py`)

Generates answers using GPT-4 with retrieved context.

**Key Methods:**

```python
from app.services.generator import rag_generator

# Non-streaming generation
result = rag_generator.generate(
    query="What is machine learning?",
    search_results=search_results,
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=1000
)

# Returns:
{
    "answer": "Machine learning is a subset of AI [1]...",
    "citations": [...],
    "model": "gpt-4o-mini",
    "usage": {
        "prompt_tokens": 500,
        "completion_tokens": 200,
        "total_tokens": 700
    }
}

# Streaming generation
for chunk in rag_generator.generate_stream(
    query="What is machine learning?",
    search_results=search_results
):
    print(chunk, end="", flush=True)
```

**System Prompt:**
The generator uses a carefully crafted system prompt that:
- Instructs the model to answer only from provided context
- Requires citation markers [1], [2], etc.
- Handles cases with insufficient information
- Ensures accuracy and precision

### 2. Citation Tracker (`app/services/citation_tracker.py`)

Manages citation extraction, validation, and formatting.

**Key Methods:**

```python
from app.services.citation_tracker import citation_tracker

# Extract citation numbers
text = "ML is AI [1]. DL is ML [2][3]."
citations = citation_tracker.extract_citations(text)
# Returns: [1, 2, 3]

# Validate citations
is_valid, errors = citation_tracker.validate_citations(
    text=text,
    max_citation_number=5
)

# Map citations to sources
citation_data = citation_tracker.map_citations_to_sources(
    text=text,
    search_results=search_results
)

# Get statistics
stats = citation_tracker.get_citation_statistics(
    text=text,
    search_results=search_results
)
# Returns: {
#     "total_citations": 3,
#     "unique_citations": 3,
#     "sources_cited": 3,
#     "coverage_percentage": 60.0,
#     ...
# }
```

### 3. RAG Endpoint (`POST /rag/answer`)

Main endpoint for generating answers with citations.

**Request:**
```json
{
  "q": "What is machine learning and how does it work?",
  "k": 5,
  "search_type": "hybrid",
  "alpha": 0.5,
  "model": "gpt-4o-mini",
  "temperature": 0.3,
  "max_tokens": 1000,
  "stream": false
}
```

**Parameters:**
- `q` (required): Question to answer (1-1000 chars)
- `k` (optional): Number of context chunks (1-20, default: 5)
- `search_type` (optional): "vector", "fulltext", or "hybrid" (default: "hybrid")
- `alpha` (optional): Vector weight 0-1 (default: 0.5)
- `model` (optional): "gpt-4o-mini", "gpt-4o", "gpt-4-turbo" (default: "gpt-4o-mini")
- `temperature` (optional): Sampling temperature 0-2 (default: 0.3)
- `max_tokens` (optional): Max response tokens 100-4000 (default: 1000)
- `stream` (optional): Enable streaming (default: false)

**Response:**
```json
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "query_text": "What is machine learning and how does it work?",
  "answer": "Machine learning is a subset of artificial intelligence that enables systems to learn from data without explicit programming [1]. It works by using algorithms that identify patterns in data and make predictions or decisions based on those patterns [2]. The process involves training models on large datasets, which allows them to improve their performance over time [3].",
  "citations": [
    {
      "number": 1,
      "chunk_id": 42,
      "document_id": 7,
      "document_filename": "ml_introduction.pdf",
      "page_number": 2,
      "chunk_index": 3,
      "score": 0.92,
      "content_preview": "Machine learning is a subset of artificial intelligence that enables systems to learn from data..."
    },
    {
      "number": 2,
      "chunk_id": 45,
      "document_id": 7,
      "document_filename": "ml_introduction.pdf",
      "page_number": 3,
      "chunk_index": 6,
      "score": 0.88,
      "content_preview": "ML algorithms identify patterns in data and make predictions..."
    },
    {
      "number": 3,
      "chunk_id": 51,
      "document_id": 8,
      "document_filename": "deep_learning.pdf",
      "page_number": 1,
      "chunk_index": 0,
      "score": 0.85,
      "content_preview": "Training models on large datasets allows them to improve..."
    }
  ],
  "sources": [
    {
      "chunk_id": 42,
      "document_id": 7,
      "document_filename": "ml_introduction.pdf",
      "content": "Machine learning is a subset of artificial intelligence...",
      "chunk_index": 3,
      "page_number": 2,
      "score": 0.92,
      "rank": 1
    }
    // ... more sources
  ],
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 856,
    "completion_tokens": 143,
    "total_tokens": 999
  },
  "response_time_ms": 2341.5,
  "search_time_ms": 234.8,
  "generation_time_ms": 2100.2
}
```

### 4. Streaming Endpoint (`POST /rag/answer/stream`)

Real-time answer streaming with Server-Sent Events.

**Event Types:**

1. **Search Status:**
```json
{"type": "status", "message": "Searching documents..."}
```

2. **Search Complete:**
```json
{"type": "search_complete", "sources_found": 5, "time_ms": 234.5}
```

3. **Sources:**
```json
{
  "type": "sources",
  "sources": [
    {"chunk_id": 42, "document_filename": "ml.pdf", "page_number": 2},
    ...
  ]
}
```

4. **Answer Chunks:**
```json
{"type": "answer_chunk", "content": "Machine learning "}
{"type": "answer_chunk", "content": "is a subset "}
{"type": "answer_chunk", "content": "of AI [1]."}
```

5. **Citations:**
```json
{
  "type": "citations",
  "citations": [
    {"number": 1, "document_filename": "ml.pdf", "page_number": 2, ...},
    ...
  ]
}
```

6. **Completion:**
```json
{
  "type": "done",
  "query_id": "550e8400-...",
  "response_time_ms": 2500.0,
  "search_time_ms": 250.0,
  "generation_time_ms": 2200.0
}
```

## Setup Instructions

### Prerequisites
- Phase 3 completed (embeddings & search working)
- OpenAI API key with GPT-4 access

### No Additional Dependencies
Phase 4 uses the same `openai` package as Phase 3, so no new installations needed!

### Start Services

```bash
# Terminal 1 - FastAPI Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info
```

The new `/rag/answer` and `/rag/answer/stream` endpoints are automatically available.

## Usage Examples

### Example 1: Basic RAG Query

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What are the key features of Python programming language?",
    "k": 5
  }'
```

### Example 2: High-Quality Answer (GPT-4o)

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "Explain the difference between supervised and unsupervised learning",
    "k": 10,
    "model": "gpt-4o",
    "temperature": 0.2,
    "max_tokens": 1500
  }'
```

### Example 3: Creative Answer

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "How can machine learning be applied in healthcare?",
    "k": 8,
    "temperature": 0.7,
    "max_tokens": 1200
  }'
```

### Example 4: Streaming Response

```bash
curl -X POST http://localhost:8000/rag/answer/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What is deep learning?",
    "k": 5,
    "stream": true
  }' \
  --no-buffer
```

### Example 5: Vector Search Only for RAG

```bash
curl -X POST http://localhost:8000/rag/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What is neural architecture search?",
    "k": 5,
    "search_type": "vector",
    "alpha": 1.0
  }'
```

## JavaScript/TypeScript Client Example

```typescript
// Non-streaming request
async function askQuestion(question: string, token: string) {
  const response = await fetch('http://localhost:8000/rag/answer', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      q: question,
      k: 5,
      model: 'gpt-4o-mini',
      temperature: 0.3
    })
  });

  const data = await response.json();

  console.log('Answer:', data.answer);
  console.log('Citations:', data.citations);
  console.log('Response time:', data.response_time_ms, 'ms');

  return data;
}

// Streaming request with EventSource
function askQuestionStream(question: string, token: string) {
  const eventSource = new EventSource(
    `http://localhost:8000/rag/answer/stream?token=${token}`
  );

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'status':
        console.log('Status:', data.message);
        break;
      case 'search_complete':
        console.log(`Found ${data.sources_found} sources`);
        break;
      case 'sources':
        console.log('Sources:', data.sources);
        break;
      case 'answer_chunk':
        process.stdout.write(data.content); // Print incrementally
        break;
      case 'citations':
        console.log('\nCitations:', data.citations);
        break;
      case 'done':
        console.log(`\nCompleted in ${data.response_time_ms}ms`);
        eventSource.close();
        break;
      case 'error':
        console.error('Error:', data.message);
        eventSource.close();
        break;
    }
  };

  eventSource.onerror = (error) => {
    console.error('Stream error:', error);
    eventSource.close();
  };
}
```

## Performance & Costs

### Response Time Breakdown

Typical RAG request (5 chunks, GPT-4o-mini):
- **Search**: 200-500ms
  - Vector search: 10-50ms
  - Full-text search: 10-50ms
  - Result fusion: 150-400ms
- **Generation**: 1500-3000ms
  - Prompt formatting: <10ms
  - GPT-4 API call: 1500-3000ms
- **Citation extraction**: <10ms
- **Total**: ~2-4 seconds

### OpenAI API Costs

**GPT-4o-mini** (Recommended):
- Input: $0.150 per 1M tokens
- Output: $0.600 per 1M tokens
- Typical RAG request (~1000 prompt tokens, ~200 completion tokens):
  - Cost: $0.00027 per request
  - **~3,700 requests per $1**

**GPT-4o**:
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens
- Same request: $0.0045 per request
  - ~220 requests per $1

**Recommendation**: Use GPT-4o-mini for most queries. Reserve GPT-4o for complex questions requiring deeper reasoning.

### Token Usage Optimization

**Context Management:**
```python
# Retrieve 5 chunks instead of 20 to reduce prompt tokens
"k": 5  # vs "k": 20

# Shorter max_tokens saves generation cost
"max_tokens": 500  # vs "max_tokens": 2000
```

**Chunk Size:**
- Default: 512 tokens per chunk
- 5 chunks = ~2560 tokens of context
- Add ~500 tokens for system/user prompt
- Total prompt: ~3000 tokens

## Best Practices

### 1. Question Formulation
**Good questions:**
- "What is machine learning and how does it work?"
- "What are the differences between Python and JavaScript?"
- "Explain the benefits of cloud computing"

**Poor questions:**
- "ML" (too vague)
- "Tell me everything about AI" (too broad)
- "What's the weather?" (not in documents)

### 2. Parameter Tuning

**For factual questions:**
```json
{
  "temperature": 0.1,
  "max_tokens": 500,
  "k": 5,
  "model": "gpt-4o-mini"
}
```

**For creative/explanatory answers:**
```json
{
  "temperature": 0.7,
  "max_tokens": 1500,
  "k": 10,
  "model": "gpt-4o"
}
```

### 3. Citation Validation

Always validate that:
- All citations in answer refer to actual sources
- Citation numbers are sequential [1], [2], [3]
- No citations point beyond available sources

The `CitationTracker` handles this automatically.

### 4. Error Handling

**No relevant documents:**
```json
{
  "answer": "I don't have any relevant documents to answer this question."
}
```

**API errors:**
- Caught and returned as HTTP 500
- Logged for debugging
- User sees error message

## Troubleshooting

### Issue: "I don't have any relevant documents"

**Causes:**
1. No documents uploaded for this topic
2. Search failed to find relevant chunks
3. User doesn't own documents on this topic

**Solutions:**
1. Upload relevant documents
2. Try rephrasing the question
3. Check user permissions (admins see all documents)

### Issue: Slow response times (>10 seconds)

**Causes:**
1. Large `k` value (many chunks)
2. Long `max_tokens`
3. Cold start for GPT-4

**Solutions:**
```json
{
  "k": 3,              // Reduce from 10
  "max_tokens": 500,    // Reduce from 2000
  "model": "gpt-4o-mini" // Faster than gpt-4o
}
```

### Issue: Citations missing or incorrect

**Cause:** Model didn't follow citation instructions

**Solution:** This is rare with GPT-4. If it happens:
1. Lower temperature (0.1-0.3 is more reliable)
2. Use gpt-4o instead of gpt-4o-mini
3. Check system prompt formatting

### Issue: OpenAI API rate limits

**Symptoms:** HTTP 429 errors

**Solutions:**
1. Implement exponential backoff (TODO: add to generator.py)
2. Queue requests with Celery
3. Upgrade OpenAI API tier
4. Cache common queries

## Security

### Access Control
- Users can only query their own documents (unless admin)
- Citations filtered by document ownership
- Query logs include user attribution

### Data Privacy
- Questions and answers sent to OpenAI
- Consider using Azure OpenAI for enterprise data privacy
- For sensitive data, use local LLMs (Llama, Mistral)

### Rate Limiting
TODO: Implement per-user rate limiting:
```python
# Recommended: 10 RAG requests per minute per user
# 100 RAG requests per hour per user
```

## Future Enhancements

### Phase 5+ Ideas:

1. **Query Expansion**
   - Reformulate questions for better retrieval
   - Generate multiple query variations

2. **Re-ranking**
   - Cross-encoder re-ranking of search results
   - Prioritize most relevant chunks

3. **Conversation History**
   - Multi-turn conversations
   - Context persistence across queries

4. **Answer Validation**
   - Fact-checking against sources
   - Confidence scoring

5. **Multi-modal Answers**
   - Include images from PDFs
   - Extract tables and charts

6. **Local LLM Support**
   - Llama 3, Mistral, Phi
   - Privacy-first deployment

## Testing

Run RAG tests:
```bash
pytest tests/test_rag.py -v
```

Test coverage:
- RAG generator (mocked OpenAI)
- Citation tracker
- Citation extraction and validation
- Full RAG pipeline integration

## API Documentation

Interactive documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Search for `/rag/answer` endpoints.

## Summary

Phase 4 transforms DocQuery from a search system into an intelligent Q&A system:

✅ **Retrieval** (Phase 3) + **Generation** (Phase 4) = **RAG**
✅ **Accurate answers** with source citations
✅ **Real-time streaming** for better UX
✅ **Cost-effective** with GPT-4o-mini
✅ **Production-ready** with error handling and logging

The system can now:
1. Find relevant documents (hybrid search)
2. Generate accurate answers (GPT-4)
3. Track citations ([1], [2], etc.)
4. Stream responses in real-time
5. Log queries for analytics
