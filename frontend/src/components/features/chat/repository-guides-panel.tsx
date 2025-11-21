import React from "react";
import { cn } from "#/utils/utils";
import { CreateGuideModal } from "./create-guide-modal";
import { useRepositoryGuides } from "./hooks/use-repository-guides";
import { GuidesPanelHeader } from "./components/guides-panel-header";
import { GuideList } from "./components/guide-list";

interface RepositoryGuidesPanelProps {
  className?: string;
}

export function RepositoryGuidesPanel({
  className,
}: RepositoryGuidesPanelProps) {
  const {
    hasRepository,
    repositoryName,
    guides,
    isLoading,
    isError,
    isExpanded,
    setIsExpanded,
    isCreateModalOpen,
    guideToEdit,
    handleCreateGuide,
    handleEditGuide,
    handleCloseModal,
  } = useRepositoryGuides();

  if (!hasRepository) {
    return null;
  }

  return (
    <div
      className={cn(
        "border-t border-violet-500/20 bg-black/50 backdrop-blur-sm",
        className,
      )}
    >
      <GuidesPanelHeader
        isExpanded={isExpanded}
        onToggle={() => setIsExpanded(!isExpanded)}
        repositoryName={repositoryName}
      />

      {isExpanded && (
        <div className="px-4 pb-4 space-y-3 max-h-[300px] overflow-y-auto">
          <GuideList
            guides={guides}
            isLoading={isLoading}
            isError={isError}
            onCreateGuide={handleCreateGuide}
            onEditGuide={handleEditGuide}
          />
        </div>
      )}

      {isCreateModalOpen && (
        <CreateGuideModal
          onClose={handleCloseModal}
          guideToEdit={guideToEdit}
        />
      )}
    </div>
  );
}
