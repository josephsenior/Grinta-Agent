import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Clock, ArrowRight, MessageSquare, Plus } from "lucide-react";
import { Card } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { useGSAPFadeIn } from "#/hooks/use-gsap-animations";
import { RecentConversationCard } from "./recent-conversation-card";

interface RecentConversationsSectionProps {
  isLoading: boolean;
  hasError: boolean;
  conversations: Array<{
    id: string;
    title?: string;
    updated_at?: string;
    created_at: string;
  }>;
  onCreateConversation: () => void;
  isCreating: boolean;
  conversationsRef: React.RefObject<HTMLDivElement | null>;
}

export function RecentConversationsSection({
  isLoading,
  hasError,
  conversations,
  onCreateConversation,
  isCreating,
  conversationsRef,
}: RecentConversationsSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const headerRef = useGSAPFadeIn<HTMLDivElement>({
    delay: 0.3,
    duration: 0.5,
  });

  const handleViewAll = () => {
    navigate("/conversations");
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div ref={headerRef} className="flex items-center justify-between">
          <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
            <Clock className="h-5 w-5 text-[#8b5cf6]" />
            {t("dashboard.recentConversations", "Recent Conversations")}
          </h2>
        </div>
        <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
          <div className="flex items-center justify-center">
            <LoadingSpinner size="medium" />
          </div>
        </Card>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="space-y-4">
        <div ref={headerRef} className="flex items-center justify-between">
          <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
            <Clock className="h-5 w-5 text-[#8b5cf6]" />
            {t("dashboard.recentConversations", "Recent Conversations")}
          </h2>
        </div>
        <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
          <MessageSquare className="w-12 h-12 mx-auto mb-4 text-[#94A3B8] opacity-50" />
          <p className="text-sm text-[#94A3B8] mb-2">
            {t("dashboard.unableToLoadData", "Unable to load dashboard data")}
          </p>
          <p className="text-xs text-[#6a6f7f]">
            {t("dashboard.pleaseRefresh", "Please try refreshing the page")}
          </p>
        </Card>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="space-y-4">
        <div ref={headerRef} className="flex items-center justify-between">
          <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
            <Clock className="h-5 w-5 text-[#8b5cf6]" />
            {t("dashboard.recentConversations", "Recent Conversations")}
          </h2>
        </div>
        <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
          <div className="space-y-4">
            <div className="w-16 h-16 rounded-full bg-[rgba(139,92,246,0.1)] flex items-center justify-center mx-auto">
              <MessageSquare className="h-8 w-8 text-[#8b5cf6]" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#FFFFFF] mb-2">
                {t("dashboard.noConversationsYet", "No conversations yet")}
              </h3>
              <p className="text-sm text-[#94A3B8] mb-4">
                {t(
                  "dashboard.startFirstConversation",
                  "Start your first conversation to begin building with AI",
                )}
              </p>
              <Button
                onClick={onCreateConversation}
                disabled={isCreating}
                className="bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white rounded-lg px-6 py-3 hover:brightness-110 active:brightness-95"
              >
                <Plus className="mr-2 h-4 w-4" />
                {t("dashboard.startConversation", "Start Conversation")}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div ref={headerRef} className="flex items-center justify-between">
        <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
          <Clock className="h-5 w-5 text-[#8b5cf6]" />
          {t("dashboard.recentConversations", "Recent Conversations")}
        </h2>
        <button
          type="button"
          onClick={handleViewAll}
          className="text-sm text-[#94A3B8] hover:text-[#FFFFFF] transition-colors flex items-center gap-1"
        >
          {t("common.viewAll", "View all")}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
      <div ref={conversationsRef} className="space-y-3">
        {conversations.map((conv) => (
          <RecentConversationCard
            key={conv.id}
            title={conv.title || "Untitled Conversation"}
            updatedAt={conv.updated_at || conv.created_at}
            onClick={() => navigate(`/conversations/${conv.id}`)}
          />
        ))}
      </div>
    </div>
  );
}
