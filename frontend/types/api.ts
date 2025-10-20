/**
 * TypeScript types for DocQuery API
 * Matches the backend Pydantic schemas
 */

// Authentication
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  username: string;
  email: string | null;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

// Documents
export interface DocumentResponse {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string | null;
  status: "pending" | "processing" | "completed" | "failed";
  job_id: string;
  owner_id: number;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
}

export interface UploadResponse {
  job_id: string;
  document_id: number;
  filename: string;
  original_filename: string;
  status: string;
  file_size: number;
  message: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
  offset: number;
  limit: number;
}

// Search
export interface SearchResult {
  chunk_id: number;
  document_id: number;
  filename: string;
  content: string;
  page_number: number | null;
  score: number;
  rank: number;
}

// RAG
export interface RAGRequest {
  q: string;
  k?: number;
  search_type?: "vector" | "fulltext" | "hybrid";
  alpha?: number;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface Citation {
  id: number;
  document_id: number;
  filename: string;
  page_number: number | null;
  content: string;
}

export interface SourceDocument {
  document_id: number;
  filename: string;
  citation_count: number;
}

export interface RAGResponse {
  query_id: string;
  query_text: string;
  answer: string;
  citations: Citation[];
  sources: SourceDocument[];
  model: string;
  usage: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  response_time_ms: number;
  search_time_ms: number;
  generation_time_ms: number;
}

// Cache
export interface CacheStats {
  query_cache: {
    hits: number;
    misses: number;
    total: number;
    hit_rate: number;
  };
  embedding_cache: {
    hits: number;
    misses: number;
    total: number;
    hit_rate: number;
  };
}

// API Error
export interface APIError {
  detail: string;
}
