"use client";

/**
 * Documents Page
 * Upload and manage documents
 */

import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
import DocumentList from "@/components/DocumentList";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DocumentsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Page Header */}
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Documents
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Manage your documents and view upload status
            </p>
          </div>

          {/* Instructions Card */}
          <Card>
            <CardHeader>
              <CardTitle>📝 Document Management</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                <div>
                  <p className="font-medium mb-1">Upload Documents:</p>
                  <p>Go to the Chat page to upload new documents</p>
                  <p className="text-xs mt-1">
                    Supports: PDF, Images (PNG, JPG, TIFF, BMP, GIF), Audio (MP3, WAV, M4A, OGG, FLAC), Text (TXT, MD, HTML, CSV, JSON, XML)
                  </p>
                </div>
                <p><strong>Status:</strong> Monitor document processing status below</p>
                <p><strong>Delete:</strong> Remove documents you no longer need</p>
              </div>
            </CardContent>
          </Card>

          {/* Document List */}
          <DocumentList autoRefresh={true} refreshInterval={5000} />
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
