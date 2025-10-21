"use client";

/**
 * Document List Component
 * Displays uploaded documents with status badges and actions
 */

import { useEffect, useState } from "react";
import { useDocumentsStore } from "@/store/documentsStore";
import type { DocumentResponse } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface DocumentListProps {
  autoRefresh?: boolean; // Enable polling for processing documents
  refreshInterval?: number; // Polling interval in ms
}

export default function DocumentList({
  autoRefresh = true,
  refreshInterval = 5000,
}: DocumentListProps) {
  const { documents, fetchDocuments, deleteDocument, refreshDocumentStatus, isLoading } =
    useDocumentsStore();
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Auto-refresh processing documents
  useEffect(() => {
    if (!autoRefresh) return;

    const processingDocs = documents.filter(
      (doc) => doc.status === "pending" || doc.status === "processing"
    );

    if (processingDocs.length === 0) return;

    const interval = setInterval(() => {
      processingDocs.forEach((doc) => {
        refreshDocumentStatus(doc.id);
      });
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [documents, autoRefresh, refreshInterval, refreshDocumentStatus]);

  const handleDelete = async (documentId: number) => {
    if (!confirm("Are you sure you want to delete this document?")) return;

    setDeletingIds((prev) => new Set(prev).add(documentId));

    try {
      await deleteDocument(documentId);
    } catch (error) {
      console.error("Failed to delete document:", error);
    } finally {
      setDeletingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(documentId);
        return newSet;
      });
    }
  };

  const handleDownload = async (documentId: number, filename: string) => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`https://api.docquery.me/upload/${documentId}/download`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to download document");
      }

      // Create a blob from the response
      const blob = await response.blob();

      // Create a temporary URL for the blob
      const url = window.URL.createObjectURL(blob);

      // Create a temporary anchor element and trigger download
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Failed to download document:", error);
      alert("Failed to download document");
    }
  };

  const getStatusBadge = (status: DocumentResponse["status"]) => {
    const variants = {
      pending: { variant: "secondary" as const, label: "Pending", icon: "⏳" },
      processing: { variant: "default" as const, label: "Processing", icon: "⚙️" },
      completed: { variant: "secondary" as const, label: "Completed", icon: "✓" },
      failed: { variant: "destructive" as const, label: "Failed", icon: "✗" },
    };

    const config = variants[status] || variants.pending;

    return (
      <Badge variant={config.variant} className={status === "completed" ? "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400" : ""}>
        <span className="mr-1">{config.icon}</span>
        {config.label}
      </Badge>
    );
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (isLoading && documents.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent mb-4" />
          <p className="text-gray-600">Loading documents...</p>
        </CardContent>
      </Card>
    );
  }

  if (documents.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <div className="text-6xl mb-4">📭</div>
          <p className="text-lg font-medium text-gray-900 dark:text-white">
            No documents yet
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Upload your first document to get started
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Your Documents ({documents.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex flex-col md:flex-row md:items-center gap-3 md:gap-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                {/* Document Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <h3 className="font-medium text-gray-900 dark:text-white truncate flex-1 min-w-0">
                      {doc.original_filename}
                    </h3>
                    {getStatusBadge(doc.status)}
                  </div>

                  <div className="flex flex-wrap items-center gap-2 md:gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <span>{formatFileSize(doc.file_size)}</span>
                    <span className="hidden md:inline">•</span>
                    <span className="text-xs md:text-sm">{formatDate(doc.created_at)}</span>
                  </div>

                  {doc.error_message && (
                    <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                      Error: {doc.error_message}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 md:flex-shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownload(doc.id, doc.original_filename)}
                    disabled={doc.status !== "completed"}
                    title={doc.status !== "completed" ? "Document must be completed to download" : "Download document"}
                    className="flex-1 md:flex-none"
                  >
                    <svg className="w-4 h-4 md:mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span className="hidden md:inline">Download</span>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingIds.has(doc.id)}
                    className="flex-1 md:flex-none"
                  >
                    {deletingIds.has(doc.id) ? "Deleting..." : "Delete"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
