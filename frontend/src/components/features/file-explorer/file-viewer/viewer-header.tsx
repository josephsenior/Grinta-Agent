import React from "react";
import {
  Copy,
  Download,
  Edit3,
  Save,
  Eye,
  Maximize2,
  Minimize2,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "#/components/ui/button";
import { Badge } from "#/components/ui/badge";

interface ViewerHeaderProps {
  fileName: string;
  language: string;
  contentLength: number;
  editable: boolean;
  editing: boolean;
  copied: boolean;
  isFullscreen: boolean;
  onCopy: () => void;
  onDownload: () => void;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onToggleFullscreen: () => void;
  onClose?: () => void;
}

export function ViewerHeader({
  fileName,
  language,
  contentLength,
  editable,
  editing,
  copied,
  isFullscreen,
  onCopy,
  onDownload,
  onEdit,
  onSave,
  onCancel,
  onToggleFullscreen,
  onClose,
}: ViewerHeaderProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-violet-500" />
          <span className="text-sm font-medium text-text-primary truncate">
            {fileName}
          </span>
        </div>

        <Badge variant="outline" className="text-xs">
          {language}
        </Badge>

        <span className="text-xs text-text-secondary">
          {t("viewerHeader.charCount", "{{count}} chars", {
            count: contentLength,
          })}
        </span>
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={onCopy}
          className="h-7 px-2 text-xs"
        >
          {copied ? (
            <span className="text-success-500">
              {t("viewerHeader.copied", "Copied!")}
            </span>
          ) : (
            <>
              <Copy className="w-3 h-3 mr-1" />
              {t("viewerHeader.copy", "Copy")}
            </>
          )}
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onDownload}
          className="h-7 px-2 text-xs"
        >
          <Download className="w-3 h-3 mr-1" />
          {t("viewerHeader.download", "Download")}
        </Button>

        {editable && !editing && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onEdit}
            className="h-7 px-2 text-xs"
          >
            <Edit3 className="w-3 h-3 mr-1" />
            {t("viewerHeader.edit", "Edit")}
          </Button>
        )}

        {editing && (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={onSave}
              className="h-7 px-2 text-xs text-success-500"
            >
              <Save className="w-3 h-3 mr-1" />
              {t("viewerHeader.save", "Save")}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              className="h-7 px-2 text-xs text-text-secondary"
            >
              {t("viewerHeader.cancel", "Cancel")}
            </Button>
          </>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleFullscreen}
          className="h-7 w-7 p-0"
        >
          {isFullscreen ? (
            <Minimize2 className="w-3 h-3" />
          ) : (
            <Maximize2 className="w-3 h-3" />
          )}
        </Button>

        {onClose && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-7 w-7 p-0"
          >
            <X className="w-3 h-3" />
          </Button>
        )}
      </div>
    </div>
  );
}
