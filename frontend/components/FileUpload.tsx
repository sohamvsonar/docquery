"use client";

/**
 * File Upload Component
 * Drag-and-drop interface with progress tracking
 */

import { useCallback, useState } from "react";
import { useDocumentsStore } from "@/store/documentsStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";

// Supported file types matching backend processor capabilities
const ALLOWED_TYPES = [
  // PDF
  "application/pdf",
  // Documents
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // .docx
  "application/msword", // .doc
  // Images
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/tiff",
  "image/bmp",
  "image/gif",
  // Audio
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/m4a",
  "audio/ogg",
  "audio/flac",
  // Text files
  "text/plain",
  "text/markdown",
  "text/x-markdown",
  "text/html",
  "text/csv",
  // Structured data
  "application/json",
  "application/xml",
  "text/xml",
];

const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".docx", ".doc",
  ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif",
  ".mp3", ".wav", ".m4a", ".ogg", ".flac",
  ".txt", ".md", ".markdown", ".html", ".htm", ".csv",
  ".json", ".xml",
];

export default function FileUpload() {
  const { uploadDocument, isUploading, uploadProgress, error, clearError } =
    useDocumentsStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; timestamp: Date }>>([]);

  const validateFile = (file: File): string | null => {
    // Check file type
    const isValidType = ALLOWED_TYPES.includes(file.type) ||
      ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));

    if (!isValidType) {
      return "Invalid file type. Supported formats: PDF, DOCX, Images (PNG, JPG, TIFF, BMP, GIF), Audio (MP3, WAV, M4A, OGG, FLAC), Text (TXT, MD, HTML, CSV, JSON, XML)";
    }

    // Check file size (max 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      return "File too large. Maximum size is 50MB.";
    }

    return null;
  };

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0]; // Single file upload
    const validationError = validateFile(file);

    if (validationError) {
      alert(validationError);
      return;
    }

    clearError();
    const result = await uploadDocument(file);

    // Add to uploaded files list if successful
    if (result) {
      setUploadedFiles((prev) => [
        { name: file.name, timestamp: new Date() },
        ...prev,
      ]);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    handleFileSelect(files);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  return (
    <div className="space-y-4">
      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <p className="text-sm">{error}</p>
        </Alert>
      )}

      {/* Compact Drag and Drop Area */}
      <Card>
        <CardContent className="p-0">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`
              relative border-2 border-dashed rounded-lg p-4 transition-colors
              ${isDragging
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/10"
                : "border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
              }
              ${isUploading ? "pointer-events-none opacity-60" : ""}
            `}
          >
            {isUploading ? (
              // Upload Progress - Compact
              <div className="flex items-center gap-3">
                <div className="text-2xl">📤</div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    Uploading... {uploadProgress}%
                  </p>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ) : (
              // Upload Prompt - Compact
              <div className="flex items-center gap-3">
                <div className="text-2xl">{isDragging ? "📥" : "📎"}</div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {isDragging ? "Drop file here" : "Add file"}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Drag & drop or click to browse
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => document.getElementById("file-input")?.click()}
                  disabled={isUploading}
                >
                  Browse
                </Button>
              </div>
            )}

            {/* Hidden File Input */}
            <input
              id="file-input"
              type="file"
              accept={ALLOWED_EXTENSIONS.join(",")}
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
              disabled={isUploading}
            />
          </div>
        </CardContent>
      </Card>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
              Uploaded Files
            </h4>
            <div className="space-y-2">
              {uploadedFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700"
                >
                  <div className="text-lg">📄</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {file.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-400">
                      ✓ Uploaded
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
