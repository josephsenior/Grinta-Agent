import React, { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { useMenuItems } from "./hooks/use-menu-items";
import { useDropdownPosition } from "./hooks/use-dropdown-position";
import { useDropdownCloseHandlers } from "./hooks/use-dropdown-close-handlers";
import { UserBadge } from "./components/user-badge";
import { DropdownPortal } from "./user-profile-dropdown/dropdown-portal";
import { useUserData } from "./user-profile-dropdown/use-user-data";

export function UserProfileDropdown() {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const { isSaas, hasProAccess, userEmail, username, isUserAdmin, balance } =
    useUserData();

  const handleClose = () => setIsOpen(false);
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(!isOpen);
  };

  const menuItems = useMenuItems({
    onClose: handleClose,
  });

  const dropdownPosition = useDropdownPosition(isOpen, buttonRef);
  useDropdownCloseHandlers(isOpen, dropdownRef, handleClose);

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          ref={buttonRef}
          type="button"
          onClick={handleToggle}
          className={cn(
            "relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
            isOpen && "text-white bg-white/10",
          )}
          aria-label={t("COMMON$USER_SETTINGS", {
            defaultValue: "User settings",
          })}
          aria-expanded={isOpen}
        >
          <UserBadge userEmail={userEmail} hasProAccess={hasProAccess} />
        </button>
      </div>

      <DropdownPortal
        isOpen={isOpen}
        dropdownPosition={dropdownPosition}
        username={username}
        userEmail={userEmail}
        isUserAdmin={isUserAdmin}
        hasProAccess={hasProAccess}
        isSaas={isSaas}
        balance={balance}
        menuItems={menuItems}
      />
    </>
  );
}
