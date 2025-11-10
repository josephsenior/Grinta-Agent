import React from "react";
import { NavLink, useParams, useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { ConversationCard } from "./conversation-card";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { useInfiniteScroll } from "#/hooks/use-infinite-scroll";
import { useDeleteConversation } from "#/hooks/mutation/use-delete-conversation";
import { useStopConversation } from "#/hooks/mutation/use-stop-conversation";
import { ConfirmDeleteModal } from "./confirm-delete-modal";
import { ConfirmStopModal } from "./confirm-stop-modal";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { ExitConversationModal } from "./exit-conversation-modal";
import { useClickOutsideElement } from "#/hooks/use-click-outside-element";
import { useUpdateConversation } from "#/hooks/mutation/use-update-conversation";
import { displaySuccessToast } from "#/utils/custom-toast-handlers";
import { cn } from "#/utils/utils";

interface ConversationPanelProps {
  onClose: () => void;
}

interface LoadingOverlayProps {
  isVisible: boolean;
}

function LoadingOverlay({ isVisible }: LoadingOverlayProps) {
  if (!isVisible) {
    return null;
  }

  return (
    <div className="w-full h-full absolute flex justify-center items-center">
      <LoadingSpinner size="small" />
    </div>
  );
}

interface ErrorStateProps {
  error: Error | null;
}

function ErrorState({ error }: ErrorStateProps) {
  if (!error) {
    return null;
  }

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      <div className="card-modern border-error-500/30 bg-error-500/5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-error-500/20 flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-error-500" />
          </div>
          <h3 className="text-lg font-semibold text-error-500">Error</h3>
        </div>
        <p className="text-foreground-secondary text-sm font-medium">
          {error.message}
        </p>
      </div>
    </div>
  );
}

interface EmptyStateProps {
  isVisible: boolean;
  title: string;
  subtitle: string;
}

function EmptyState({ isVisible, title, subtitle }: EmptyStateProps) {
  if (!isVisible) {
    return null;
  }

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      <div className="card-modern">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-brand-500/10 flex items-center justify-center">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-accent-500" />
          </div>
          <div className="text-center">
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {title}
            </h3>
            <p className="text-foreground-secondary text-sm font-medium">
              {subtitle}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

interface PlaywrightButtonProps {
  show: boolean;
  label: string;
}

function PlaywrightButton({ show, label }: PlaywrightButtonProps) {
  if (!show) {
    return null;
  }

  return (
    <div className="p-4">
      <button
        type="button"
        data-testid="new-conversation-button"
        className="btn"
      >
        {label}
      </button>
    </div>
  );
}

interface FetchMoreIndicatorProps {
  isVisible: boolean;
}

function FetchMoreIndicator({ isVisible }: FetchMoreIndicatorProps) {
  if (!isVisible) {
    return null;
  }

  return (
    <div className="flex justify-center py-4">
      <LoadingSpinner size="small" />
    </div>
  );
}

interface ConfirmDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmDeleteDialog({
  isOpen,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) {
    return null;
  }

  return <ConfirmDeleteModal onConfirm={onConfirm} onCancel={onCancel} />;
}

function ConfirmStopDialog({
  isOpen,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) {
    return null;
  }

  return <ConfirmStopModal onConfirm={onConfirm} onCancel={onCancel} />;
}

interface ExitConversationDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

function ExitConversationDialog({
  isOpen,
  onConfirm,
  onClose,
}: ExitConversationDialogProps) {
  if (!isOpen) {
    return null;
  }

  return <ExitConversationModal onConfirm={onConfirm} onClose={onClose} />;
}

export function ConversationPanel({ onClose }: ConversationPanelProps) {
  const { t } = useTranslation();
  const controller = useConversationPanelController({ onClose, t });
  const { ref } = controller;

  const showEmptyState =
    controller.conversations.length === 0 &&
    !controller.isFetching &&
    !controller.error;

  return (
    <div className="relative h-full" ref={ref}>
      <LoadingOverlay isVisible={controller.isFetching} />

      <div className="flex flex-col h-full">
        <ErrorState error={controller.error as Error | null} />
        <EmptyState
          isVisible={showEmptyState}
          title={t("No conversations yet")}
          subtitle={t("Start a new conversation to begin")}
        />

        {controller.conversations.length > 0 && (
          <div className="flex flex-col h-full">
            <div className="flex-none">
              <PlaywrightButton
                show={controller.isPlaywrightRun}
                label={t("View in Browser")}
              />
            </div>

            <div
              className="flex-1 overflow-y-auto"
              ref={controller.scrollContainerRef}
            >
              <div className="p-3">
                {controller.conversations.map((conversation) => (
                  <NavLink
                    key={conversation.conversation_id}
                    to={`/c/${conversation.conversation_id}`}
                    className={({ isActive }) =>
                      cn(
                        "block rounded-lg mb-2 border border-transparent hover:border-border",
                        isActive && "border-brand-500",
                      )
                    }
                    onClick={() =>
                      controller.handleCardClick(conversation.conversation_id)
                    }
                  >
                    <ConversationCard
                      title={conversation.title || t("Untitled")}
                      lastUpdatedAt={conversation.last_updated_at || ""}
                      createdAt={conversation.created_at || ""}
                      selectedRepository={(conversation as any).repo}
                      conversationStatus={conversation.status}
                      showOptions
                      conversationId={conversation.conversation_id}
                      contextMenuOpen={
                        controller.openContextMenuId ===
                        conversation.conversation_id
                      }
                      onContextMenuToggle={() =>
                        controller.handleContextMenuToggle(
                          conversation.conversation_id,
                        )
                      }
                      onClick={() =>
                        controller.handleCardClick(conversation.conversation_id)
                      }
                      onDelete={() =>
                        controller.handleDeleteProject(
                          conversation.conversation_id,
                        )
                      }
                      onStop={() =>
                        controller.handleStopConversation(
                          conversation.conversation_id,
                        )
                      }
                      onChangeTitle={(title) =>
                        controller.handleConversationTitleChange(
                          conversation.conversation_id,
                          title,
                        )
                      }
                      variant="default"
                    />
                  </NavLink>
                ))}
              </div>
              <FetchMoreIndicator isVisible={controller.isFetchingNextPage} />
            </div>
          </div>
        )}
      </div>

      <ConfirmDeleteDialog
        isOpen={controller.confirmDeleteModalVisible}
        onConfirm={() => {
          controller.handleConfirmDelete();
          controller.closeDeleteModal();
        }}
        onCancel={controller.closeDeleteModal}
      />
      <ConfirmStopDialog
        isOpen={controller.confirmStopModalVisible}
        onConfirm={() => {
          controller.handleConfirmStop();
          controller.closeStopModal();
        }}
        onCancel={controller.closeStopModal}
      />
      <ExitConversationDialog
        isOpen={controller.confirmExitConversationModalVisible}
        onConfirm={controller.handleConfirmExit}
        onClose={() => controller.setConfirmExitConversationModalVisible(false)}
      />
    </div>
  );
}

function useConversationPanelController({
  onClose,
  t,
}: {
  onClose: () => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const ref = useClickOutsideElement<HTMLDivElement>(onClose);
  const location = useLocation();
  const navigate = useNavigate();
  const { conversationId: currentConversationId } = useParams();

  interface WindowWithE2E extends Window {
    __Forge_PLAYWRIGHT?: boolean;
  }

  const isPlaywrightRun =
    typeof window !== "undefined" &&
    (window as unknown as WindowWithE2E).__Forge_PLAYWRIGHT === true;

  const [confirmDeleteModalVisible, setConfirmDeleteModalVisible] =
    React.useState(false);
  const [confirmStopModalVisible, setConfirmStopModalVisible] =
    React.useState(false);
  const [
    confirmExitConversationModalVisible,
    setConfirmExitConversationModalVisible,
  ] = React.useState(false);
  const [selectedConversationId, setSelectedConversationId] = React.useState<
    string | null
  >(null);
  const [openContextMenuId, setOpenContextMenuId] = React.useState<
    string | null
  >(null);

  const paginated = usePaginatedConversations();
  const conversations =
    paginated.data?.pages.flatMap((page) => page.results) ?? [];
  const deleteConversation = useDeleteConversation();
  const stopConversation = useStopConversation();
  const updateConversation = useUpdateConversation();

  const scrollContainerRef = useInfiniteScroll({
    hasNextPage: !!paginated.hasNextPage,
    isFetchingNextPage: paginated.isFetchingNextPage,
    fetchNextPage: paginated.fetchNextPage,
    threshold: 200,
  });

  const handleDeleteProject = (conversationId: string) => {
    setConfirmDeleteModalVisible(true);
    setSelectedConversationId(conversationId);
  };

  const handleStopConversation = (conversationId: string) => {
    setConfirmStopModalVisible(true);
    setSelectedConversationId(conversationId);
  };

  const handleConversationTitleChange = React.useCallback(
    (conversationId: string, newTitle: string) => {
      updateConversation.mutate(
        { conversationId, newTitle },
        {
          onSuccess: () => {
            displaySuccessToast(t(I18nKey.CONVERSATION$TITLE_UPDATED));
          },
        },
      );
    },
    [t, updateConversation],
  );

  const handleConfirmDelete = React.useCallback(() => {
    if (!selectedConversationId) {
      return;
    }

    deleteConversation.mutate(
      { conversationId: selectedConversationId },
      {
        onSuccess: () => {
          if (selectedConversationId === currentConversationId) {
            navigate("/");
          }
        },
      },
    );
  }, [
    currentConversationId,
    deleteConversation,
    navigate,
    selectedConversationId,
  ]);

  const handleConfirmStop = React.useCallback(() => {
    if (!selectedConversationId) {
      return;
    }

    stopConversation.mutate(
      { conversationId: selectedConversationId },
      {
        onSuccess: () => {
          displaySuccessToast(t("Conversation stopped"));
        },
      },
    );
  }, [selectedConversationId, stopConversation, t]);

  const handleConfirmExit = React.useCallback(() => {
    setConfirmExitConversationModalVisible(false);
    onClose();
  }, [onClose]);

  const closeDeleteModal = React.useCallback(() => {
    setConfirmDeleteModalVisible(false);
    setSelectedConversationId(null);
  }, []);

  const closeStopModal = React.useCallback(() => {
    setConfirmStopModalVisible(false);
    setSelectedConversationId(null);
  }, []);

  const handleContextMenuToggle = React.useCallback(
    (conversationId: string) => {
      setOpenContextMenuId((prev) =>
        prev === conversationId ? null : conversationId,
      );
    },
    [],
  );

  const handleCardClick = React.useCallback(
    (conversationId: string) => {
      if (conversationId === currentConversationId) {
        setConfirmExitConversationModalVisible(true);
      }
    },
    [currentConversationId],
  );

  return {
    ref,
    isPlaywrightRun,
    location,
    conversations,
    isFetching: paginated.isFetching,
    error: paginated.error,
    isFetchingNextPage: paginated.isFetchingNextPage,
    fetchNextPage: paginated.fetchNextPage,
    scrollContainerRef,
    confirmDeleteModalVisible,
    confirmStopModalVisible,
    confirmExitConversationModalVisible,
    setConfirmExitConversationModalVisible,
    openContextMenuId,
    handleDeleteProject,
    handleStopConversation,
    handleConversationTitleChange,
    handleConfirmDelete,
    handleConfirmStop,
    handleConfirmExit,
    closeDeleteModal,
    closeStopModal,
    handleContextMenuToggle,
    handleCardClick,
  };
}
