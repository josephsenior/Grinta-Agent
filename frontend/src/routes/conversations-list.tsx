import React from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { MessageSquare, ChevronRight } from "lucide-react";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";

function ConversationsList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
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

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-violet-400 font-light">Loading conversations…</div>
      </div>
    );
  }
  
  if (isError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-red-400 font-light">Failed to load conversations.</div>
      </div>
    );
  }

  return (
    <div
      data-testid="conversations-list"
      className="min-h-screen pt-20 px-6 bg-black"
    >
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 data-testid="page-title" className="text-3xl font-light text-white mb-2">
            Conversations
          </h1>
          <p className="text-sm text-gray-500 font-light">
            {conversations.length} total
          </p>
        </div>

        {/* Conversation List */}
        <div className="space-y-2">
          {conversations.map((c) => (
            <button
              key={c.conversation_id}
              type="button"
              onClick={() => navigate(`/conversations/${c.conversation_id}`)}
              className="group w-full text-left p-4 rounded-lg bg-violet-500/[0.02] border border-violet-500/10 hover:border-violet-500/20 hover:bg-violet-500/[0.04] transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <MessageSquare className="w-4 h-4 text-violet-400/60 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-white font-normal truncate">
                      {c.title ||
                        `Conversation ${c.conversation_id.slice(0, 8)}...`}
                    </div>
                    {c.selected_repository && (
                      <div className="text-xs text-violet-300/50 mt-1 font-light">
                        {c.selected_repository}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-xs text-gray-500 font-light">
                    <ClientFormattedDate iso={c.created_at} />
                  </div>
                  <ChevronRight className="w-4 h-4 text-violet-400/40 group-hover:text-violet-400/70 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Load More */}
        {hasNextPage && (
          <div className="mt-8 flex justify-center">
            <button
              type="button"
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="px-6 py-2.5 rounded-lg border border-violet-500/20 text-violet-400 hover:border-violet-500/40 hover:bg-violet-500/5 transition-all duration-200 font-light text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isFetchingNextPage ? "Loading…" : "Load more"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

export default ConversationsList;
