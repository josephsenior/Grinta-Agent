import React from "react";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { showErrorToast } from "#/utils/error-handler";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";
import { useAgentState } from "#/hooks/use-agent-state";
import { useWsStatus } from "#/context/ws-client-provider";
import { useBrowserNotification } from "#/hooks/use-browser-notification";
import { browserTab } from "#/utils/browser-tab";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { getIndicatorColor, getStatusCode } from "#/utils/status";

const notificationStates = [
  AgentState.AWAITING_USER_INPUT,
  AgentState.FINISHED,
  AgentState.AWAITING_USER_CONFIRMATION,
];

export function AgentStatusBar() {
  const { t, i18n } = useTranslation();
  const curAgentState = useAgentState();
  const { curStatusMessage } = useSelector((state: RootState) => state.status);
  const { webSocketStatus } = useWsStatus();
  const { data: conversation } = useActiveConversation();
  const indicatorColor = getIndicatorColor(
    webSocketStatus,
    conversation?.status || null,
    conversation?.runtime_status || null,
    curAgentState,
  );
  const statusCode = getStatusCode(
    curStatusMessage,
    webSocketStatus,
    conversation?.status || null,
    conversation?.runtime_status || null,
    curAgentState,
  );
  const { notify } = useBrowserNotification();

  // Show error toast if required
  React.useEffect(() => {
    if (curStatusMessage?.type !== "error") {
      return;
    }
    let message = curStatusMessage.message || "";
    if (curStatusMessage?.id) {
      const id = curStatusMessage.id.trim();
      if (id === "STATUS$READY") {
        message = "awaiting_user_input";
      }
      if (i18n.exists(id)) {
        message = t(curStatusMessage.id.trim(), { defaultValue: `${message}` });
      }
    }
    showErrorToast({
      message,
      source: "agent-status",
      metadata: { ...curStatusMessage },
    });
  }, [curStatusMessage]);

  // Handle notify
  React.useEffect(() => {
    if (notificationStates.includes(curAgentState)) {
      const message = t(statusCode);
      notify(message, {
        body: t(`Agent state changed to ${curAgentState}`),
        playSound: true,
      });

      // Update browser tab if window exists and is not focused
      if (typeof document !== "undefined" && !document.hasFocus()) {
        browserTab.startNotification(message);
      }
    }
  }, [curAgentState, statusCode]);

  // Handle window focus/blur
  React.useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const handleFocus = () => {
      browserTab.stopNotification();
    };

    window.addEventListener("focus", handleFocus);
    return () => {
      window.removeEventListener("focus", handleFocus);
      browserTab.stopNotification();
    };
  }, []);

  return (
    <div className="flex items-center justify-center">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-gray-800/50 rounded-full border border-gray-200 dark:border-gray-700">
        <div
          className={`w-2 h-2 rounded-full ${indicatorColor} ${
            curAgentState === AgentState.RUNNING ||
            curAgentState === AgentState.LOADING
              ? "animate-pulse"
              : ""
          }`}
        />
        <span className="text-xs font-medium text-gray-600 dark:text-gray-300 tracking-wide">
          {t(statusCode)}
        </span>
      </div>
    </div>
  );
}
