import React, { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useDashboardStats } from "#/hooks/query/use-dashboard-stats";
import { useBalance } from "#/hooks/query/use-balance";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useIsCreatingConversation } from "#/hooks/use-is-creating-conversation";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";
import { SEO } from "#/components/shared/SEO";
import { useGSAPFadeIn } from "#/hooks/use-gsap-animations";
import { useDashboardAnimations } from "./dashboard/hooks/use-dashboard-animations";
import { QuickStatsSection } from "./dashboard/components/quick-stats-section";
import { QuickActionsSection } from "./dashboard/components/quick-actions-section";
import { RecentConversationsSection } from "./dashboard/components/recent-conversations-section";
import { ActivityFeedSection } from "./dashboard/components/activity-feed-section";

export default function Dashboard(): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const isCreatingConversationElsewhere = useIsCreatingConversation();
  const { data: balance, isLoading: balanceLoading } = useBalance();
  const {
    data: dashboardStats,
    isLoading: dashboardLoading,
    error: dashboardError,
  } = useDashboardStats(5, 10);

  const hasDashboardError =
    dashboardError !== null && dashboardError !== undefined;

  // GSAP animation refs
  const headerRef = useGSAPFadeIn<HTMLDivElement>({
    delay: 0.1,
    duration: 0.6,
  });
  const quickStatsRef = useRef<HTMLDivElement>(null);
  const quickActionsRef = useRef<HTMLDivElement>(null);
  const recentConversationsRef = useRef<HTMLDivElement>(null);
  const activityFeedRef = useRef<HTMLDivElement>(null);

  useDashboardAnimations({
    refs: {
      quickStatsRef,
      quickActionsRef,
      recentConversationsRef,
      activityFeedRef,
    },
    isLoading: dashboardLoading,
    hasError: hasDashboardError,
    stats: dashboardStats,
  });

  const handleNewConversation = () => {
    if (isPending || isCreatingConversationElsewhere) return;
    createConversation(
      {},
      {
        onSuccess: (data) => {
          try {
            localStorage.setItem(
              "RECENT_CONVERSATION_ID",
              data.conversation_id,
            );
          } catch (e) {
            // ignore storage errors
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  };

  const handleViewAllConversations = () => {
    navigate("/conversations");
  };

  const handleViewAnalytics = () => {
    navigate("/settings/analytics");
  };

  const handleViewBilling = () => {
    navigate("/settings/billing");
  };

  // Helper function to normalize balance value
  const normalizeBalance = (
    balanceValue: string | number | undefined,
  ): number | undefined => {
    if (balanceValue === undefined) {
      return undefined;
    }
    if (typeof balanceValue === "string") {
      return parseFloat(balanceValue);
    }
    return balanceValue;
  };

  return (
    <AuthGuard>
      <SEO
        title={t("dashboard.title", "Dashboard")}
        description={t(
          "dashboard.description",
          "Manage your AI development projects, view statistics, and access recent conversations.",
        )}
        keywords={t(
          "dashboard.keywords",
          "dashboard, projects, AI development, conversations",
        )}
        noindex
      />
      <AppLayout>
        <div className="space-y-8">
          <div ref={headerRef}>
            <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
              {t("dashboard.title", "Dashboard")}
            </h1>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <QuickStatsSection
              isLoading={dashboardLoading}
              stats={dashboardStats?.quick_stats ?? null}
              balance={normalizeBalance(balance)}
              balanceLoading={balanceLoading}
              quickStatsRef={quickStatsRef}
            />

            <QuickActionsSection
              onCreateConversation={handleNewConversation}
              onViewAllConversations={handleViewAllConversations}
              onViewAnalytics={handleViewAnalytics}
              onViewBilling={handleViewBilling}
              balance={normalizeBalance(balance)}
              quickActionsRef={quickActionsRef}
            />
          </div>

          <RecentConversationsSection
            isLoading={dashboardLoading}
            hasError={hasDashboardError}
            conversations={dashboardStats?.recent_conversations ?? []}
            onCreateConversation={handleNewConversation}
            isCreating={isPending || isCreatingConversationElsewhere}
            conversationsRef={recentConversationsRef}
          />

          {dashboardStats?.activity_feed && (
            <ActivityFeedSection
              activityFeed={dashboardStats.activity_feed}
              activityFeedRef={activityFeedRef}
            />
          )}
        </div>
      </AppLayout>
    </AuthGuard>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
