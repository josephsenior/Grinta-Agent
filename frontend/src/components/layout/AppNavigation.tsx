import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  User,
  Bell,
  HelpCircle,
  Database,
  Search,
  DollarSign,
  Settings,
  Keyboard,
} from "lucide-react";
import { cn } from "#/utils/utils";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { KeyboardShortcutsPanel } from "#/components/features/chat/keyboard-shortcuts-panel";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  requiresPro?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

export function AppNavigation() {
  const location = useLocation();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const [showShortcutsPanel, setShowShortcutsPanel] = React.useState(false);

  const hasPro = subscriptionAccess?.status === "ACTIVE";

  // Simplified navigation - all settings consolidated under single entry
  const navGroups: NavGroup[] = [
    {
      title: "Main",
      items: [
        { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
        { to: "/conversations", label: "Conversations", icon: MessageSquare },
        { to: "/search", label: "Search", icon: Search },
        { to: "/database-browser", label: "Database Browser", icon: Database },
        { to: "/profile", label: "Profile", icon: User },
        { to: "/notifications", label: "Notifications", icon: Bell },
        { to: "/pricing", label: "Pricing", icon: DollarSign },
        { to: "/help", label: "Help & Support", icon: HelpCircle },
      ],
    },
    {
      title: "Settings",
      items: [{ to: "/settings", label: "Settings", icon: Settings }],
    },
  ];

  // Filter out pro-only items if user doesn't have pro
  const filteredGroups = navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.requiresPro || hasPro),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <div className="space-y-8">
      {filteredGroups.map((group) => (
        <div key={group.title} className="space-y-3">
          <h3 className="px-3 text-xs font-semibold uppercase tracking-[0.2em] text-white/50">
            {group.title}
          </h3>
          <nav className="space-y-1">
            {group.items.map(({ to, label, icon: Icon }) => {
              const isActive =
                location.pathname === to ||
                (to !== "/dashboard" && location.pathname.startsWith(to));
              return (
                <NavLink
                  key={to}
                  to={to}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-white/10 border border-white/20 text-white"
                      : "text-white/70 hover:text-white hover:bg-white/5",
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0 text-white/50" />
                  <span>{label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      ))}

      {/* Keyboard Shortcuts Section */}
      <div className="space-y-3 pt-4 border-t border-white/10">
        <h3 className="px-3 text-xs font-semibold uppercase tracking-[0.2em] text-white/50">
          Help
        </h3>
        <nav className="space-y-1">
          <button
            type="button"
            onClick={() => setShowShortcutsPanel(true)}
            className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 text-white/70 hover:text-white hover:bg-white/5"
          >
            <Keyboard className="h-4 w-4 flex-shrink-0 text-white/50" />
            <span>Keyboard Shortcuts</span>
          </button>
        </nav>
      </div>

      {/* Keyboard Shortcuts Panel */}
      <KeyboardShortcutsPanel
        isOpen={showShortcutsPanel}
        onClose={() => setShowShortcutsPanel(false)}
      />
    </div>
  );
}
