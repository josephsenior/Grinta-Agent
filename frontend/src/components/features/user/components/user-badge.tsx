import { User, Crown } from "lucide-react";

interface UserBadgeProps {
  userEmail?: string;
  hasProAccess: boolean;
  size?: "sm" | "md";
}

export function UserBadge({
  userEmail,
  hasProAccess,
  size = "sm",
}: UserBadgeProps) {
  const sizeClasses = {
    sm: "w-8 h-8",
    md: "w-10 h-10",
  };
  const iconSizes = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
  };
  const textSizes = {
    sm: "text-xs",
    md: "text-sm",
  };

  return (
    <div className="relative">
      <div
        className={`${sizeClasses[size]} rounded-full bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center shadow-lg shadow-brand-500/20`}
      >
        {userEmail ? (
          <span className={`${textSizes[size]} font-semibold text-white`}>
            {userEmail[0].toUpperCase()}
          </span>
        ) : (
          <User className={`${iconSizes[size]} text-white`} />
        )}
      </div>
      {hasProAccess && (
        <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-yellow-400 border-2 border-black flex items-center justify-center shadow-lg">
          <Crown className="h-2.5 w-2.5 text-black" />
        </div>
      )}
    </div>
  );
}
