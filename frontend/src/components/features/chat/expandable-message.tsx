import { PayloadAction } from "@reduxjs/toolkit";
import { useCallback, useEffect, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import Markdown from "react-markdown";
import { Link } from "react-router-dom";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { useConfig } from "#/hooks/query/use-config";
import { I18nKey } from "#/i18n/declaration";
import ArrowDown from "#/icons/angle-down-solid.svg?react";
import ArrowUp from "#/icons/angle-up-solid.svg?react";
import CheckCircle from "#/icons/check-circle-solid.svg?react";
import XCircle from "#/icons/x-circle-solid.svg?react";
import { ForgeAction } from "#/types/core/actions";
import { ForgeObservation } from "#/types/core/observations";
import { cn } from "#/utils/utils";
import { code } from "../markdown/code";
import { ol, ul } from "../markdown/list";
import { paragraph } from "../markdown/paragraph";
import { MonoComponent } from "./mono-component";
import { PathComponent } from "./path-component";

const trimText = (text: string, maxLength: number): string => {
  if (!text) {
    return "";
  }
  return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
};

interface ExpandableMessageProps {
  id?: string;
  message: string;
  type: string;
  success?: boolean;
  observation?: PayloadAction<ForgeObservation>;
  action?: PayloadAction<ForgeAction>;
}

export function ExpandableMessage({
  id,
  message,
  type,
  success,
  observation,
  action,
}: ExpandableMessageProps) {
  const { data: config } = useConfig();
  const { t, i18n } = useTranslation();
  const {
    showDetails,
    toggleDetails,
    translationId,
    translationParams,
    details,
  } = useExpandableMessageTranslation({
    id,
    message,
    observation,
    action,
    i18n,
  });

  const statusIconClasses = "h-4 w-4 ml-2 inline";
  const billingNotice = buildBillingNotice({ config, id, t });
  if (billingNotice) {
    return billingNotice;
  }

  const heading = buildMessageHeading({
    translationId,
    translationParams,
    message,
  });
  const toggleIcon = getToggleIcon({ showDetails, type });
  const statusIcon = getStatusIcon({ type, success, classes: statusIconClasses });

  return (
    <div
      className={cn(
        "flex gap-2 items-center justify-start border-l-2 pl-2 my-2 py-2",
        type === "error" ? "border-danger" : "border-neutral-300",
      )}
    >
      <div className="text-sm w-full">
        <div className="flex flex-row justify-between items-center w-full">
          <span
            className={cn(
              "font-bold",
              type === "error" ? "text-danger" : "text-foreground",
            )}
          >
            {heading}
            <button
              type="button"
              onClick={toggleDetails}
              className="cursor-pointer text-left"
            >
              {toggleIcon}
            </button>
          </span>
          {statusIcon}
        </div>
        {showDetails && (
          <div className="text-sm">
            <Markdown
              components={{
                code,
                ul,
                ol,
                p: paragraph,
              }}
              remarkPlugins={[remarkGfm, remarkBreaks]}
            >
              {details}
            </Markdown>
          </div>
        )}
      </div>
    </div>
  );
}

function buildBillingNotice({
  config,
  id,
  t,
}: {
  config: ReturnType<typeof useConfig>["data"];
  id?: string;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (
    !config?.FEATURE_FLAGS?.ENABLE_BILLING ||
    config?.APP_MODE !== "saas" ||
    id !== I18nKey.STATUS$ERROR_LLM_OUT_OF_CREDITS
  ) {
    return null;
  }

  return (
    <div
      data-testid="out-of-credits"
      className="flex gap-2 items-center justify-start border-l-2 pl-2 my-2 py-2 border-danger"
    >
      <div className="text-sm w-full">
        <div className="font-bold text-danger">
          {t(I18nKey.STATUS$ERROR_LLM_OUT_OF_CREDITS)}
        </div>
        <Link
          className="mt-2 mb-2 w-full h-10 rounded-sm flex items-center justify-center gap-2 bg-primary text-[#0D0F11]"
          to="/settings/billing"
        >
          {t(I18nKey.BILLING$CLICK_TO_TOP_UP)}
        </Link>
      </div>
    </div>
  );
}

function buildMessageHeading({
  translationId,
  translationParams,
  message,
}: {
  translationId?: string;
  translationParams: Record<string, unknown>;
  message: string;
}) {
  if (!translationId) {
    return message;
  }

  return (
    <Trans
      i18nKey={translationId}
      values={translationParams}
      components={{
        bold: <strong />,
        path: <PathComponent />,
        cmd: <MonoComponent />,
      }}
    />
  );
}

function getToggleIcon({
  showDetails,
  type,
}: {
  showDetails: boolean;
  type: string;
}) {
  const iconClasses = cn(
    "h-4 w-4 ml-2 inline",
    type === "error" ? "fill-error-500" : "fill-foreground",
  );

  return showDetails ? <ArrowUp className={iconClasses} /> : <ArrowDown className={iconClasses} />;
}

function getStatusIcon({
  type,
  success,
  classes,
}: {
  type: string;
  success?: boolean;
  classes: string;
}) {
  if (type !== "action" || success === undefined) {
    return null;
  }

  return (
    <span className="flex-shrink-0">
      {success ? (
        <CheckCircle data-testid="status-icon" className={cn(classes, "fill-success")} />
      ) : (
        <XCircle data-testid="status-icon" className={cn(classes, "fill-danger")} />
      )}
    </span>
  );
}

function useExpandableMessageTranslation({
  id,
  message,
  observation,
  action,
  i18n,
}: {
  id?: string;
  message: string;
  observation?: PayloadAction<ForgeObservation>;
  action?: PayloadAction<ForgeAction>;
  i18n: ReturnType<typeof useTranslation>["i18n"];
}) {
  const [state, setState] = useState<TranslationState>({
    showDetails: true,
    translationParams: { observation, action },
    details: message,
  });

  useEffect(() => {
    if (!id || !i18n.exists(id)) {
      setState((previous) => ({
        ...previous,
        showDetails: true,
        translationId: undefined,
        translationParams: { observation, action },
        details: message,
      }));
      return;
    }

    const processedAction = trimRunCommand(action);
    const processedObservation = trimObservationCommand(observation);

    setState({
      showDetails: false,
      translationId: id,
      translationParams: {
        observation: processedObservation,
        action: processedAction,
      },
      details: message,
    });
  }, [id, message, observation, action, i18n, i18n.language]);

  const toggleDetails = useCallback(() => {
    setState((previous) => ({
      ...previous,
      showDetails: !previous.showDetails,
    }));
  }, []);

  return {
    showDetails: state.showDetails ?? true,
    toggleDetails,
    translationId: state.translationId,
    translationParams: state.translationParams ?? { observation, action },
    details: state.details ?? message,
  };
}

type TranslationState = {
  showDetails: boolean;
  translationId?: string;
  translationParams: Record<string, unknown>;
  details: string;
};

function trimRunCommand(
  payload?: PayloadAction<ForgeAction>,
): PayloadAction<ForgeAction> | undefined {
  if (!payload || payload.payload.action !== "run") {
    return payload;
  }

  const command = trimText(payload.payload.args.command, 80);
  return {
    ...payload,
    payload: {
      ...payload.payload,
      args: { ...payload.payload.args, command },
    },
  };
}

function trimObservationCommand(
  payload?: PayloadAction<ForgeObservation>,
): PayloadAction<ForgeObservation> | undefined {
  if (!payload || payload.payload.observation !== "run") {
    return payload;
  }

  const command = trimText(payload.payload.extras.command, 80);
  return {
    ...payload,
    payload: {
      ...payload.payload,
      extras: { ...payload.payload.extras, command },
    },
  };
}
