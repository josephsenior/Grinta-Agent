import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  MessageSquare,
  Plus,
  Search,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { cn } from "#/utils/utils";
import type { ConversationStatus } from "#/types/conversation-status";

/**
 * Maps API conversation status to UI status values
 */
function mapConversationStatusToUI(
  status?: ConversationStatus | null,
): "active" | "completed" | "failed" | undefined {
  if (!status) {
    return undefined;
  }

  switch (status) {
    case "RUNNING":
    case "STARTING":
      return "active";
    case "STOPPED":
    case "ARCHIVED":
      return "completed";
    case "ERROR":
      return "failed";
    default:
      return undefined;
  }
}

interface ConversationItemProps {
  title: string;
  status?: "active" | "completed" | "failed";
  isActive: boolean;
  onClick: () => void;
}

function ConversationItem({
  title,
  status,
  isActive,
  onClick,
}: ConversationItemProps) {
  const statusConfig = {
    active: {
      icon: Clock,
      color: "text-[var(--text-warning)]",
    },
    completed: {
      icon: CheckCircle,
      color: "text-[var(--text-success)]",
    },
    failed: {
      icon: XCircle,
      color: "text-[var(--text-danger)]",
    },
  };

  const statusInfo = status ? statusConfig[status] : null;
  const StatusIcon = statusInfo?.icon;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full text-left px-2.5 py-2 rounded-lg text-xs transition-all duration-200 group relative",
        "border border-transparent mb-0.5",
        isActive
          ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-[var(--border-secondary)] shadow-sm"
          : "text-[var(--text-tertiary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-secondary)]",
      )}
      title={title}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <MessageSquare
          className={cn(
            "w-3.5 h-3.5 shrink-0 transition-colors",
            isActive
              ? "text-[var(--text-accent)]"
              : "text-[var(--text-tertiary)] group-hover:text-[var(--text-accent)]",
          )}
        />
        <span className="truncate flex-1 font-medium">{title}</span>
        {statusInfo && StatusIcon && (
          <StatusIcon
            className={cn("w-3.5 h-3.5 shrink-0", statusInfo.color)}
          />
        )}
      </div>
      {isActive && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1 h-1 rounded-full bg-[var(--text-accent)] shadow-[0_0_8px_var(--text-accent)]" />
      )}
    </button>
  );
}

export function ConversationsSidebar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams<{ conversationId?: string }>();
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (showSearch) {
      searchInputRef.current?.focus();
    }
  }, [showSearch]);

  const { mutate: createConversation, isPending } = useCreateConversation();
  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = usePaginatedConversations(20);

  const conversations = React.useMemo(
    () => data?.pages.flatMap((p) => p.results) ?? [],
    [data],
  );

  // Filter conversations based on search
  const filteredConversations = React.useMemo(() => {
    if (!searchQuery.trim()) {
      return conversations;
    }
    const query = searchQuery.toLowerCase();
    return conversations.filter(
      (c) =>
        c.title?.toLowerCase().includes(query) ||
        c.conversation_id.toLowerCase().includes(query),
    );
  }, [conversations, searchQuery]);

  const handleNewConversation = React.useCallback(() => {
    createConversation(
      {},
      {
        onSuccess: (response) => {
          navigate(`/conversations/${response.conversation_id}`);
        },
        onError: (error) => {
          displayErrorToast(
            error instanceof Error
              ? error.message
              : "Failed to create conversation",
          );
        },
      },
    );
  }, [createConversation, navigate]);

  const handleConversationClick = React.useCallback(
    (conversationId: string) => {
      // Use replace: false to keep sidebar state, but prevent full page reload
      navigate(`/conversations/${conversationId}`, { replace: false });
    },
    [navigate],
  );

  return (
    <div className="h-full flex flex-col bg-[var(--bg-elevated)] border-r border-[var(--border-primary)]">
      {/* Modern Header */}
      <div className="px-3 py-2.5 border-b border-[var(--border-primary)] flex items-center gap-2 shrink-0">
        {showSearch ? (
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-tertiary)]" />
            <input
              ref={searchInputRef}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              onBlur={() => {
                if (!searchQuery) setShowSearch(false);
              }}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-[var(--bg-input)] border border-[var(--border-primary)] rounded-lg text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-[var(--border-accent)] transition-all"
            />
          </div>
        ) : (
          <>
            <div className="flex-1 flex items-center gap-2 px-1">
              <span className="text-[10px] font-bold text-[var(--text-tertiary)] uppercase tracking-wider">
                History
              </span>
            </div>
            <button
              type="button"
              onClick={() => setShowSearch(true)}
              className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded-lg transition-all duration-200 text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
              title="Search conversations"
            >
              <Search className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleNewConversation}
              disabled={isPending}
              className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded-lg transition-all duration-200 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] disabled:opacity-50 disabled:cursor-not-allowed"
              title="New conversation"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </>
        )}
      </div>

      {/* Modern Conversations List */}
      <div className="flex-1 overflow-y-auto px-1.5 py-1.5">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="small" />
          </div>
        )}

        {isError && (
          <div className="px-3 py-3 text-xs text-[var(--text-danger)] text-center rounded-lg bg-[var(--text-danger)]/10 border border-[var(--text-danger)]/20">
            {t(I18nKey.CONVERSATIONS$FAILED_TO_LOAD)}
          </div>
        )}

        {!isLoading && !isError && filteredConversations.length === 0 && (
          <div className="px-3 py-8 text-center">
            <MessageSquare className="w-6 h-6 text-[var(--text-tertiary)]/30 mx-auto mb-3" />
            <p className="text-xs text-[var(--text-tertiary)]">
              {searchQuery
                ? t(I18nKey.CONVERSATIONS$NO_CONVERSATIONS_FOUND)
                : t(I18nKey.CONVERSATION$NO_CONVERSATIONS)}
            </p>
          </div>
        )}

        {!isLoading && !isError && filteredConversations.length > 0 && (
          <div className="space-y-0.5">
            {filteredConversations.map((conv) => {
              const status = mapConversationStatusToUI(conv.status);
              return (
                <ConversationItem
                  key={conv.conversation_id}
                  title={
                    conv.title ||
                    t(I18nKey.CONVERSATIONS$DEFAULT_TITLE, {
                      id: conv.conversation_id.slice(0, 8),
                    })
                  }
                  status={status}
                  isActive={params.conversationId === conv.conversation_id}
                  onClick={() => handleConversationClick(conv.conversation_id)}
                />
              );
            })}
          </div>
        )}

        {/* Load More */}
        {hasNextPage && (
          <div className="px-2 py-2 mt-2">
            <button
              type="button"
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="w-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)] rounded-lg disabled:opacity-50 transition-all duration-200 border border-[var(--border-secondary)]"
            >
              {isFetchingNextPage ? t(I18nKey.HOME$LOADING) : "Load more"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
