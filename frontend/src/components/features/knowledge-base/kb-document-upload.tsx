import React, { useState, useRef } from "react";
import { Upload, X, FileText, AlertCircle } from "lucide-react";
import { Button } from "#/components/ui/button";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { useUploadDocument } from "#/hooks/mutation/use-knowledge-base-mutations";

interface KBDocumentUploadProps {
  collectionId: string;
  collectionName: string;
  onClose: () => void;
}

const ALLOWED_FILE_TYPES = [
  ".txt",
  ".md",
  ".json",
  ".yaml",
  ".yml",
  ".csv",
  ".log",
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function KBDocumentUpload({
  collectionId,
  collectionName,
  onClose,
}: KBDocumentUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadDocument();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      setError(
        `File too large. Maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB`,
      );
      return;
    }

    // Validate file type
    const extension = `.${file.name.split(".").pop()}`;
    if (!ALLOWED_FILE_TYPES.includes(extension.toLowerCase())) {
      setError(
        `Unsupported file type. Allowed: ${ALLOWED_FILE_TYPES.join(", ")}`,
      );
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      await uploadMutation.mutateAsync({
        collectionId,
        file: selectedFile,
      });
      onClose();
    } catch (error) {
      // Error handled by mutation
      console.error("Upload failed:", error);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      // Create a fake input change event
      const fakeEvent = {
        target: { files: [file] },
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      handleFileSelect(fakeEvent);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  return (
    <ModalBackdrop onClose={onClose}>
      <div className="bg-background-secondary p-6 rounded-xl max-w-md w-full border border-border shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              Upload Document
            </h2>
            <p className="text-sm text-foreground-secondary mt-1">
              to "{collectionName}"
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-background-tertiary/70 transition-colors"
            title="Close"
          >
            <X className="w-5 h-5 text-foreground-secondary" />
          </button>
        </div>

        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            selectedFile
              ? "border-brand-500 bg-brand-500/5"
              : "border-border hover:border-brand-500/50 hover:bg-background-tertiary/30"
          }`}
        >
          <Upload className="w-12 h-12 mx-auto mb-4 text-foreground-secondary" />
          {selectedFile ? (
            <div className="flex items-center justify-center gap-2">
              <FileText className="w-5 h-5 text-violet-500" />
              <span className="text-sm font-medium text-foreground">
                {selectedFile.name}
              </span>
              <span className="text-xs text-foreground-secondary">
                ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            </div>
          ) : (
            <div>
              <p className="text-sm text-foreground mb-1">
                Click to browse or drag & drop
              </p>
              <p className="text-xs text-foreground-secondary">
                {ALLOWED_FILE_TYPES.join(", ")} • Max{" "}
                {MAX_FILE_SIZE / (1024 * 1024)}MB
              </p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_FILE_TYPES.join(",")}
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-500">{error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            className="flex-1"
            disabled={uploadMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            className="flex-1"
            disabled={!selectedFile || uploadMutation.isPending}
          >
            {uploadMutation.isPending ? "Uploading..." : "Upload Document"}
          </Button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
