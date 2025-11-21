import { MessageSquare, Activity, DollarSign, TrendingUp } from "lucide-react";
import { QuickStatCard } from "./quick-stat-card";

interface QuickStatsSectionProps {
  isLoading: boolean;
  stats: {
    total_conversations?: number;
    active_conversations?: number;
    success_rate?: number;
  } | null;
  balance: number | undefined;
  balanceLoading: boolean;
  quickStatsRef: React.RefObject<HTMLDivElement | null>;
}

export function QuickStatsSection({
  isLoading,
  stats,
  balance,
  balanceLoading,
  quickStatsRef,
}: QuickStatsSectionProps) {
  return (
    <div ref={quickStatsRef} className="lg:col-span-2 grid grid-cols-2 gap-4">
      <QuickStatCard
        icon={MessageSquare}
        label="Total Conversations"
        value={isLoading ? "..." : (stats?.total_conversations ?? 0)}
        href="/conversations"
      />
      <QuickStatCard
        icon={Activity}
        label="Active Sessions"
        value={isLoading ? "..." : (stats?.active_conversations ?? 0)}
      />
      {balance !== undefined && (
        <QuickStatCard
          icon={DollarSign}
          label="Account Balance"
          value={balanceLoading ? "..." : `$${Number(balance).toFixed(2)}`}
          href="/settings/billing"
        />
      )}
      <QuickStatCard
        icon={TrendingUp}
        label="Success Rate"
        value={
          isLoading ? "..." : `${Math.round((stats?.success_rate ?? 0) * 100)}%`
        }
        href="/settings/analytics"
      />
    </div>
  );
}
