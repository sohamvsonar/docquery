/**
 * Zustand store for document management
 * Handles document upload, listing, deletion, and status polling
 */

import { create } from "zustand";
import { documentsAPI } from "@/lib/api";
import type { DocumentResponse } from "@/types/api";

interface DocumentsState {
  documents: DocumentResponse[];
  isLoading: boolean;
  error: string | null;
  uploadProgress: number;
  isUploading: boolean;

  // Actions
  fetchDocuments: () => Promise<void>;
  uploadDocument: (file: File) => Promise<DocumentResponse | null>;
  deleteDocument: (documentId: number) => Promise<void>;
  refreshDocumentStatus: (documentId: number) => Promise<void>;
  clearError: () => void;
}

export const useDocumentsStore = create<DocumentsState>()((set, get) => ({
  documents: [],
  isLoading: false,
  error: null,
  uploadProgress: 0,
  isUploading: false,

  fetchDocuments: async () => {
    set({ isLoading: true, error: null });

    try {
      const documents = await documentsAPI.list();

      set({
        documents,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || error.message || "Failed to fetch documents";

      set({
        isLoading: false,
        error: errorMessage,
      });
    }
  },

  uploadDocument: async (file: File) => {
    set({ isUploading: true, uploadProgress: 0, error: null });

    try {
      const document = await documentsAPI.upload(file, (progress) => {
        set({ uploadProgress: progress });
      });

      // Add new document to the list
      set((state) => ({
        documents: [document, ...state.documents],
        isUploading: false,
        uploadProgress: 100,
        error: null,
      }));

      return document;
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || error.message || "Failed to upload document";

      set({
        isUploading: false,
        uploadProgress: 0,
        error: errorMessage,
      });

      return null;
    }
  },

  deleteDocument: async (documentId: number) => {
    set({ error: null });

    try {
      await documentsAPI.delete(documentId);

      // Remove document from the list
      set((state) => ({
        documents: state.documents.filter((doc) => doc.id !== documentId),
        error: null,
      }));
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || error.message || "Failed to delete document";

      set({
        error: errorMessage,
      });

      throw new Error(errorMessage);
    }
  },

  refreshDocumentStatus: async (documentId: number) => {
    try {
      const updatedDocument = await documentsAPI.getStatus(documentId);

      // Update the document in the list
      set((state) => ({
        documents: state.documents.map((doc) =>
          doc.id === documentId ? updatedDocument : doc
        ),
      }));
    } catch (error: any) {
      console.error("Failed to refresh document status:", error);
      // Don't set error for polling failures
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
