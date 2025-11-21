import { Spinner } from "@heroui/react";
import { useTranslation } from "react-i18next";
import safeToast from "#/utils/safe-hot-toast";
import { TOAST_OPTIONS } from "#/utils/custom-toast-handlers/toast-config";
import CloseIcon from "#/icons/close.svg?react";
import { SuccessIndicator } from "../success-indicator";

interface ConversationCreatedToastProps {
  conversationId: string;
  onClose: () => void;
}

interface ConversationStartingToastProps {
  conversationId: string;
  onClose: () => void;
}

function ConversationCreatedToast({
  conversationId,
  onClose,
}: ConversationCreatedToastProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-start gap-2">
      <Spinner size="sm" />
      <div>
        {t("MICROAGENT$ADDING_CONTEXT")}
        <br />
        <a
          href={`/conversations/${conversationId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="underline"
        >
          {t("MICROAGENT$VIEW_CONVERSATION")}
        </a>
      </div>
      <button type="button" onClick={onClose}>
        <CloseIcon />
      </button>
    </div>
  );
}

function ConversationStartingToast({
  conversationId,
  onClose,
}: ConversationStartingToastProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-start gap-2">
      <Spinner size="sm" />
      <div>
        {t("MICROAGENT$CONVERSATION_STARTING")}
        <br />
        <a
          href={`/conversations/${conversationId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="underline"
        >
          {t("MICROAGENT$VIEW_CONVERSATION")}
        </a>
      </div>
      <button type="button" onClick={onClose}>
        <CloseIcon />
      </button>
    </div>
  );
}

interface ConversationFinishedToastProps {
  conversationId: string;
  onClose: () => void;
}

function ConversationFinishedToast({
  conversationId,
  onClose,
}: ConversationFinishedToastProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-start gap-2">
      <SuccessIndicator status="success" />
      <div>
        {t("MICROAGENT$SUCCESS_PR_READY")}
        <br />
        <a
          href={`/conversations/${conversationId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="underline"
        >
          {t("MICROAGENT$VIEW_CONVERSATION")}
        </a>
      </div>
      <button type="button" onClick={onClose}>
        <CloseIcon />
      </button>
    </div>
  );
}

interface ConversationErroredToastProps {
  errorMessage: string;
  onClose: () => void;
}

function ConversationErroredToast({
  errorMessage,
  onClose,
}: ConversationErroredToastProps) {
  const { t } = useTranslation();

  // Check if the error message is a translation key
  const displayMessage =
    errorMessage === "MICROAGENT$UNKNOWN_ERROR"
      ? t(errorMessage)
      : errorMessage;

  return (
    <div className="flex items-start gap-2">
      <SuccessIndicator status="error" />
      <div>{displayMessage}</div>
      <button type="button" onClick={onClose}>
        <CloseIcon />
      </button>
    </div>
  );
}

export const renderConversationCreatedToast = (conversationId: string) =>
  safeToast.show(
    (toastInstance: { id: string }) => (
      <ConversationCreatedToast
        conversationId={conversationId}
        onClose={() => safeToast.dismiss(toastInstance.id)}
      />
    ),
    {
      ...TOAST_OPTIONS,
      id: `status-${conversationId}`,
      duration: 5000,
    },
  );

export const renderConversationFinishedToast = (conversationId: string) =>
  safeToast.show(
    (toastInstance: { id: string }) => (
      <ConversationFinishedToast
        conversationId={conversationId}
        onClose={() => safeToast.dismiss(toastInstance.id)}
      />
    ),
    {
      ...TOAST_OPTIONS,
      id: `status-${conversationId}`,
      duration: 5000,
    },
  );

export const renderConversationErroredToast = (
  conversationId: string,
  errorMessage: string,
) =>
  safeToast.show(
    (toastInstance: { id: string }) => (
      <ConversationErroredToast
        errorMessage={errorMessage}
        onClose={() => safeToast.dismiss(toastInstance.id)}
      />
    ),
    {
      ...TOAST_OPTIONS,
      id: `status-${conversationId}`,
      duration: 5000,
    },
  );

export const renderConversationStartingToast = (conversationId: string) =>
  safeToast.show(
    (toastInstance: { id: string }) => (
      <ConversationStartingToast
        conversationId={conversationId}
        onClose={() => safeToast.dismiss(toastInstance.id)}
      />
    ),
    {
      ...TOAST_OPTIONS,
      id: `starting-${conversationId}`,
      duration: 10000, // Show for 10 seconds or until dismissed
    },
  );
