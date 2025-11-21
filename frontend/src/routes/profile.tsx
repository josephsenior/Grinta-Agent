import React from "react";
import { useTranslation } from "react-i18next";
import { Activity } from "lucide-react";
import { useUserStatistics, useUserActivity } from "#/hooks/query/use-profile";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";
import { useProfileData } from "./profile/hooks/use-profile-data";
import { UserInfoCard } from "./profile/components/user-info-card";
import { StatisticsSection } from "./profile/components/statistics-section";
import { ActivitySection } from "./profile/components/activity-section";

/**
 * Profile Page
 * Layout matches specification exactly:
 * - Sidebar + Header (via AppLayout)
 * - Page Title: "Profile"
 * - User Info Card (Avatar, Name, Email, Role)
 * - Statistics (3 columns: Total, Active, Cost)
 * - Recent Activity Timeline
 */
export default function ProfilePage() {
  const { t } = useTranslation();
  const { data: statistics, isLoading: statsLoading } = useUserStatistics();
  const { data: activity, isLoading: activityLoading } = useUserActivity(10);

  const {
    isSaas,
    hasProAccess,
    userEmail,
    username,
    userRole,
    isUserAdmin,
    avatarLetter,
  } = useProfileData();

  return (
    <AuthGuard>
      <AppLayout>
        <div className="space-y-8">
          {/* Page Title: Profile */}
          <div>
            <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
              {t("profile.title")}
            </h1>
          </div>

          {/* User Info Card */}
          <UserInfoCard
            username={username}
            userEmail={userEmail}
            userRole={userRole}
            isUserAdmin={isUserAdmin}
            hasProAccess={hasProAccess}
            isSaas={isSaas}
            avatarLetter={avatarLetter}
          />

          {/* Statistics - 3 columns: Total, Active, Cost */}
          <div className="space-y-4">
            <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2]">
              {t("profile.statistics")}
            </h2>
            <StatisticsSection
              statistics={statistics}
              isLoading={statsLoading}
            />
          </div>

          {/* Recent Activity Timeline */}
          <div className="space-y-4">
            <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
              <Activity className="h-5 w-5 text-[#8b5cf6]" />
              {t("profile.recentActivity")}
            </h2>
            <ActivitySection activity={activity} isLoading={activityLoading} />
          </div>
        </div>
      </AppLayout>
    </AuthGuard>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
