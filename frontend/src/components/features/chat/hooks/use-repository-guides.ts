import { useState } from "react";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { useRepositoryMicroagents } from "#/hooks/query/use-repository-microagents";

interface Guide {
  name: string;
  path?: string;
}

export function useRepositoryGuides() {
  const { data: conversation } = useActiveConversation();
  const [isExpanded, setIsExpanded] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [guideToEdit, setGuideToEdit] = useState<Guide | null>(null);

  const selectedRepository = conversation?.selected_repository;
  const [owner, repo] = selectedRepository?.split("/") || [];

  const {
    data: guides,
    isLoading,
    isError,
  } = useRepositoryMicroagents(owner || "", repo || "", false);

  const hasRepository = Boolean(selectedRepository && owner && repo);

  const handleCreateGuide = () => {
    setGuideToEdit(null);
    setIsCreateModalOpen(true);
  };

  const handleEditGuide = (guide: Guide) => {
    setGuideToEdit(guide);
    setIsCreateModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsCreateModalOpen(false);
    setGuideToEdit(null);
  };

  return {
    hasRepository,
    repositoryName: selectedRepository || "",
    guides: guides || [],
    isLoading,
    isError,
    isExpanded,
    setIsExpanded,
    isCreateModalOpen,
    guideToEdit,
    handleCreateGuide,
    handleEditGuide,
    handleCloseModal,
  };
}
