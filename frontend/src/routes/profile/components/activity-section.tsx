import { Activity } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Card } from "#/components/ui/card";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { cn } from "#/utils/utils";

interface ActivityItem {
  id: string;
  description: string;
  timestamp: string;
}

interface ActivitySectionProps {
  activity: ActivityItem[] | undefined;
  isLoading: boolean;
}

export function ActivitySection({ activity, isLoading }: ActivitySectionProps) {
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

  if (!activity || activity.length === 0) {
    return (
      <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
        <Activity className="w-12 h-12 mx-auto mb-4 text-[#94A3B8] opacity-50" />
        <p className="text-sm text-[#94A3B8]">
          {t("profile.noRecentActivity")}
        </p>
      </Card>
    );
  }

  return (
    <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-6 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
      <div className="space-y-0">
        {activity.map((item, index) => (
          <div
            key={item.id}
            className={cn(
              "py-4 border-b border-[#1a1a1a] last:border-0",
              index === 0 && "pt-0",
              index === activity.length - 1 && "pb-0",
            )}
          >
            <p className="text-sm text-[#FFFFFF] mb-1">{item.description}</p>
            <p className="text-xs text-[#94A3B8]">
              <ClientFormattedDate iso={item.timestamp} />
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
