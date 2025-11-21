import { Crown } from "lucide-react";
import { UserBadge } from "./user-badge";

interface UserProfileHeaderProps {
  username?: string;
  userEmail?: string;
  isUserAdmin: boolean;
  hasProAccess: boolean;
  isSaas: boolean;
  balance: number | undefined;
}

export function UserProfileHeader({
  username,
  userEmail,
  isUserAdmin,
  hasProAccess,
  isSaas,
  balance,
}: UserProfileHeaderProps) {
  return (
    <div className="px-4 py-3 border-b border-white/10">
      <div className="flex items-center gap-3">
        <UserBadge
          userEmail={userEmail}
          hasProAccess={hasProAccess}
          size="md"
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate">
            {username || userEmail || "Account"}
          </p>
          {isUserAdmin && (
            <p className="text-xs text-brand-400 font-medium flex items-center gap-1">
              Admin
            </p>
          )}
          {(() => {
            if (hasProAccess) {
              return (
                <p className="text-xs text-yellow-400 font-medium flex items-center gap-1">
                  <Crown className="h-3 w-3" />
                  Pro Member
                </p>
              );
            }
            if (isSaas) {
              return <p className="text-xs text-white/60">Free Tier</p>;
            }
            return null;
          })()}
          {isSaas && balance !== undefined && (
            <p className="text-xs text-white/60 mt-0.5">
              Balance: ${Number(balance).toFixed(2)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
