import { Trans } from "react-i18next";
import { OpenHandsAction } from "#/types/core/actions";
import { isOpenHandsAction, isOpenHandsObservation, hasExtras } from "#/types/core/guards";
import { OpenHandsObservation } from "#/types/core/observations";
import { MonoComponent } from "../mono-component";
import { PathComponent } from "../path-component";
import { getActionContent } from "./get-action-content";
import { getObservationContent } from "./get-observation-content";
import i18n from "#/i18n";

const hasPathProperty = (
  obj: Record<string, unknown>,
): obj is { path: string } => typeof obj.path === "string";

const hasCommandProperty = (
  obj: Record<string, unknown>,
): obj is { command: string } => typeof obj.command === "string";

const trimText = (text: string, maxLength: number): string => {
  if (!text) {
    return "";
  }
  return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
};

export const getEventContent = (
  event: OpenHandsAction | OpenHandsObservation,
) => {
  let title: React.ReactNode = "";
  let details: string = "";

  const normalizeKeyPart = (s: unknown) =>
    typeof s === "string" && s.toLowerCase() !== "null" ? String(s) : null;

  if (isOpenHandsAction(event)) {
    const actionPart = normalizeKeyPart(event.action) ?? "";
    const actionKey = `ACTION_MESSAGE$${actionPart.toUpperCase()}`;

    // If translation key exists, use Trans component
    if (actionPart && i18n.exists(actionKey)) {
      title = (
        <Trans
          i18nKey={actionKey}
          values={{
            path: hasPathProperty(event.args) && event.args.path,
            command:
              hasCommandProperty(event.args) &&
              trimText(event.args.command, 80),
            mcp_tool_name: event.action === "call_tool_mcp" && event.args.name,
          }}
          components={{
            path: <PathComponent />,
            cmd: <MonoComponent />,
          }}
        />
      );
    } else {
      // For generic actions, just use the uppercase type (unless it's the
      // string 'null', in which case fall back to unknown translation)
      title =
        event.action &&
        typeof event.action === "string" &&
        event.action.toLowerCase() !== "null"
          ? event.action.toUpperCase()
          : "";
    }
    details = getActionContent(event);
  }

  if (isOpenHandsObservation(event)) {
    const obsPart = normalizeKeyPart(event.observation) ?? "";
    const observationKey = `OBSERVATION_MESSAGE$${obsPart.toUpperCase()}`;

    // If translation key exists, use Trans component
    if (obsPart && i18n.exists(observationKey)) {
      title = (
        <Trans
          i18nKey={observationKey}
          values={{
            path: hasExtras(event) && hasPathProperty(event.extras) ? event.extras.path : undefined,
            command:
              hasExtras(event) && hasCommandProperty(event.extras) &&
              trimText(event.extras.command, 80),
            mcp_tool_name: event.observation === "mcp" && hasExtras(event) ? event.extras.name : undefined,
          }}
          components={{
            path: <PathComponent />,
            cmd: <MonoComponent />,
          }}
        />
      );
    } else {
      // For generic observations, just use the uppercase type (unless it's
      // the string 'null')
      title =
        event.observation &&
        typeof event.observation === "string" &&
        event.observation.toLowerCase() !== "null"
          ? event.observation.toUpperCase()
          : "";
    }
    details = getObservationContent(event);
  }

  return {
    title: title ?? i18n.t("EVENT$UNKNOWN_EVENT"),
    details: details ?? i18n.t("EVENT$UNKNOWN_EVENT"),
  };
};
