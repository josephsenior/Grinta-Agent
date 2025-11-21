import { validateFiles } from "#/utils/file-validation";
import { convertImageToBase64 } from "#/utils/convert-image-to-base-64";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

export async function processImages(images: File[]): Promise<string[]> {
  return Promise.all(images.map((image) => convertImageToBase64(image)));
}

export function validateAllFiles(
  images: File[],
  files: File[],
): {
  isValid: boolean;
  errorMessage?: string;
} {
  const allFiles = [...images, ...files];
  return validateFiles(allFiles);
}

interface UploadFilesResult {
  skippedFiles?: Array<{ reason?: string }>;
  skipped_files?: Array<{ reason?: string }>;
  uploadedFiles?: string[];
  uploaded_files?: string[];
}

export async function uploadAttachments({
  conversationId,
  files,
  uploadFiles,
}: {
  conversationId: string;
  files: File[];
  uploadFiles: (variables: {
    conversationId: string;
    files: File[];
  }) => Promise<UploadFilesResult>;
}): Promise<{
  skippedFiles: Array<{ reason?: string }>;
  uploadedFiles: string[];
}> {
  if (files.length === 0) {
    return { skippedFiles: [], uploadedFiles: [] };
  }
  const result = await uploadFiles({ conversationId, files });
  return {
    skippedFiles: result.skippedFiles || result.skipped_files || [],
    uploadedFiles: result.uploadedFiles || result.uploaded_files || [],
  };
}

export function reportSkippedFiles(
  skippedFiles: Array<{ reason?: string }>,
): void {
  skippedFiles.forEach((file) => {
    if (file.reason) {
      displayErrorToast(file.reason);
    }
  });
}
