import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { MessageCircle, User, Info, Bell } from "lucide-react";

export function useHeaderNavigation() {
  const { t } = useTranslation();

  return useMemo(
    () => [
      {
        to: "/dashboard",
        label: t("COMMON$DASHBOARD", { defaultValue: "Dashboard" }),
        icon: MessageCircle,
      },
      {
        to: "/profile",
        label: t("COMMON$PROFILE", { defaultValue: "Profile" }),
        icon: User,
      },
      {
        to: "/notifications",
        label: t("COMMON$NOTIFICATIONS", { defaultValue: "Notifications" }),
        icon: Bell,
      },
      {
        to: "/help",
        label: t("COMMON$HELP", { defaultValue: "Help" }),
        icon: Info,
      },
    ],
    [t],
  );
}
