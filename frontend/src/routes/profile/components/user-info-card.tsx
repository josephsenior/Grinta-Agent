import { Settings, Edit, CreditCard, Key } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card } from "#/components/ui/card";
import { Button } from "#/components/ui/button";

interface UserInfoCardProps {
  username?: string;
  userEmail?: string;
  userRole: string;
  isUserAdmin: boolean;
  hasProAccess: boolean;
  isSaas: boolean;
  avatarLetter: string;
}

export function UserInfoCard({
  username,
  userEmail,
  userRole,
  isUserAdmin,
  hasProAccess,
  isSaas,
  avatarLetter,
}: UserInfoCardProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-6 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
      <div className="flex items-center gap-6">
        {/* Avatar */}
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#8b5cf6] to-[#7c3aed] flex items-center justify-center shadow-[0_4px_20px_rgba(139,92,246,0.3)]">
          <span className="text-2xl font-bold text-[#FFFFFF]">
            {avatarLetter}
          </span>
        </div>

        {/* User Info */}
        <div className="flex-1">
          <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] mb-1">
            {username || userEmail || t("profile.anonymousUser")}
          </h2>
          <p className="text-sm text-[#94A3B8] mb-2">{userEmail}</p>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs font-medium text-[#94A3B8]">
              {t("profile.roleLabel")}
            </span>
            <span className="text-xs font-medium text-[#FFFFFF]">
              {userRole.charAt(0).toUpperCase() + userRole.slice(1)}
            </span>
            {isUserAdmin && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[rgba(59,130,246,0.12)] text-[#3B82F6] text-xs font-medium">
                {t("profile.roles.admin")}
              </span>
            )}
            {hasProAccess && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[rgba(245,158,11,0.12)] text-[#F59E0B] text-xs font-medium">
                {t("profile.roles.pro")}
              </span>
            )}
          </div>
          {/* Quick Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              onClick={() => navigate("/settings/user")}
              className="bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-lg px-4 py-2 hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] transition-all duration-150 text-xs"
            >
              <Edit className="h-3 w-3 mr-1.5" />
              {t("profile.actions.editProfile")}
            </Button>
            {isSaas && (
              <Button
                onClick={() => navigate("/settings/billing")}
                className="bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-lg px-4 py-2 hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] transition-all duration-150 text-xs"
              >
                <CreditCard className="h-3 w-3 mr-1.5" />
                {t("profile.actions.billing")}
              </Button>
            )}
            <Button
              onClick={() => navigate("/settings/api-keys")}
              className="bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-lg px-4 py-2 hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] transition-all duration-150 text-xs"
            >
              <Key className="h-3 w-3 mr-1.5" />
              {t("profile.actions.apiKeys")}
            </Button>
            <Button
              onClick={() => navigate("/settings")}
              className="bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-lg px-4 py-2 hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] transition-all duration-150 text-xs"
            >
              <Settings className="h-3 w-3 mr-1.5" />
              {t("profile.actions.settings")}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
