import { useTranslation } from "react-i18next";
import { FileText, Edit, Plus } from "lucide-react";
import { Button } from "#/components/ui/button";

interface Guide {
  name: string;
  path?: string;
}

interface GuideItemProps {
  guide: Guide;
  onEdit: (guide: Guide) => void;
}

function GuideItem({ guide, onEdit }: GuideItemProps) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-violet-500/5 border border-violet-500/10 hover:bg-violet-500/10 transition-colors group">
      <FileText className="h-4 w-4 text-violet-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-foreground-secondary truncate">
          {guide.name}
        </div>
        {guide.path && (
          <div className="text-xs text-foreground-tertiary truncate">
            {guide.path}
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={() => onEdit(guide)}
        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-violet-500/20"
        title="Edit guide"
      >
        <Edit className="h-3.5 w-3.5 text-violet-400" />
      </button>
    </div>
  );
}

interface GuideListProps {
  guides: Guide[];
  isLoading: boolean;
  isError: boolean;
  onCreateGuide: () => void;
  onEditGuide: (guide: Guide) => void;
}

export function GuideList({
  guides,
  isLoading,
  isError,
  onCreateGuide,
  onEditGuide,
}: GuideListProps) {
  const { t } = useTranslation();
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <div className="text-sm text-foreground-tertiary">
          {t("chat.guides.loading", "Loading guides...")}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-sm text-red-400 py-2">
        {t("chat.guides.loadError", "Failed to load guides")}
      </div>
    );
  }

  if (guides.length === 0) {
    return (
      <div className="text-sm text-foreground-tertiary py-2">
        {t(
          "chat.guides.noGuides",
          "No guides available. Create one to get started.",
        )}
      </div>
    );
  }

  return (
    <>
      {guides.map((guide) => (
        <GuideItem key={guide.name} guide={guide} onEdit={onEditGuide} />
      ))}
      <Button
        variant="outline"
        size="sm"
        className="w-full mt-2 border-violet-500/20 hover:bg-violet-500/10"
        onClick={onCreateGuide}
      >
        <Plus className="h-4 w-4 mr-2" />
        {t("chat.guides.create", "Create Guide")}
      </Button>
    </>
  );
}
