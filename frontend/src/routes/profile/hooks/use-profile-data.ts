import { useAuth } from "#/context/auth-context";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { useUserProfile } from "#/hooks/query/use-profile";
import { isAdmin } from "#/utils/auth/permissions";

export function useProfileData() {
  const { user } = useAuth();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const { data: config } = useConfig();
  const { data: settings } = useSettings();
  const { data: profileData } = useUserProfile();

  const isSaas = config?.APP_MODE === "saas";
  const hasProAccess = subscriptionAccess?.status === "ACTIVE";
  const userEmail = profileData?.user?.email ?? user?.email ?? settings?.EMAIL;
  const username = profileData?.user?.username ?? user?.username;
  const userRole = profileData?.user?.role ?? user?.role ?? "User";
  const isUserAdmin = isAdmin(user);
  const avatarLetter = (userEmail?.[0] || username?.[0] || "U").toUpperCase();

  return {
    isSaas,
    hasProAccess,
    userEmail,
    username,
    userRole,
    isUserAdmin,
    avatarLetter,
  };
}
