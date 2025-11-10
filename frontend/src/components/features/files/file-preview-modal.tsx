import React from "react";
import {
  X,
  File,
  FileText,
  Code,
  Image as ImageIcon,
  FileArchive,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "#/components/ui/dialog";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import { Badge } from "#/components/ui/badge";

interface FilePreviewModalProps {
  files: File[];
  onConfirm: (files: File[]) => void;
  onCancel: () => void;
  isOpen: boolean;
}

function getFileIcon(fileType: string) {
  if (fileType.startsWith("image/")) return <ImageIcon className="h-4 w-4" />;
  if (fileType.startsWith("text/")) return <FileText className="h-4 w-4" />;
  if (
    fileType.includes("json") ||
    fileType.includes("javascript") ||
    fileType.includes("typescript")
  )
    return <Code className="h-4 w-4" />;
  if (
    fileType.includes("zip") ||
    fileType.includes("tar") ||
    fileType.includes("gz")
  )
    return <FileArchive className="h-4 w-4" />;
  return <File className="h-4 w-4" />;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Math.round((bytes / k ** i) * 100) / 100} ${sizes[i]}`;
}

export function FilePreviewModal({
  files,
  onConfirm,
  onCancel,
  isOpen,
}: FilePreviewModalProps) {
  const [selectedFiles, setSelectedFiles] = React.useState<File[]>(files);
  const [previewUrls, setPreviewUrls] = React.useState<Map<string, string>>(
    new Map(),
  );

  React.useEffect(() => {
    setSelectedFiles(files);

    // Create preview URLs for images
    const urls = new Map<string, string>();
    files.forEach((file) => {
      if (file.type.startsWith("image/")) {
        urls.set(file.name, URL.createObjectURL(file));
      }
    });
    setPreviewUrls(urls);

    // Cleanup URLs on unmount
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [files]);

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleConfirm = () => {
    onConfirm(selectedFiles);
  };

  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
  const hasImages = selectedFiles.some((f) => f.type.startsWith("image/"));

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <File className="h-5 w-5" />
            File Preview
            <Badge variant="outline" className="ml-auto">
              {selectedFiles.length}{" "}
              {selectedFiles.length === 1 ? "file" : "files"}
            </Badge>
          </DialogTitle>
          <DialogDescription className="text-sm text-text-secondary">
            Review your selected files and remove any you do not want to upload.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-4">
          {/* Image Previews */}
          {hasImages && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-text-secondary">
                Images
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {selectedFiles
                  .filter((f) => f.type.startsWith("image/"))
                  .map((file, index) => {
                    const previewUrl = previewUrls.get(file.name);
                    const globalIndex = selectedFiles.indexOf(file);
                    return (
                      <div
                        key={`${file.name}-${index}`}
                        className="relative group aspect-square"
                      >
                        {previewUrl && (
                          <img
                            src={previewUrl}
                            alt={file.name}
                            className="w-full h-full object-cover rounded-lg border border-border-glass"
                          />
                        )}
                        <button
                          type="button"
                          onClick={() => handleRemoveFile(globalIndex)}
                          className="absolute top-1 right-1 p-1.5 bg-error-500/90 hover:bg-error-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                          title="Remove file"
                        >
                          <X className="h-3 w-3 text-white" />
                        </button>
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2 rounded-b-lg">
                          <p className="text-xs text-white truncate">
                            {file.name}
                          </p>
                          <p className="text-xs text-white/70">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Other Files */}
          {selectedFiles.some((f) => !f.type.startsWith("image/")) && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-text-secondary">
                Documents
              </h3>
              <div className="space-y-2">
                {selectedFiles
                  .filter((f) => !f.type.startsWith("image/"))
                  .map((file, index) => {
                    const globalIndex = selectedFiles.indexOf(file);
                    return (
                      <div
                        key={`${file.name}-${index}`}
                        className={cn(
                          "flex items-center gap-3 p-3 rounded-lg border border-border-glass",
                          "bg-background-surface hover:bg-background-surface/80 transition-colors group",
                        )}
                      >
                        <div className="flex-shrink-0 p-2 rounded-lg bg-primary-500/10 text-primary-500">
                          {getFileIcon(file.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {file.name}
                          </p>
                          <p className="text-xs text-text-foreground-secondary">
                            {formatFileSize(file.size)} •{" "}
                            {file.type || "Unknown type"}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveFile(globalIndex)}
                          className="flex-shrink-0 p-1.5 rounded-lg hover:bg-error-500/20 text-text-foreground-secondary hover:text-error-500 transition-colors opacity-0 group-hover:opacity-100"
                          title="Remove file"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex items-center justify-between border-t border-border-glass pt-4">
          <div className="text-sm text-text-foreground-secondary">
            Total: {formatFileSize(totalSize)}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={selectedFiles.length === 0}
              className="bg-primary-500 hover:bg-primary-600"
            >
              Upload {selectedFiles.length}{" "}
              {selectedFiles.length === 1 ? "file" : "files"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
