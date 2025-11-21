import React from "react";
import { createPortal } from "react-dom";
import { LogOut } from "lucide-react";
import { UserProfileHeader } from "../components/user-profile-header";
import { MenuItemsList } from "../components/menu-items-list";

interface DropdownPortalProps {
  isOpen: boolean;
  dropdownPosition: { top: number; right: number } | null;
  username: string | undefined;
  userEmail: string | undefined;
  isUserAdmin: boolean;
  hasProAccess: boolean;
  isSaas: boolean;
  balance: number | undefined;
  menuItems: Array<{
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    onClick: () => void;
    href?: string;
  }>;
  onLogout: () => void;
}

export function DropdownPortal({
  isOpen,
  dropdownPosition,
  username,
  userEmail,
  isUserAdmin,
  hasProAccess,
  isSaas,
  balance,
  menuItems,
  onLogout,
}: DropdownPortalProps) {
  if (!isOpen || !dropdownPosition || typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <div
      data-profile-dropdown
      className="fixed w-64 rounded-xl border border-white/10 bg-black/90 backdrop-blur-xl shadow-2xl z-[9999] overflow-hidden"
      style={{
        top: `${dropdownPosition.top}px`,
        right: `${dropdownPosition.right}px`,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <UserProfileHeader
        username={username}
        userEmail={userEmail}
        isUserAdmin={isUserAdmin}
        hasProAccess={hasProAccess}
        isSaas={isSaas}
        balance={balance}
      />

      <MenuItemsList items={menuItems} />

      <div className="border-t border-white/10 px-4 py-2">
        <button
          type="button"
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-danger-400 hover:text-danger-300 hover:bg-danger-500/10 rounded-lg transition-colors"
        >
          <LogOut className="h-4 w-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>,
    document.body,
  );
}
