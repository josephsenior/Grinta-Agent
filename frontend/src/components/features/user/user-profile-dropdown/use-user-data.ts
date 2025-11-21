import { useAuth } from "#/context/auth-context";
import { useBalance } from "#/hooks/query/use-balance";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { isAdmin } from "#/utils/auth/permissions";

export function useUserData() {
  const { user } = useAuth();
  const { data: balance } = useBalance();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const { data: config } = useConfig();
  const { data: settings } = useSettings();

  const isSaas = config?.APP_MODE === "saas";
  const hasProAccess = subscriptionAccess?.status === "ACTIVE";
  const userEmail =
    user?.email ?? settings?.EMAIL ?? settings?.GIT_USER_EMAIL ?? undefined;
  const username = user?.username;
  const isUserAdmin = isAdmin(user);

  const normalizedBalance = (() => {
    if (balance === undefined) return undefined;
    if (typeof balance === "string") return parseFloat(balance);
    return balance;
  })();

  return {
    isSaas,
    hasProAccess,
    userEmail,
    username,
    isUserAdmin,
    balance: normalizedBalance,
  };
}
