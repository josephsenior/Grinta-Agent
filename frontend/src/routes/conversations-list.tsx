import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageSquare,
  ChevronRight,
  Plus,
  Search,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { Button } from "#/components/ui/button";
import { Card } from "#/components/ui/card";
import { Input } from "#/components/ui/input";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";
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
  const statusConfig = {
    active: {
      icon: Clock,
      label: "Active",
      color: "text-[#F59E0B]",
      bg: "bg-[rgba(245,158,11,0.12)]",
    },
    completed: {
      icon: CheckCircle,
      label: "Completed",
      color: "text-[#10B981]",
      bg: "bg-[rgba(16,185,129,0.12)]",
    },
    failed: {
      icon: XCircle,
      label: "Failed",
      color: "text-[#EF4444]",
      bg: "bg-[rgba(239,68,68,0.12)]",
    },
  };

  const statusInfo = status ? statusConfig[status] : null;
  const StatusIcon = statusInfo?.icon;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group w-full text-left",
        "bg-[#000000] border border-[#1a1a1a] rounded-xl p-6",
        "shadow-[0_4px_20px_rgba(0,0,0,0.15)]",
        "transition-all duration-200",
        "hover:border-[#8b5cf6] hover:shadow-[0_8px_40px_rgba(0,0,0,0.2)]",
      )}
    >
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-[rgba(139,92,246,0.12)] flex items-center justify-center flex-shrink-0">
          <MessageSquare className="h-6 w-6 text-[#8b5cf6]" />
        </div>
        <div className="flex-1 min-w-0 space-y-2">
          {/* Title */}
          <p className="text-base font-semibold text-[#FFFFFF] truncate">
            {title}
          </p>
          {/* Preview */}
          {preview && (
            <p className="text-sm text-[#94A3B8] line-clamp-2">{preview}</p>
          )}
          {/* Date & Status */}
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs text-[#94A3B8]">
              <ClientFormattedDate iso={date} />
            </span>
            {statusInfo && StatusIcon && (
              <>
                <span className="text-xs text-[#6a6f7f]">•</span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium",
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
        </div>
        <ChevronRight className="h-5 w-5 text-[#94A3B8] transition-transform group-hover:translate-x-1 group-hover:text-[#8b5cf6] flex-shrink-0 mt-1" />
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
    <AuthGuard>
      <AppLayout>
        <div className="space-y-6">
          {/* Page Title: Conversations */}
          <div>
            <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
              Conversations
            </h1>
          </div>

          {/* Search, Filter, and + New button */}
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-[#94A3B8]" />
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search conversations..."
                className="pl-12 pr-4 py-3 bg-[#000000] border-[#1a1a1a] text-[#FFFFFF] placeholder:text-[#94A3B8] rounded-xl focus:border-[#8b5cf6] focus:ring-1 focus:ring-[#8b5cf6]"
              />
            </div>

            {/* Filters */}
            <div className="flex gap-2">
              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-3 bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8b5cf6] text-sm"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>

              {/* Date Filter */}
              <select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="px-4 py-3 bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8b5cf6] text-sm"
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
              </select>

              {/* Model Filter */}
              <select
                value={modelFilter}
                onChange={(e) => setModelFilter(e.target.value)}
                className="px-4 py-3 bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8b5cf6] text-sm"
              >
                <option value="all">All Models</option>
                {/* Model options would come from API */}
              </select>
            </div>

            {/* + New Button */}
            <Button
              onClick={handleNewConversation}
              disabled={isPending}
              className="bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white rounded-xl px-6 py-3 hover:brightness-110 active:brightness-95 shadow-[0_4px_20px_rgba(139,92,246,0.3)] font-semibold disabled:opacity-60"
            >
              <Plus className="h-4 w-4 mr-2" />
              New
            </Button>
          </div>

          {/* Conversation Cards */}
          {(() => {
            if (isLoading) {
              return (
                <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
                  <div className="flex items-center justify-center">
                    <LoadingSpinner size="medium" />
                  </div>
                </Card>
              );
            }

            if (isError) {
              return (
                <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4 text-[#94A3B8] opacity-50" />
                  <p className="text-sm text-[#94A3B8] mb-2">
                    Failed to load conversations
                  </p>
                  <p className="text-xs text-[#6a6f7f]">
                    Please try refreshing the page
                  </p>
                </Card>
              );
            }

            if (filteredConversations.length === 0) {
              return (
                <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
                  <div className="space-y-4">
                    <div className="w-16 h-16 rounded-full bg-[rgba(139,92,246,0.1)] flex items-center justify-center mx-auto">
                      <MessageSquare className="h-8 w-8 text-[#8b5cf6]" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-[#FFFFFF] mb-2">
                        {searchQuery.trim()
                          ? "No conversations found"
                          : "No conversations yet"}
                      </h3>
                      <p className="text-sm text-[#94A3B8] mb-4">
                        {searchQuery.trim()
                          ? "Try adjusting your search or filters"
                          : "Start your first conversation to begin building with AI"}
                      </p>
                      {!searchQuery.trim() && (
                        <Button
                          onClick={handleNewConversation}
                          disabled={isPending}
                          className="bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white rounded-lg px-6 py-3 hover:brightness-110 active:brightness-95"
                        >
                          <Plus className="mr-2 h-4 w-4" />
                          Start Conversation
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              );
            }

            return (
              <div className="space-y-3">
                {filteredConversations.map((conv) => (
                  <ConversationCard
                    key={conv.conversation_id}
                    title={
                      conv.title ||
                      `Conversation ${conv.conversation_id.slice(0, 8)}…`
                    }
                    preview={conv.selected_repository || undefined}
                    date={conv.updated_at || conv.created_at || ""}
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
                className="bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-xl px-6 py-3 hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] transition-all duration-150 disabled:opacity-60"
              >
                {isFetchingNextPage ? "Loading…" : "Load More"}
              </Button>
            </div>
          )}
        </div>
      </AppLayout>
    </AuthGuard>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
