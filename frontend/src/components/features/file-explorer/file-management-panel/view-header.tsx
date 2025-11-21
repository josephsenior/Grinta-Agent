import React from "react";
import { useTranslation } from "react-i18next";
import { PanelLeftClose, FileText, Grid3X3, List } from "lucide-react";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";
import type { ViewMode } from "./use-view-state";

interface ViewHeaderProps {
  view: ViewMode;
  onViewChange: (view: ViewMode) => void;
  onClose: () => void;
  viewedFilesCount: number;
  hasSelectedFile: boolean;
}

export function ViewHeader({
  view,
  onViewChange,
  onClose,
  viewedFilesCount,
  hasSelectedFile,
}: ViewHeaderProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
      <div className="flex items-center gap-2">
        <FileText className="w-4 h-4 text-violet-500" />
        <h2 className="text-sm font-semibold text-text-primary">
          {t("fileExplorer.fileManager", "File Manager")}
        </h2>
        <Badge variant="secondary" className="text-xs">
          {t("fileExplorer.recentCount", "{{count}} recent", {
            count: viewedFilesCount,
          })}
        </Badge>
      </div>

      <div className="flex items-center gap-1">
        <div className="flex items-center border border-border rounded-md p-0.5">
          <Button
            variant={view === "explorer" ? "default" : "ghost"}
            size="sm"
            onClick={() => onViewChange("explorer")}
            className="h-6 w-6 p-0"
          >
            <List className="w-3 h-3" />
          </Button>
          <Button
            variant={view === "split" ? "default" : "ghost"}
            size="sm"
            onClick={() => onViewChange("split")}
            className="h-6 w-6 p-0"
          >
            <Grid3X3 className="w-3 h-3" />
          </Button>
          <Button
            variant={view === "viewer" ? "default" : "ghost"}
            size="sm"
            onClick={() => onViewChange("viewer")}
            className="h-6 w-6 p-0"
            disabled={!hasSelectedFile}
          >
            <FileText className="w-3 h-3" />
          </Button>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="h-6 w-6 p-0"
        >
          <PanelLeftClose className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
}
