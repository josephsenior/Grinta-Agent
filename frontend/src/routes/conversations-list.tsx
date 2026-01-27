import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  MessageSquare,
  ChevronRight,
  Plus,
  Search,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { cn } from "#/utils/utils";
import type { ConversationStatus } from "#/types/conversation-status";
import { WelcomeScreen } from "#/components/features/onboarding/welcome-screen";

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

/**
 * Conversation Card Component
 * Matches design system: Standard Card
 * Shows: Title, Preview, Date & Status
 */
function ConversationCard({
  title,
  preview,
  date,
  status,
  onClick,
}: {
  title: string;
  preview?: string;
  date: string;
  status?: "active" | "completed" | "failed";
  onClick: () => void;
}) {
  const { t } = useTranslation();
  const statusConfig = {
    active: {
      icon: Clock,
      label: t(I18nKey.CONVERSATIONS$STATUS_ACTIVE),
      color: "text-[var(--text-warning)]",
      bg: "bg-[var(--text-warning)]/10",
    },
    completed: {
      icon: CheckCircle,
      label: t(I18nKey.CONVERSATIONS$STATUS_COMPLETED),
      color: "text-[var(--text-success)]",
      bg: "bg-[var(--text-success)]/10",
    },
    failed: {
      icon: XCircle,
      label: t(I18nKey.CONVERSATIONS$STATUS_FAILED),
      color: "text-[var(--text-danger)]",
      bg: "bg-[var(--text-danger)]/10",
    },
  };

  const statusInfo = status ? statusConfig[status] : null;
  const StatusIcon = statusInfo?.icon;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group w-full text-left h-full",
        "bg-[var(--bg-elevated)] border-none rounded-lg p-4",
        "transition-all duration-200",
        "hover:bg-[var(--bg-tertiary)] hover:shadow-lg",
        "flex flex-col",
      )}
    >
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg bg-[var(--bg-primary)] flex items-center justify-center flex-shrink-0 transition-colors">
          <MessageSquare className="h-5 w-5 text-[var(--text-success)]" />
        </div>
        <div className="flex-1 min-w-0">
          {/* Title */}
          <p className="text-sm font-semibold text-[var(--text-primary)] line-clamp-2 mb-1.5 group-hover:text-[var(--text-primary)] transition-colors">
            {title}
          </p>
          {/* Preview */}
          {preview && (
            <p className="text-xs text-[var(--text-tertiary)] line-clamp-2 mb-2">
              {preview}
            </p>
          )}
        </div>
      </div>

      {/* Date & Status - Bottom aligned */}
      <div className="mt-auto flex items-center justify-between gap-2 pt-3 border-t border-transparent">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-[var(--text-tertiary)]">
            <ClientFormattedDate iso={date} />
          </span>
          {statusInfo && StatusIcon && (
            <>
              <span className="text-xs text-[var(--border-primary)]">•</span>
              <span
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium",
                  statusInfo.bg,
                  statusInfo.color,
                )}
              >
                <StatusIcon className="h-3 w-3" />
                {statusInfo.label}
              </span>
            </>
          )}
        </div>
        <ChevronRight className="h-4 w-4 text-[var(--text-tertiary)] transition-all group-hover:translate-x-1 group-hover:text-[var(--border-accent)] flex-shrink-0" />
      </div>
    </button>
  );
}

/**
 * Conversations List Page
 * Layout matches specification exactly:
 * - Sidebar + Header (via AppLayout)
 * - Page Title: "Conversations"
 * - Search, Filter, and + New button in header area
 * - Conversation cards with Title, Preview, Date & Status
 * - Load More button
 */
export default function ConversationsList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dateFilter, setDateFilter] = useState<string>("all");
  const [modelFilter, setModelFilter] = useState<string>("all");

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

  // Filter conversations based on search and filters
  const filteredConversations = React.useMemo(() => {
    let filtered = conversations;

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.title?.toLowerCase().includes(query) ||
          c.conversation_id.toLowerCase().includes(query),
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter((c) => {
        const uiStatus = mapConversationStatusToUI(c.status);
        return uiStatus === statusFilter;
      });
    }

    return filtered;
  }, [conversations, searchQuery, statusFilter, dateFilter, modelFilter]);

  const handleNewConversation = () => {
    if (isPending) return;
    createConversation(
      {},
      {
        onSuccess: (response) => {
          try {
            localStorage.setItem(
              "RECENT_CONVERSATION_ID",
              response.conversation_id,
            );
          } catch (error) {
            // ignore storage errors
          }
          navigate(`/conversations/${response.conversation_id}`);
        },
        onError: (error) => {
          displayErrorToast(error);
        },
      },
    );
  };

  // Determine status from conversation using API status field
  const getConversationStatus = (conv?: {
    status?: ConversationStatus | null;
  }): "active" | "completed" | "failed" | undefined => {
    if (!conv) {
      return undefined;
    }
    return mapConversationStatusToUI(conv.status);
  };
  return (
    <div
      data-testid="conversations-list"
      className="h-full w-full flex flex-col bg-[var(--bg-primary)] overflow-hidden"
    >
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            {/* Page Title: Conversations */}
            <div>
              <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
                {t(I18nKey.CONVERSATIONS$TITLE)}
              </h1>
              <p className="text-sm text-[var(--text-tertiary)]">
                {t(
                  "conversations.description",
                  "Manage and browse your conversations",
                )}
              </p>
            </div>

            {/* Search, Filter, and + New button */}
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--text-tertiary)]" />
                <Input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t(I18nKey.CONVERSATIONS$SEARCH_PLACEHOLDER)}
                  className="pl-9 pr-3 py-2 bg-[var(--bg-input)] border-[var(--border-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] rounded-lg focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] text-sm transition-all"
                />
              </div>

              {/* Filters */}
              <div className="flex gap-2">
                {/* Status Filter */}
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 bg-[var(--bg-input)] border border-[var(--border-primary)] text-[var(--text-primary)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] focus:border-[var(--border-accent)] text-sm transition-all"
                >
                  <option value="all">
                    {t(I18nKey.CONVERSATIONS$FILTER_ALL_STATUS)}
                  </option>
                  <option value="active">
                    {t(I18nKey.CONVERSATIONS$STATUS_ACTIVE)}
                  </option>
                  <option value="completed">
                    {t(I18nKey.CONVERSATIONS$STATUS_COMPLETED)}
                  </option>
                  <option value="failed">
                    {t(I18nKey.CONVERSATIONS$STATUS_FAILED)}
                  </option>
                </select>

                {/* Date Filter */}
                <select
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                  className="px-3 py-2 bg-[var(--bg-input)] border border-[var(--border-primary)] text-[var(--text-primary)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] focus:border-[var(--border-accent)] text-sm transition-all"
                >
                  <option value="all">
                    {t(I18nKey.CONVERSATIONS$FILTER_ALL_TIME)}
                  </option>
                  <option value="today">
                    {t(I18nKey.CONVERSATIONS$FILTER_TODAY)}
                  </option>
                  <option value="week">
                    {t(I18nKey.CONVERSATIONS$FILTER_THIS_WEEK)}
                  </option>
                  <option value="month">
                    {t(I18nKey.CONVERSATIONS$FILTER_THIS_MONTH)}
                  </option>
                </select>

                {/* Model Filter */}
                <select
                  value={modelFilter}
                  onChange={(e) => setModelFilter(e.target.value)}
                  className="px-3 py-2 bg-[var(--bg-input)] border border-[var(--border-primary)] text-[var(--text-primary)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] focus:border-[var(--border-accent)] text-sm transition-all"
                >
                  <option value="all">
                    {t(I18nKey.CONVERSATIONS$FILTER_ALL_MODELS)}
                  </option>
                  {/* Model options would come from API */}
                </select>
              </div>

              {/* + New Button */}
              <Button
                onClick={handleNewConversation}
                disabled={isPending}
                className="bg-[var(--text-accent)] hover:bg-[var(--text-accent)]/90 text-white rounded-lg px-6 py-2 shadow-lg shadow-[var(--text-accent)]/20 active:scale-95 font-bold disabled:opacity-60 text-sm transition-all duration-200 flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                {t(I18nKey.CONVERSATIONS$NEW_BUTTON)}
              </Button>
            </div>

            {/* Conversation Cards */}
            {(() => {
              if (isLoading) {
                return (
                  <div className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-lg p-8">
                    <div className="flex items-center justify-center">
                      <LoadingSpinner size="medium" />
                    </div>
                  </div>
                );
              }

              if (isError) {
                return (
                  <div className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-lg p-8 text-center">
                    <MessageSquare className="w-10 h-10 mx-auto mb-3 text-[var(--text-tertiary)] opacity-50" />
                    <p className="text-sm text-[var(--text-primary)] mb-1">
                      {t(I18nKey.CONVERSATIONS$FAILED_TO_LOAD)}
                    </p>
                    <p className="text-xs text-[var(--text-tertiary)]">
                      {t(I18nKey.CONVERSATIONS$REFRESH_PAGE)}
                    </p>
                  </div>
                );
              }

              if (filteredConversations.length === 0) {
                if (searchQuery.trim()) {
                  // Show search empty state
                  return (
                    <div className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-lg p-12 text-center">
                      <div className="space-y-4">
                        <div className="w-16 h-16 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)] flex items-center justify-center mx-auto">
                          <Search className="h-8 w-8 text-[var(--text-tertiary)]" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
                            {t(I18nKey.CONVERSATIONS$NO_CONVERSATIONS_FOUND)}
                          </h3>
                          <p className="text-sm text-[var(--text-tertiary)]">
                            {t(I18nKey.CONVERSATIONS$ADJUST_SEARCH_FILTERS)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                }
                // Show welcome screen for empty state
                return (
                  <div className="py-8">
                    <WelcomeScreen
                      isNewUser={conversations.length === 0}
                      onDismiss={undefined}
                    />
                  </div>
                );
              }

              return (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                  {filteredConversations.map((conv) => (
                    <ConversationCard
                      key={conv.conversation_id}
                      title={
                        conv.title ||
                        t(I18nKey.CONVERSATIONS$DEFAULT_TITLE, {
                          id: conv.conversation_id.slice(0, 8),
                        })
                      }
                      preview={conv.selected_repository || undefined}
                      date={conv.last_updated_at || conv.created_at || ""}
                      status={getConversationStatus(conv)}
                      onClick={() =>
                        navigate(`/conversations/${conv.conversation_id}`)
                      }
                    />
                  ))}
                </div>
              );
            })()}

            {/* Load More Button */}
            {hasNextPage && (
              <div className="flex justify-center pt-4">
                <Button
                  onClick={() => fetchNextPage()}
                  disabled={isFetchingNextPage}
                  className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] text-[var(--text-primary)] rounded-lg px-4 py-2 hover:bg-[var(--bg-tertiary)] hover:border-[var(--border-accent)] transition-all duration-200 disabled:opacity-60 text-sm font-medium"
                >
                  {isFetchingNextPage ? "Loading…" : "Load More"}
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
