import React from "react";
import { useTranslation } from "react-i18next";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";

interface RecentFilesProps {
  viewedFiles: string[];
  selectedFile: string | null;
  onFileSelect: (filePath: string) => void;
}

export function RecentFiles({
  viewedFiles,
  selectedFile,
  onFileSelect,
}: RecentFilesProps) {
  const { t } = useTranslation();
  if (viewedFiles.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-border p-2 bg-background-secondary">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-text-secondary">
          {t("fileExplorer.recentFiles", "Recent Files")}
        </span>
      </div>
      <div className="flex flex-wrap gap-1">
        {viewedFiles.slice(0, 5).map((filePath) => {
          const fileName = filePath.split("/").pop() || filePath;
          const isSelected = selectedFile === filePath;

          return (
            <Button
              key={filePath}
              variant="ghost"
              size="sm"
              onClick={() => onFileSelect(filePath)}
              className={cn(
                "h-6 px-2 text-xs",
                isSelected && "bg-brand-500/10 text-violet-500",
              )}
            >
              <span className="truncate max-w-20" title={fileName}>
                {fileName}
              </span>
            </Button>
          );
        })}
      </div>
    </div>
  );
}
