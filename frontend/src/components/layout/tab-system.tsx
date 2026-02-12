import React, { useState, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { X, Plus } from "lucide-react";
import { cn } from "#/utils/utils";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

interface Tab {
  id: string;
  label: string;
  path: string;
  type: "conversation" | "file" | "settings";
  isActive: boolean;
}

interface TabSystemProps {
  onTabChange?: (tabId: string) => void;
  onNewTab?: () => void;
}

export function TabSystem({ onTabChange, onNewTab }: TabSystemProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [tabs, setTabs] = useState<Tab[]>([]);
  const { mutate: createConversation, isPending } = useCreateConversation();

  // Get current conversation ID from URL
  const currentConversationId = React.useMemo(() => {
    if (location.pathname.startsWith("/conversations/")) {
      const parts = location.pathname.split("/").filter(Boolean);
      const idx = parts.indexOf("conversations");
      return parts[idx + 1] || null;
    }
    return null;
  }, [location.pathname]);

  // Load conversations for tabs
  const { data: conversationsData } = usePaginatedConversations(10);
  const conversations = React.useMemo(
    () => conversationsData?.pages.flatMap((p) => p.results) ?? [],
    [conversationsData],
  );

  // Update tabs based on conversations
  React.useEffect(() => {
    const conversationTabs: Tab[] = conversations.slice(0, 10).map((conv) => ({
      id: conv.conversation_id,
      label: conv.title || `Conversation ${conv.conversation_id.slice(0, 8)}`,
      path: `/conversations/${conv.conversation_id}`,
      type: "conversation" as const,
      isActive: conv.conversation_id === currentConversationId,
    }));

    // Add current conversation if not in list
    if (
      currentConversationId &&
      !conversationTabs.find((t) => t.id === currentConversationId)
    ) {
      conversationTabs.unshift({
        id: currentConversationId,
        label: `Conversation ${currentConversationId.slice(0, 8)}`,
        path: `/conversations/${currentConversationId}`,
        type: "conversation",
        isActive: true,
      });
    }

    setTabs(conversationTabs);
  }, [conversations, currentConversationId]);

  const handleTabClick = useCallback(
    (tab: Tab) => {
      navigate(tab.path);
      onTabChange?.(tab.id);
    },
    [navigate, onTabChange],
  );

  const handleTabClose = useCallback(
    (e: React.MouseEvent, tab: Tab) => {
      e.stopPropagation();
      setTabs((prev) => prev.filter((t) => t.id !== tab.id));
      // If closing active tab, navigate to conversations list
      if (tab.isActive) {
        navigate("/conversations");
      }
    },
    [navigate],
  );

  const handleNewConversation = useCallback(() => {
    if (isPending) return;
    createConversation(
      {},
      {
        onSuccess: (response) => {
          navigate(`/conversations/${response.conversation_id}`);
          onNewTab?.();
        },
        onError: (error) => {
          displayErrorToast(error);
        },
      },
    );
  }, [createConversation, navigate, isPending, onNewTab]);

  if (tabs.length === 0) {
    return (
      <div className="h-9 bg-[var(--bg-secondary)] border-b border-[var(--border-primary)] flex items-center px-2">
        <button
          type="button"
          onClick={handleNewConversation}
          disabled={isPending}
          className="px-3 py-1 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] rounded-md flex items-center gap-1.5 disabled:opacity-50 transition-colors"
          title="New Conversation"
        >
          <Plus className="w-3 h-3" />
          <span>New</span>
        </button>
      </div>
    );
  }

  return (
    <div className="h-9 bg-[var(--bg-secondary)] border-b border-[var(--border-primary)] flex items-center overflow-x-auto flex-shrink-0 scrollbar-hide">
      <div className="flex items-center h-full min-w-0">
        {tabs.map((tab) => (
          <button
            type="button"
            key={tab.id}
            onClick={() => handleTabClick(tab)}
            className={cn(
              "h-full px-4 flex items-center gap-2 border-r border-[var(--border-primary)] text-xs transition-all group relative",
              tab.isActive
                ? "bg-[var(--bg-primary)] text-[var(--text-primary)]"
                : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]",
            )}
            title={tab.label}
          >
            <span className="truncate max-w-[160px] font-medium">
              {tab.label}
            </span>
            <button
              type="button"
              onClick={(e) => handleTabClose(e, tab)}
              className={cn(
                "opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded-md hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
                tab.isActive && "opacity-100",
              )}
              title="Close tab"
            >
              <X className="w-3 h-3" />
            </button>
            {tab.isActive && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--border-accent)]" />
            )}
          </button>
        ))}
        <button
          type="button"
          onClick={handleNewConversation}
          disabled={isPending}
          className="px-3 h-full text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors disabled:opacity-50"
          title="New Conversation"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
