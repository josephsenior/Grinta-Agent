import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  isInputElement,
  isModifierPressed,
  matchesKey,
} from "./utils/keyboard-utils";

interface NavigationShortcut {
  key: string;
  path: string;
  description: string;
  modifier?: "ctrl" | "meta" | "shift";
}

const NAVIGATION_SHORTCUTS: NavigationShortcut[] = [
  {
    key: "1",
    path: "/dashboard",
    description: "Go to Dashboard",
    modifier: "meta",
  },
  {
    key: "2",
    path: "/conversations",
    description: "Go to Conversations",
    modifier: "meta",
  },
  {
    key: "3",
    path: "/search",
    description: "Go to Search",
    modifier: "meta",
  },
  {
    key: "4",
    path: "/database-browser",
    description: "Go to Database Browser",
    modifier: "meta",
  },
  {
    key: "5",
    path: "/profile",
    description: "Go to Profile",
    modifier: "meta",
  },
  {
    key: ",",
    path: "/settings",
    description: "Go to Settings",
    modifier: "meta",
  },
  {
    key: "H",
    path: "/help",
    description: "Go to Help",
    modifier: "meta",
  },
];

const LANDING_OR_AUTH_PATHS = [
  "/",
  "/auth/",
  "/about",
  "/contact",
  "/pricing",
  "/terms",
  "/privacy",
];

function isLandingOrAuthPage(pathname: string): boolean {
  return LANDING_OR_AUTH_PATHS.some(
    (path) => pathname === path || pathname.startsWith(path),
  );
}

function findMatchingShortcut(
  event: KeyboardEvent,
  shortcuts: NavigationShortcut[],
): NavigationShortcut | undefined {
  return shortcuts.find((shortcut) => {
    const modifierPressed = shortcut.modifier
      ? isModifierPressed(event, shortcut.modifier)
      : true;

    const keyMatches = matchesKey(event, shortcut.key);

    const noConflictingModifiers =
      !event.altKey && (shortcut.modifier !== "shift" ? !event.shiftKey : true);

    return modifierPressed && keyMatches && noConflictingModifiers;
  });
}

/**
 * Global navigation keyboard shortcuts hook
 * Provides quick navigation to main pages using Cmd/Ctrl + number keys
 */
export function useGlobalNavigationShortcuts() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (isLandingOrAuthPage(location.pathname)) {
      return;
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (isInputElement(e.target)) {
        return;
      }

      const shortcut = findMatchingShortcut(e, NAVIGATION_SHORTCUTS);
      if (!shortcut) {
        return;
      }

      // Don't navigate if already on that page
      if (location.pathname === shortcut.path) {
        return;
      }

      e.preventDefault();
      navigate(shortcut.path);
    };

    window.addEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line consistent-return
    return (): void => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [navigate, location.pathname]);
}

export { NAVIGATION_SHORTCUTS };
