/**
 * Error Action Handler Hook
 * 
 * Centralized handler for error action buttons (retry, new session, help, etc.)
 */

import { useNavigate } from "react-router-dom";
import type { ErrorAction } from "#/components/shared/error/user-friendly-error";

export function useErrorActionHandler() {
  const navigate = useNavigate();

  const handleErrorAction = (action: ErrorAction, customHandlers?: Record<string, () => void>) => {
    // Check for custom handler first
    if (customHandlers && action.type in customHandlers) {
      customHandlers[action.type]();
      return;
    }

    // Built-in handlers
    switch (action.type) {
      case "refresh":
        window.location.reload();
        break;

      case "retry":
        // Retry is usually handled by the component passing a custom handler
        if (customHandlers?.retry) {
          customHandlers.retry();
        }
        break;

      case "new_conversation":
      case "new_session":
        navigate("/");
        break;

      case "login":
        navigate("/login");
        break;

      case "upgrade":
        navigate("/billing");
        break;

      case "pricing":
        navigate("/pricing");
        break;

      case "help":
        if (action.url) {
          window.open(action.url, "_blank");
        } else {
          window.open("https://docs.forge.ai", "_blank");
        }
        break;

      case "support":
        if (action.url) {
          window.open(action.url, "_blank");
        } else {
          window.open("mailto:support@forge.ai", "_blank");
        }
        break;

      case "report":
        if (action.url) {
          window.open(action.url, "_blank");
        }
        break;

      case "status":
        window.open("https://status.forge.ai", "_blank");
        break;

      case "export":
        // TODO: Implement export functionality
        break;

      case "summarize":
        // TODO: Implement summarization functionality
        break;

      case "search_files":
        // TODO: Implement file search functionality
        break;

      case "create_file":
        // TODO: Implement file creation functionality
        break;

      default:
        // Handle unknown actions gracefully
        console.warn(`Unknown error action: ${action.type}`);
        if (action.url) {
          window.open(action.url, "_blank");
        }
    }
  };

  return { handleErrorAction };
}

