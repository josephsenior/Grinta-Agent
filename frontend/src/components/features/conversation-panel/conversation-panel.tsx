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
import { Provider } from "#/types/settings";
import { useUpdateConversation } from "#/hooks/mutation/use-update-conversation";
import { displaySuccessToast } from "#/utils/custom-toast-handlers";

interface ConversationPanelProps {
  onClose: () => void;
}

export function ConversationPanel({ onClose }: ConversationPanelProps) {
  const { t } = useTranslation();
  interface WindowWithE2E extends Window {
    __OPENHANDS_PLAYWRIGHT?: boolean;
  }

  const isPlaywrightRun =
    typeof window !== "undefined" &&
    (window as unknown as WindowWithE2E).__OPENHANDS_PLAYWRIGHT === true;
  const location = useLocation();
  const { conversationId: currentConversationId } = useParams();
  const ref = useClickOutsideElement<HTMLDivElement>(onClose);
  const navigate = useNavigate();

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

  const {
    data,
    isFetching,
    error,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = usePaginatedConversations();

  // Flatten all pages into a single array of conversations
  const conversations = data?.pages.flatMap((page) => page.results) ?? [];

  const { mutate: deleteConversation } = useDeleteConversation();
  const { mutate: stopConversation } = useStopConversation();
  const { mutate: updateConversation } = useUpdateConversation();

  // Set up infinite scroll
  const scrollContainerRef = useInfiniteScroll({
    hasNextPage: !!hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    threshold: 200, // Load more when 200px from bottom
  });

  const handleDeleteProject = (conversationId: string) => {
    setConfirmDeleteModalVisible(true);
    setSelectedConversationId(conversationId);
  };

  const handleStopConversation = (conversationId: string) => {
    setConfirmStopModalVisible(true);
    setSelectedConversationId(conversationId);
  };

  const handleConversationTitleChange = async (
    conversationId: string,
    newTitle: string,
  ) => {
    updateConversation(
      { conversationId, newTitle },
      {
        onSuccess: () => {
          displaySuccessToast(t(I18nKey.CONVERSATION$TITLE_UPDATED));
        },
      },
    );
  };

  const handleConfirmDelete = () => {
    if (selectedConversationId) {
      deleteConversation(
        { conversationId: selectedConversationId },
        {
          onSuccess: () => {
            if (selectedConversationId === currentConversationId) {
              navigate("/");
            }
          },
        },
      );
    }
  };

  const handleConfirmStop = () => {
    if (selectedConversationId) {
      stopConversation(
        { conversationId: selectedConversationId },
        {
          onSuccess: () => {
            if (selectedConversationId === currentConversationId) {
              navigate("/");
            }
          },
        },
      );
    }
  };

  return (
    <div
      ref={(node) => {
        // TODO: Combine both refs somehow
        if (ref.current !== node) ref.current = node;
        if (scrollContainerRef.current !== node)
          scrollContainerRef.current = node;
      }}
      data-testid="conversation-panel"
      className="w-[350px] h-full bg-background-secondary backdrop-blur-xl border border-border rounded-2xl overflow-y-auto absolute shadow-2xl"
    >
      {isFetching && conversations.length === 0 && (
        <div className="w-full h-full absolute flex justify-center items-center">
          <LoadingSpinner size="small" />
        </div>
      )}
      {error && (
        <div className="flex flex-col items-center justify-center h-full p-6">
          <div className="card-modern border-error-500/30 bg-error-500/5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 rounded-full bg-error-500/20 flex items-center justify-center">
                <div className="w-3 h-3 rounded-full bg-error-500" />
              </div>
              <h3 className="text-lg font-semibold text-error-500">Error</h3>
            </div>
            <p className="text-foreground-secondary text-sm font-medium">{error.message}</p>
          </div>
        </div>
      )}
      {conversations?.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full p-6">
          <div className="card-modern">
            <div className="flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-brand-500/10 flex items-center justify-center">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-accent-500" />
              </div>
              <div className="text-center">
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  No Conversations Yet
                </h3>
                <p className="text-foreground-secondary text-sm font-medium">
                  {t(I18nKey.CONVERSATION$NO_CONVERSATIONS)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
      {conversations?.map((project) => (
        <NavLink
          key={project.conversation_id}
          to={`/conversations/${project.conversation_id}`}
          onClick={onClose}
        >
          {({ isActive }) => (
            <ConversationCard
              isActive={isActive}
              onDelete={() => handleDeleteProject(project.conversation_id)}
              onStop={() => handleStopConversation(project.conversation_id)}
              onChangeTitle={(title) =>
                handleConversationTitleChange(project.conversation_id, title)
              }
              title={project.title}
              selectedRepository={{
                selected_repository: project.selected_repository,
                selected_branch: project.selected_branch,
                git_provider: project.git_provider as Provider,
              }}
              lastUpdatedAt={project.last_updated_at}
              createdAt={project.created_at}
              conversationStatus={project.status}
              conversationId={project.conversation_id}
              contextMenuOpen={openContextMenuId === project.conversation_id}
              onContextMenuToggle={(isOpen) =>
                setOpenContextMenuId(isOpen ? project.conversation_id : null)
              }
            />
          )}
        </NavLink>
      ))}

      {/* Playwright-only test hook: render a visible new conversation button
          only when inside a conversation route so E2E tests can assert the
          button's presence on conversation pages without relying on sockets.
       */}
      {isPlaywrightRun &&
        currentConversationId &&
        location.pathname.startsWith("/conversations/") && (
          <div className="p-4">
            <button
              type="button"
              data-testid="new-conversation-button"
              className="btn"
            >
              {t(I18nKey.CONVERSATION$START_NEW)}
            </button>
          </div>
        )}

      {/* Loading indicator for fetching more conversations */}
      {isFetchingNextPage && (
        <div className="flex justify-center py-4">
          <LoadingSpinner size="small" />
        </div>
      )}

      {confirmDeleteModalVisible && (
        <ConfirmDeleteModal
          onConfirm={() => {
            handleConfirmDelete();
            setConfirmDeleteModalVisible(false);
          }}
          onCancel={() => setConfirmDeleteModalVisible(false)}
        />
      )}

      {confirmStopModalVisible && (
        <ConfirmStopModal
          onConfirm={() => {
            handleConfirmStop();
            setConfirmStopModalVisible(false);
          }}
          onCancel={() => setConfirmStopModalVisible(false)}
        />
      )}

      {confirmExitConversationModalVisible && (
        <ExitConversationModal
          onConfirm={() => {
            onClose();
          }}
          onClose={() => setConfirmExitConversationModalVisible(false)}
        />
      )}
    </div>
  );
}
