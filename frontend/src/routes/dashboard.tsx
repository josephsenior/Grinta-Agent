import React from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  MessageSquare,
  Sparkles,
  TrendingUp,
  Clock,
  DollarSign,
  Activity,
  ArrowRight,
  Plus,
  FileText,
  Zap,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import AnimatedBackground from "#/components/landing/AnimatedBackground";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { useBalance } from "#/hooks/query/use-balance";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useIsCreatingConversation } from "#/hooks/use-is-creating-conversation";
import { Button } from "#/components/ui/button";
import { Card, CardContent } from "#/components/ui/card";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { cn } from "#/utils/utils";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";

function StatCard({
  icon: Icon,
  label,
  value,
  change,
  href,
  className,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  change?: string;
  href?: string;
  className?: string;
}) {
  const content = (
    <Card
      className={cn(
        "group relative overflow-hidden border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 backdrop-blur-xl transition-all duration-300 hover:border-white/20 hover:shadow-lg hover:shadow-black/20",
        href && "cursor-pointer",
        className,
      )}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-white/60">
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-white">{value}</p>
              {change && (
                <span className="text-sm font-medium text-success-400">
                  {change}
                </span>
              )}
            </div>
          </div>
          {href && (
            <ArrowRight className="h-5 w-5 text-white/40 transition-transform group-hover:translate-x-1 group-hover:text-white/60" />
          )}
        </div>
      </CardContent>
    </Card>
  );

  if (href) {
    return <Link to={href}>{content}</Link>;
  }

  return content;
}

function RecentConversationCard({
  conversationId,
  title,
  updatedAt,
  onClick,
}: {
  conversationId: string;
  title: string;
  updatedAt: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="group w-full text-left rounded-xl border border-white/10 bg-black/60 p-4 transition-all duration-200 hover:border-white/20 hover:bg-white/5"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare className="h-4 w-4 text-white/60 flex-shrink-0" />
            <p className="text-sm font-medium text-white truncate">{title}</p>
          </div>
          <p className="text-xs text-white/50">
            <ClientFormattedDate iso={updatedAt} />
          </p>
        </div>
        <ArrowRight className="h-4 w-4 text-white/40 transition-transform group-hover:translate-x-1 group-hover:text-white/60 flex-shrink-0" />
      </div>
    </button>
  );
}

function QuickActionCard({
  icon: Icon,
  title,
  description,
  onClick,
  variant = "default",
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  onClick: () => void;
  variant?: "default" | "primary";
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group w-full text-left rounded-xl border p-5 transition-all duration-200",
        variant === "primary"
          ? "border-white/20 bg-gradient-to-br from-white/10 to-black/60 hover:from-white/15 hover:to-black/80"
          : "border-white/10 bg-black/60 hover:border-white/20 hover:bg-white/5",
      )}
    >
      <div className="flex items-start gap-4">
        <div
          className={cn(
            "rounded-lg p-3 transition-colors",
            variant === "primary"
              ? "bg-white/10 group-hover:bg-white/15"
              : "bg-white/5 group-hover:bg-white/10",
          )}
        >
          <Icon
            className={cn(
              "h-5 w-5",
              variant === "primary" ? "text-white" : "text-white/70",
            )}
          />
        </div>
        <div className="flex-1 space-y-1">
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          <p className="text-xs text-white/60">{description}</p>
        </div>
        <ArrowRight className="h-4 w-4 text-white/40 transition-transform group-hover:translate-x-1 group-hover:text-white/60" />
      </div>
    </button>
  );
}

// Dashboard page - main authenticated home page
export default function Dashboard(): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const isCreatingConversationElsewhere = useIsCreatingConversation();
  const { data: balance, isLoading: balanceLoading } = useBalance();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const {
    data: conversationsData,
    isLoading: conversationsLoading,
    error: conversationsError,
  } = usePaginatedConversations(5);

  const conversations = React.useMemo(
    () => conversationsData?.pages.flatMap((p) => p.results) ?? [],
    [conversationsData],
  );

  // Handle API errors gracefully
  const hasConversationsError =
    conversationsError !== null && conversationsError !== undefined;

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

  return (
    <AuthGuard>
      <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
        <div aria-hidden className="pointer-events-none">
          <AnimatedBackground />
        </div>
        <AppLayout>
          <div className="rounded-3xl border border-white/10 bg-black/60 backdrop-blur-xl p-6 sm:p-8 lg:p-10">
            {/* Header */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">
                    Dashboard
                  </h1>
                  <p className="text-white/60">
                    Welcome back! Here's what's happening with your workspace.
                  </p>
                </div>
                <Button
                  onClick={handleNewConversation}
                  disabled={isPending || isCreatingConversationElsewhere}
                  className="bg-white text-black hover:bg-white/90 font-semibold rounded-xl px-6 py-3 shadow-lg shadow-black/20"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  New Conversation
                </Button>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatCard
                icon={MessageSquare}
                label="Total Conversations"
                value={
                  typeof conversationsData?.pages[0]?.total_count === "number"
                    ? conversationsData.pages[0].total_count
                    : 0
                }
                href="/conversations"
              />
              <StatCard
                icon={Activity}
                label="Active Sessions"
                value={conversations.length}
                change="+2 today"
              />
              {balance !== undefined && (
                <StatCard
                  icon={DollarSign}
                  label="Account Balance"
                  value={
                    balanceLoading ? "..." : `$${Number(balance).toFixed(2)}`
                  }
                  href="/settings/billing"
                />
              )}
              <StatCard
                icon={TrendingUp}
                label="Success Rate"
                value="96%"
                change="+2% this week"
                href="/settings/analytics"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Recent Conversations */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    <Clock className="h-5 w-5 text-white/60" />
                    Recent Conversations
                  </h2>
                  <button
                    onClick={handleViewAllConversations}
                    className="text-sm text-white/60 hover:text-white transition-colors flex items-center gap-1"
                  >
                    View all
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>

                {conversationsLoading ? (
                  <Card className="border border-white/10 bg-black/60 p-8">
                    <div className="flex items-center justify-center">
                      <LoadingSpinner size="medium" />
                    </div>
                  </Card>
                ) : hasConversationsError ? (
                  <div className="text-center py-8 text-white/60">
                    <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm text-white/40 mb-2">
                      Unable to load conversations
                    </p>
                    <p className="text-xs text-white/30">
                      The API endpoint may not be available yet
                    </p>
                  </div>
                ) : conversations.length === 0 ? (
                  <Card className="border border-white/10 bg-black/60 p-8">
                    <div className="text-center space-y-4">
                      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto">
                        <MessageSquare className="h-8 w-8 text-white/40" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white mb-2">
                          No conversations yet
                        </h3>
                        <p className="text-sm text-white/60 mb-4">
                          Start your first conversation to begin building with
                          AI
                        </p>
                        <Button
                          onClick={handleNewConversation}
                          disabled={
                            isPending || isCreatingConversationElsewhere
                          }
                          className="bg-white text-black hover:bg-white/90 font-semibold rounded-xl"
                        >
                          <Plus className="mr-2 h-4 w-4" />
                          Start Conversation
                        </Button>
                      </div>
                    </div>
                  </Card>
                ) : (
                  <div className="space-y-3">
                    {conversations.map((conv) => (
                      <RecentConversationCard
                        key={conv.conversation_id}
                        conversationId={conv.conversation_id}
                        title={conv.title || "Untitled Conversation"}
                        updatedAt={conv.updated_at || new Date().toISOString()}
                        onClick={() =>
                          navigate(`/conversations/${conv.conversation_id}`)
                        }
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Quick Actions & Info */}
              <div className="space-y-4">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  <Zap className="h-5 w-5 text-white/60" />
                  Quick Actions
                </h2>

                <div className="space-y-3">
                  <QuickActionCard
                    icon={Sparkles}
                    title="New Conversation"
                    description="Start a new AI-powered conversation"
                    onClick={handleNewConversation}
                    variant="primary"
                  />
                  <QuickActionCard
                    icon={FileText}
                    title="View Analytics"
                    description="See detailed usage and performance metrics"
                    onClick={handleViewAnalytics}
                  />
                  {balance !== undefined && (
                    <QuickActionCard
                      icon={DollarSign}
                      title="Manage Billing"
                      description="Add credits and manage subscription"
                      onClick={handleViewBilling}
                    />
                  )}
                </div>

                {/* System Status */}
                <Card className="border border-white/10 bg-black/60 p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-2 h-2 rounded-full bg-success-400 animate-pulse" />
                    <h3 className="text-sm font-semibold text-white">
                      System Status
                    </h3>
                  </div>
                  <p className="text-xs text-white/60">
                    All systems operational
                  </p>
                </Card>
              </div>
            </div>
          </div>
        </AppLayout>
      </main>
    </AuthGuard>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
