import React from "react";
import { MessageSquare, Settings, FolderOpen, Clock } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { cn } from "#/utils/utils";
import { triggerHaptic } from "#/utils/haptic-feedback";

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "chat",
    label: "Chat",
    icon: <MessageSquare className="w-5 h-5" />,
    path: "/conversations/new",
  },
  {
    id: "workspace",
    label: "Files",
    icon: <FolderOpen className="w-5 h-5" />,
    path: "/workspace",
  },
  {
    id: "history",
    label: "History",
    icon: <Clock className="w-5 h-5" />,
    path: "/conversations",
  },
  {
    id: "settings",
    label: "Settings",
    icon: <Settings className="w-5 h-5" />,
    path: "/settings",
  },
];

interface MobileBottomNavProps {
  className?: string;
}

export function MobileBottomNav({ className }: MobileBottomNavProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleNavClick = (path: string) => {
    triggerHaptic("selection");
    navigate(path);
  };

  return (
    <nav
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50",
        "md:hidden", // Only show on mobile
        "bg-background-primary/95 backdrop-blur-xl",
        "border-t border-border",
        "safe-area-bottom", // iOS safe area support
        className,
      )}
    >
      <div className="flex items-center justify-around h-16 px-2">
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname.startsWith(item.path);

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleNavClick(item.path)}
              className={cn(
                "flex flex-col items-center justify-center",
                "flex-1 h-full",
                "transition-all duration-200",
                "active:scale-95",
                "touch-manipulation", // Better touch response
              )}
              aria-label={item.label}
              aria-current={isActive ? "page" : undefined}
            >
              {/* Icon */}
              <div
                className={cn(
                  "flex items-center justify-center",
                  "w-10 h-10 rounded-xl",
                  "transition-all duration-200",
                  isActive && [
                    "bg-brand-500/20",
                    "text-violet-500",
                    "shadow-lg shadow-brand-500/20",
                  ],
                  !isActive && [
                    "text-foreground-secondary",
                    "hover:bg-background-tertiary",
                  ],
                )}
              >
                {item.icon}
              </div>

              {/* Label */}
              <span
                className={cn(
                  "text-xs font-medium mt-1",
                  "transition-all duration-200",
                  isActive ? "text-violet-500" : "text-foreground-secondary",
                )}
              >
                {item.label}
              </span>

              {/* Active Indicator */}
              {isActive && (
                <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-brand-500 rounded-full" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

