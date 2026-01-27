import { PayloadAction } from "@reduxjs/toolkit";
import React, { useCallback, useEffect, useState } from "react";
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

const trimText = (text: string, maxLength: number): string => {
  if (!text) {
    return "";
  }
  return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
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

type TranslationState = {
  showDetails: boolean;
  translationId?: string;
  translationParams: Record<string, unknown>;
  details: string;
};

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

function buildBillingNotice({
  config,
  id,
}: {
  config: ReturnType<typeof useConfig>["data"];
  id?: string;
}) {
  if (!config?.APP_MODE || config.APP_MODE !== "saas") {
    return null;
  }

  if (
    id !== "OBSERVATION$BILLING_NOTICE" &&
    id !== "STATUS$ERROR_LLM_OUT_OF_CREDITS"
  ) {
    return null;
  }

  return (
    <div
      data-testid="out-of-credits"
      className="my-2 p-3 bg-warning-500/10 border border-warning-500/20 rounded-lg"
    >
      <p className="text-sm text-warning-600 dark:text-warning-400">
        <Trans
          i18nKey="OBSERVATION$BILLING_NOTICE"
          components={{
            link: <Link to="/settings" className="underline" />,
          }}
        />
      </p>
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
  if (translationId) {
    // Use React.createElement to avoid complex union type inference
    return React.createElement(Trans, {
      i18nKey: translationId as I18nKey,
      values: translationParams as Record<string, string>,
    });
  }
  return message;
}

function getToggleIcon({
  showDetails,
  type,
}: {
  showDetails: boolean;
  type: string;
}) {
  if (type === "error") {
    return showDetails ? (
      <ArrowUp className="h-4 w-4 inline" />
    ) : (
      <ArrowDown className="h-4 w-4 inline" />
    );
  }
  return showDetails ? (
    <ArrowUp className="h-4 w-4 inline" />
  ) : (
    <ArrowDown className="h-4 w-4 inline" />
  );
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
  if (type === "error") {
    return <XCircle className={cn(classes, "fill-danger")} />;
  }
  if (success) {
    return <CheckCircle className={cn(classes, "fill-success")} />;
  }
  if (success === false) {
    return <XCircle className={cn(classes, "fill-danger")} />;
  }
  return null;
}

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
  const { i18n } = useTranslation();
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
  const billingNotice = buildBillingNotice({ config, id });
  if (billingNotice) {
    return billingNotice;
  }

  const heading = buildMessageHeading({
    translationId,
    translationParams,
    message,
  });
  const toggleIcon = getToggleIcon({ showDetails, type });
  const statusIcon = getStatusIcon({
    type,
    success,
    classes: statusIconClasses,
  });

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
