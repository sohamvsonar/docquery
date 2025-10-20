/**
 * Axios API client with JWT token interceptors
 * Handles authentication, token refresh, and error handling
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";
import type {
  LoginRequest,
  TokenResponse,
  UserResponse,
  DocumentResponse,
  UploadResponse,
  DocumentListResponse,
  SearchResult,
  RAGRequest,
  RAGResponse,
  CacheStats,
  APIError,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
});

// Token management
let accessToken: string | null = null;
let refreshToken: string | null = null;

export const setTokens = (access: string, refresh: string) => {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  }
};

export const getTokens = () => {
  if (typeof window !== "undefined" && !accessToken) {
    accessToken = localStorage.getItem("access_token");
    refreshToken = localStorage.getItem("refresh_token");
  }
  return { accessToken, refreshToken };
};

export const clearTokens = () => {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }
};

// Request interceptor - add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const tokens = getTokens();
    if (tokens.accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${tokens.accessToken}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // If 401 and we haven't retried yet, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const tokens = getTokens();
        if (tokens.refreshToken) {
          // TODO: Implement refresh token endpoint
          // For now, just clear tokens and redirect to login
          clearTokens();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      } catch (refreshError) {
        clearTokens();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ===========================
// Authentication API
// ===========================

export const authAPI = {
  login: async (credentials: LoginRequest): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>("/auth/login", credentials);
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  logout: async (): Promise<void> => {
    try {
      await api.post("/auth/logout");
    } finally {
      clearTokens();
    }
  },

  getCurrentUser: async (): Promise<UserResponse> => {
    const { data } = await api.get<UserResponse>("/auth/me");
    return data;
  },
};

// ===========================
// Documents API
// ===========================

export const documentsAPI = {
  upload: async (file: File, onUploadProgress?: (progress: number) => void): Promise<DocumentResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const { data } = await api.post<UploadResponse>("/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onUploadProgress(progress);
        }
      },
    });

    // Convert UploadResponse to DocumentResponse format
    return {
      id: data.document_id,
      filename: data.filename,
      original_filename: data.original_filename,
      file_size: data.file_size,
      mime_type: null,
      status: data.status as "pending" | "processing" | "completed" | "failed",
      job_id: data.job_id,
      owner_id: 0, // Will be set by backend
      created_at: new Date().toISOString(),
      processed_at: null,
      error_message: null,
    };
  },

  list: async (): Promise<DocumentResponse[]> => {
    const { data } = await api.get<DocumentListResponse>("/upload");
    return data.documents;
  },

  delete: async (documentId: number): Promise<void> => {
    await api.delete(`/upload/${documentId}`);
  },

  getStatus: async (documentId: number): Promise<DocumentResponse> => {
    const { data } = await api.get<DocumentResponse>(`/upload/${documentId}`);
    return data;
  },
};

// ===========================
// Search API
// ===========================

export const searchAPI = {
  search: async (
    query: string,
    k: number = 10,
    searchType: "vector" | "fulltext" | "hybrid" = "hybrid",
    alpha: number = 0.5
  ): Promise<SearchResult[]> => {
    const { data } = await api.post<SearchResult[]>("/query/search", {
      q: query,
      k,
      search_type: searchType,
      alpha,
    });
    return data;
  },
};

// ===========================
// RAG API
// ===========================

export const ragAPI = {
  generateAnswer: async (request: RAGRequest): Promise<RAGResponse> => {
    const { data } = await api.post<RAGResponse>("/rag/answer", request);
    return data;
  },

  generateAnswerStream: async (
    request: RAGRequest,
    onChunk: (chunk: string) => void,
    onComplete: (response: RAGResponse) => void,
    onError: (error: Error) => void
  ): Promise<void> => {
    try {
      const tokens = getTokens();
      console.log('[RAG] Sending request:', { url: `${API_URL}/rag/answer/stream`, request, hasToken: !!tokens.accessToken });

      const response = await fetch(`${API_URL}/rag/answer/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokens.accessToken}`,
        },
        body: JSON.stringify(request),
      });

      console.log('[RAG] Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[RAG] Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("Response body is null");
      }

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");

        // Process all complete lines
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line.startsWith("data: ")) {
            const data = line.slice(6);

            if (data === "[DONE]") {
              continue;
            }

            try {
              const parsed = JSON.parse(data);
              console.log('[RAG] SSE event:', parsed.type, parsed);

              if (parsed.type === "answer_chunk") {
                onChunk(parsed.content);
              } else if (parsed.type === "done") {
                // Streaming complete - we'll keep the accumulated answer
                // The full answer is already built from chunks
                continue;
              } else if (parsed.type === "citations") {
                // Citations received - create a response object
                const citations = (parsed.citations || []).map((cit: any) => ({
                  id: cit.number,
                  document_id: 0,
                  filename: cit.document_filename,
                  page_number: cit.page_number,
                  content: cit.content_preview
                }));

                const response: RAGResponse = {
                  query_id: parsed.query_id || "",
                  query_text: request.q,
                  answer: "", // Will be filled from accumulated chunks
                  citations: citations,
                  sources: [],
                  model: request.model || "gpt-4o-mini",
                  usage: {},
                  response_time_ms: 0,
                  search_time_ms: 0,
                  generation_time_ms: 0
                };
                onComplete(response);
              } else if (parsed.type === "error") {
                throw new Error(parsed.message);
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e);
            }
          }
        }

        // Keep the last incomplete line in the buffer
        buffer = lines[lines.length - 1];
      }
    } catch (error) {
      onError(error as Error);
    }
  },
};

// ===========================
// Users API (Admin only)
// ===========================

export const usersAPI = {
  list: async (): Promise<UserResponse[]> => {
    const { data } = await api.get<{ users: UserResponse[]; total: number }>("/users");
    return data.users;
  },

  create: async (userData: {
    username: string;
    email?: string;
    password: string;
    is_admin: boolean;
  }): Promise<UserResponse> => {
    const { data } = await api.post<UserResponse>("/users", userData);
    return data;
  },

  delete: async (userId: number): Promise<void> => {
    await api.delete(`/users/${userId}`);
  },

  get: async (userId: number): Promise<UserResponse> => {
    const { data } = await api.get<UserResponse>(`/users/${userId}`);
    return data;
  },
};

// ===========================
// Cache API (Admin only)
// ===========================

export const cacheAPI = {
  getStats: async (): Promise<CacheStats> => {
    const { data } = await api.get<{ cache_stats: CacheStats }>("/cache/stats");
    return data.cache_stats;
  },

  clearAll: async (): Promise<void> => {
    await api.post("/cache/clear");
  },

  clearQuery: async (): Promise<void> => {
    await api.post("/cache/clear/query");
  },

  clearEmbeddings: async (): Promise<void> => {
    await api.post("/cache/clear/embeddings");
  },
};

export default api;
