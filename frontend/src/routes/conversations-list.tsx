import React from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare, ChevronRight, Sparkles } from "lucide-react";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { PageHero } from "#/components/layout/PageHero";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";

function ConversationsList() {
  const navigate = useNavigate();
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

  const handleNewConversation = () => {
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
        <div className="text-red-400 font-light">
          Failed to load conversations.
        </div>
      </div>
    );
  }

  return (
    <main
      data-testid="conversations-list"
      className="min-h-screen bg-black pt-24 pb-20"
    >
      <PageHero
        eyebrow="Workspace"
        title="All conversations at a glance."
        description="Searchable history, latency insights, and repository context for every run."
        align="left"
        stats={[
          {
            label: "Active threads",
            value: conversations.length.toString().padStart(2, "0"),
            helper: "Stored in this workspace",
          },
          {
            label: "Latency",
            value: "2.7s p95",
            helper: "Live beta measurement",
          },
          {
            label: "Success",
            value: "96%",
            helper: "Passing guardrails",
          },
        ]}
        actions={
          <button
            type="button"
            onClick={handleNewConversation}
            disabled={isPending}
            className="inline-flex items-center gap-2 px-5 h-12 rounded-2xl bg-white text-black font-semibold disabled:opacity-60"
          >
            <Sparkles className="w-4 h-4" />
            Start new run
          </button>
        }
      />

      <div className="px-6">
        <div className="max-w-4xl mx-auto space-y-3">
          {conversations.map((c) => (
            <button
              key={c.conversation_id}
              type="button"
              onClick={() => navigate(`/conversations/${c.conversation_id}`)}
              className="group w-full text-left rounded-3xl border border-white/10 bg-white/5 p-5 hover:border-brand-500/40 hover:bg-white/10 transition"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-brand-500/20 flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-brand-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate">
                    {c.title ||
                      `Conversation ${c.conversation_id.slice(0, 8)}…`}
                  </p>
                  <div className="flex flex-wrap gap-3 text-sm text-foreground-tertiary mt-1">
                    <ClientFormattedDate iso={c.created_at} />
                    {c.selected_repository && (
                      <span>• {c.selected_repository}</span>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-white/40 group-hover:text-white" />
              </div>
            </button>
          ))}
        </div>

        {hasNextPage && (
          <div className="max-w-4xl mx-auto mt-8 flex justify-center">
            <button
              type="button"
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="px-6 h-11 rounded-2xl border border-white/20 text-white/80 hover:border-white hover:text-white transition disabled:opacity-50"
            >
              {isFetchingNextPage ? "Loading…" : "Load more"}
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

export default ConversationsList;
