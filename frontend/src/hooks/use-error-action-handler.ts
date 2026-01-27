/**
 * Error Action Handler Hook
 *
 * Centralized handler for error action buttons (retry, new session, help, etc.)
 */

import { useNavigate } from "react-router-dom";
import React from "react";
import type { ErrorAction } from "#/components/shared/error/user-friendly-error";
import { logger } from "#/utils/logger";

type CustomHandlerMap = Record<string, () => void> | undefined;

type BuiltInHandlerContext = {
  navigate: ReturnType<typeof useNavigate>;
  customHandlers: CustomHandlerMap;
};

const NAVIGATION_ROUTES: Record<string, string> = {
  new_conversation: "/conversations",
  new_session: "/conversations",
  login: "/auth/login",
  upgrade: "/billing",
};

const EXTERNAL_LINK_DEFAULTS: Record<string, string> = {
  help: "https://docs.forge.ai",
  support: "mailto:support@forge.ai",
  status: "https://status.forge.ai",
};

function openInNewTab(url: string): void {
  window.open(url, "_blank");
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
  if (
    action.type === "help" ||
    action.type === "support" ||
    action.type === "status"
  ) {
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

function handleFallbackAction(action: ErrorAction): void {
  if (action.url) {
    openInNewTab(action.url);
    return;
  }
  logger.warn(`Unknown error action: ${action.type}`);
}

function handleBuiltInAction(
  action: ErrorAction,
  { navigate, customHandlers }: BuiltInHandlerContext,
  tracker: React.MutableRefObject<string | null>,
): boolean {
  if (handleUtilityAction(action, customHandlers)) {
    // eslint-disable-next-line no-param-reassign
    tracker.current = `utility:${action.type}`;
    return true;
  }

  if (handleNavigationAction(action.type, navigate)) {
    // eslint-disable-next-line no-param-reassign
    tracker.current = `navigate:${action.type}`;
    return true;
  }

  if (handleExternalLinkAction(action)) {
    // eslint-disable-next-line no-param-reassign
    tracker.current = `external:${action.type}`;
    return true;
  }

  if (handlePlaceholderAction(action.type)) {
    // eslint-disable-next-line no-param-reassign
    tracker.current = `placeholder:${action.type}`;
    return true;
  }

  return false;
}

export function useErrorActionHandler() {
  const navigate = useNavigate();
  const lastHandledRef = React.useRef<string | null>(null);

  const handleErrorAction = (
    action: ErrorAction,
    customHandlers?: CustomHandlerMap,
  ) => {
    if (invokeCustomHandler(action, customHandlers)) {
      lastHandledRef.current = `custom:${action.type}`;
      return;
    }

    const context: BuiltInHandlerContext = {
      navigate,
      customHandlers,
    };

    if (!handleBuiltInAction(action, context, lastHandledRef)) {
      handleFallbackAction(action);
      lastHandledRef.current = `fallback:${action.type}`;
    }
  };

  return { handleErrorAction, lastHandledAction: lastHandledRef };
}
