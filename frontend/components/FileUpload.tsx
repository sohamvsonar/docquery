"use client";

/**
 * File Upload Component
 * Drag-and-drop interface with progress tracking
 * Auto-hides picker after successful upload and shows a + (add more) action.
 */

import { useCallback, useState } from "react";
import { useDocumentsStore } from "@/store/documentsStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { Upload, Loader2, FileText, CheckCircle, Plus, Paperclip } from "lucide-react";

// Supported file types matching backend processor capabilities
const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/tiff",
  "image/bmp",
  "image/gif",
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/m4a",
  "audio/ogg",
  "audio/flac",
  "text/plain",
  "text/markdown",
  "text/x-markdown",
  "text/html",
  "text/csv",
  "application/json",
  "application/xml",
  "text/xml",
  "application/vnd.ms-excel",
];

const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".doc",
  ".png",
  ".jpg",
  ".jpeg",
  ".tiff",
  ".tif",
  ".bmp",
  ".gif",
  ".mp3",
  ".wav",
  ".m4a",
  ".ogg",
  ".flac",
  ".txt",
  ".md",
  ".markdown",
  ".html",
  ".htm",
  ".csv",
  ".json",
  ".xml",
];

interface FileUploadProps {
  onUploaded?: (file: { name: string; timestamp: Date }) => void;
}

export default function FileUpload({ onUploaded }: FileUploadProps) {
  const { uploadDocument, isUploading, uploadProgress, error, clearError } = useDocumentsStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; timestamp: Date }>>([]);
  const [showPicker, setShowPicker] = useState(true);

  const validateFile = (file: File): string | null => {
    const isValidType = ALLOWED_TYPES.includes(file.type) || ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!isValidType) return "Invalid file type. Supported: PDF, DOC/DOCX, Images, Audio, TXT/MD/HTML/CSV/JSON/XML.";
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) return "File too large. Maximum size is 50MB.";
    return null;
  };

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    const validationError = validateFile(file);
    if (validationError) {
      alert(validationError);
      return;
    }
    clearError();
    const result = await uploadDocument(file);
    if (result) {
      const entry = { name: file.name, timestamp: new Date() };
      setUploadedFiles((prev) => [entry, ...prev]);
      setShowPicker(false);
      onUploaded?.(entry);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
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
      {error && (
        <Alert variant="destructive">
          <p className="text-sm">{error}</p>
        </Alert>
      )}

      {showPicker && (
        <Card>
          <CardContent className="p-0">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`relative border-2 border-dashed rounded-lg p-4 transition-colors ${
                isDragging
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/10"
                  : "border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
              } ${isUploading ? "pointer-events-none opacity-60" : ""}`}
            >
              {isUploading ? (
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Uploading... {uploadProgress}%</p>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1">
                      <div className="bg-blue-600 h-1.5 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <Upload className="w-5 h-5 text-blue-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{isDragging ? "Drop file here" : "Add file"}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Drag & drop or click to browse</p>
                  </div>
                  <Button size="sm" onClick={() => document.getElementById("file-input")?.click()} disabled={isUploading}>
                    Browse
                  </Button>
                </div>
              )}

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
      )}

      {uploadedFiles.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Uploaded Files</h4>
            <div className="space-y-2">
              {uploadedFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700"
                >
                  <FileText className="w-4 h-4 text-gray-500" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{file.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{file.timestamp.toLocaleTimeString()}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-400">
                      <CheckCircle className="w-3.5 h-3.5 mr-1" /> Uploaded
                    </span>
                    <Button
                      size="icon"
                      variant="outline"
                      title="Add more"
                      onClick={() => {
                        setShowPicker(true);
                        setTimeout(() => document.getElementById("file-input")?.click(), 0);
                      }}
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            {!showPicker && (
              <div className="mt-3 flex justify-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowPicker(true);
                    setTimeout(() => document.getElementById("file-input")?.click(), 0);
                  }}
                >
                  <Paperclip className="w-4 h-4 mr-2" /> Add more
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

