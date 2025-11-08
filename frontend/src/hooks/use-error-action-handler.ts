/**
 * Error Action Handler Hook
 * 
 * Centralized handler for error action buttons (retry, new session, help, etc.)
 */

import { useNavigate } from "react-router-dom";
import type { ErrorAction } from "#/components/shared/error/user-friendly-error";

type CustomHandlerMap = Record<string, () => void> | undefined;

type BuiltInHandlerContext = {
  navigate: ReturnType<typeof useNavigate>;
  customHandlers: CustomHandlerMap;
};

export function useErrorActionHandler() {
  const navigate = useNavigate();

  const handleErrorAction = (
    action: ErrorAction,
    customHandlers?: CustomHandlerMap,
  ) => {
    if (invokeCustomHandler(action, customHandlers)) {
      return;
    }

    const context: BuiltInHandlerContext = {
      navigate,
      customHandlers,
    };

    if (!handleBuiltInAction(action, context)) {
      handleFallbackAction(action);
    }
  };

  return { handleErrorAction };
}

function invokeCustomHandler(
  action: ErrorAction,
  customHandlers?: CustomHandlerMap,
): boolean {
  if (customHandlers && action.type in customHandlers) {
    customHandlers[action.type]?.();
    return true;
  }
  return false;
}

const NAVIGATION_ROUTES: Record<string, string> = {
  new_conversation: "/",
  new_session: "/",
  login: "/login",
  upgrade: "/billing",
  pricing: "/pricing",
};

const EXTERNAL_LINK_DEFAULTS: Record<string, string> = {
  help: "https://docs.forge.ai",
  support: "mailto:support@forge.ai",
  status: "https://status.forge.ai",
};

function handleBuiltInAction(
  action: ErrorAction,
  { navigate, customHandlers }: BuiltInHandlerContext,
): boolean {
  if (handleUtilityAction(action, customHandlers)) {
    return true;
  }

  if (handleNavigationAction(action.type, navigate)) {
    return true;
  }

  if (handleExternalLinkAction(action)) {
    return true;
  }

  if (handlePlaceholderAction(action.type)) {
    return true;
  }

  return false;
}

function handleUtilityAction(
  action: ErrorAction,
  customHandlers: CustomHandlerMap,
): boolean {
  if (action.type === "refresh") {
    window.location.reload();
    return true;
  }

  if (action.type === "retry") {
    customHandlers?.retry?.();
    return true;
  }

  return false;
}

function handleNavigationAction(
  actionType: string,
  navigate: ReturnType<typeof useNavigate>,
): boolean {
  const destination = NAVIGATION_ROUTES[actionType];
  if (destination) {
    navigate(destination);
    return true;
  }
  return false;
}

function handleExternalLinkAction(action: ErrorAction): boolean {
  if (action.type === "help" || action.type === "support" || action.type === "status") {
    const defaultUrl = EXTERNAL_LINK_DEFAULTS[action.type];
    openInNewTab(action.url ?? defaultUrl);
    return true;
  }

  if (action.type === "report") {
    if (action.url) {
      openInNewTab(action.url);
    }
    return true;
  }

  return false;
}

function handlePlaceholderAction(actionType: string): boolean {
  const placeholderActions = new Set([
    "export",
    "summarize",
    "search_files",
    "create_file",
  ]);

  return placeholderActions.has(actionType);
}

function handleFallbackAction(action: ErrorAction) {
  if (action.url) {
    openInNewTab(action.url);
    return;
  }
  console.warn(`Unknown error action: ${action.type}`);
}

function openInNewTab(url: string) {
  window.open(url, "_blank");
}

