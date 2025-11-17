import React, { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import {
  User,
  Settings,
  CreditCard,
  LogOut,
  Crown,
  LayoutDashboard,
  Shield,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useLogout } from "#/hooks/auth/use-logout";
import { useAuth } from "#/context/auth-context";
import { useBalance } from "#/hooks/query/use-balance";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { isAdmin } from "#/utils/auth/permissions";
import { cn } from "#/utils/utils";

export function UserProfileDropdown() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { user, isAuthenticated } = useAuth();
  const logoutMutation = useLogout();
  const { data: balance } = useBalance();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const { data: config } = useConfig();
  const { data: settings } = useSettings();

  const isSaas = config?.APP_MODE === "saas";
  const hasProAccess = subscriptionAccess?.status === "ACTIVE";
  // Use auth user email if available, fallback to settings
  const userEmail =
    user?.email ?? settings?.EMAIL ?? settings?.GIT_USER_EMAIL ?? undefined;
  const username = user?.username;
  const userRole = user?.role;
  const isUserAdmin = isAdmin(user);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(target) &&
        !(
          target instanceof Element && target.closest("[data-profile-dropdown]")
        )
      ) {
        setIsOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
        document.removeEventListener("keydown", handleEscape);
      };
    }
  }, [isOpen]);

  const handleLogout = () => {
    logoutMutation.mutate();
    setIsOpen(false);
  };

  const menuItems = [
    {
      icon: LayoutDashboard,
      label: "Dashboard",
      onClick: () => {
        navigate("/dashboard");
        setIsOpen(false);
      },
    },
    {
      icon: User,
      label: "Profile",
      onClick: () => {
        navigate("/profile");
        setIsOpen(false);
      },
    },
    {
      icon: Settings,
      label: "Settings",
      onClick: () => {
        navigate("/settings");
        setIsOpen(false);
      },
    },
    ...(isUserAdmin
      ? [
          {
            icon: Shield,
            label: "Admin Panel",
            onClick: () => {
              navigate("/admin/users");
              setIsOpen(false);
            },
          },
        ]
      : []),
    ...(isSaas && balance !== undefined
      ? [
          {
            icon: CreditCard,
            label: "Billing & Credits",
            onClick: () => {
              navigate("/settings/billing");
              setIsOpen(false);
            },
            badge:
              balance !== undefined
                ? `$${Number(balance).toFixed(2)}`
                : undefined,
          },
        ]
      : []),
  ];

  const [dropdownPosition, setDropdownPosition] = useState<{
    top: number;
    right: number;
  } | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 8,
        right: window.innerWidth - rect.right,
      });
    } else {
      setDropdownPosition(null);
    }
  }, [isOpen]);

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          ref={buttonRef}
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
          className={cn(
            "relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
            isOpen && "text-white bg-white/10",
          )}
          aria-label={t("COMMON$USER_SETTINGS", {
            defaultValue: "User settings",
          })}
          aria-expanded={isOpen}
        >
          <div className="relative">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
              {userEmail ? (
                <span className="text-xs font-semibold text-white">
                  {userEmail[0].toUpperCase()}
                </span>
              ) : (
                <User className="h-4 w-4 text-white" />
              )}
            </div>
            {hasProAccess && (
              <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-yellow-400 border-2 border-black flex items-center justify-center shadow-lg">
                <Crown className="h-2.5 w-2.5 text-black" />
              </div>
            )}
          </div>
        </button>
      </div>

      {isOpen &&
        dropdownPosition &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            data-profile-dropdown
            className="fixed w-64 rounded-xl border border-white/10 bg-black/90 backdrop-blur-xl shadow-2xl z-[9999] overflow-hidden"
            style={{
              top: `${dropdownPosition.top}px`,
              right: `${dropdownPosition.right}px`,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
                    {userEmail ? (
                      <span className="text-sm font-semibold text-white">
                        {userEmail[0].toUpperCase()}
                      </span>
                    ) : (
                      <User className="h-5 w-5 text-white" />
                    )}
                  </div>
                  {hasProAccess && (
                    <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-yellow-400 border-2 border-black flex items-center justify-center shadow-lg">
                      <Crown className="h-2.5 w-2.5 text-black" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">
                    {username || userEmail || "Account"}
                  </p>
                  {isUserAdmin && (
                    <p className="text-xs text-brand-400 font-medium flex items-center gap-1">
                      Admin
                    </p>
                  )}
                  {hasProAccess ? (
                    <p className="text-xs text-yellow-400 font-medium flex items-center gap-1">
                      <Crown className="h-3 w-3" />
                      Pro Member
                    </p>
                  ) : isSaas ? (
                    <p className="text-xs text-white/60">Free Tier</p>
                  ) : null}
                  {isSaas && balance !== undefined && (
                    <p className="text-xs text-white/60 mt-0.5">
                      Balance: ${Number(balance).toFixed(2)}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Menu Items */}
            <div className="py-2">
              {menuItems.map((item, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={item.onClick}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-white/80 hover:text-white hover:bg-white/5 transition-colors"
                >
                  <item.icon className="h-4 w-4 text-white/60" />
                  <span className="flex-1 text-left">{item.label}</span>
                  {item.badge && (
                    <span className="text-xs font-medium text-white/60 bg-white/10 px-2 py-0.5 rounded">
                      {item.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Footer */}
            <div className="border-t border-white/10 px-4 py-2">
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-danger-400 hover:text-danger-300 hover:bg-danger-500/10 rounded-lg transition-colors"
              >
                <LogOut className="h-4 w-4" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
