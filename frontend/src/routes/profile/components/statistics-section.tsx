import { useTranslation } from "react-i18next";
import { Card } from "#/components/ui/card";
import { LoadingSpinner } from "#/components/shared/loading-spinner";

interface Statistics {
  total_conversations: number;
  active_conversations: number;
  total_cost: number;
}

interface StatisticsSectionProps {
  statistics: Statistics | undefined;
  isLoading: boolean;
}

interface StatCardProps {
  label: string;
  value: string | number;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-6 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
      <div className="space-y-2">
        <p className="text-xs font-medium text-[#94A3B8]">{label}</p>
        <p className="text-2xl font-bold text-[#FFFFFF] leading-tight">
          {value}
        </p>
      </div>
    </Card>
  );
}

export function StatisticsSection({
  statistics,
  isLoading,
}: StatisticsSectionProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
        <div className="flex items-center justify-center">
          <LoadingSpinner size="medium" />
        </div>
      </Card>
    );
  }

  if (!statistics) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatCard
        label={t("profile.totalConversations")}
        value={statistics.total_conversations}
      />
      <StatCard
        label={t("profile.activeConversations")}
        value={statistics.active_conversations}
      />
      <StatCard
        label={t("profile.totalCost")}
        value={`$${statistics.total_cost.toFixed(2)}`}
      />
    </div>
  );
}
