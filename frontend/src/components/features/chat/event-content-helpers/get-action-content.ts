import { ForgeAction } from "#/types/core/actions";
import { getDefaultEventContent } from "./shared";
import {
  getWriteActionContent,
  getRunActionContent,
  getBrowseActionContent,
  getBrowseInteractiveActionContent,
  getMcpActionContent,
  getThinkActionContent,
  getFinishActionContent,
  getNoContentActionContent,
} from "./get-action-content/action-handlers";

type ActionContentHandler = (event: ForgeAction) => string;

const ACTION_HANDLERS: Record<string, ActionContentHandler> = {
  read: getNoContentActionContent as ActionContentHandler,
  edit: getNoContentActionContent as ActionContentHandler,
  write: getWriteActionContent as ActionContentHandler,
  run: getRunActionContent as ActionContentHandler,
  browse: getBrowseActionContent as ActionContentHandler,
  browse_interactive:
    getBrowseInteractiveActionContent as ActionContentHandler,
  call_tool_mcp: getMcpActionContent as ActionContentHandler,
  think: getThinkActionContent as ActionContentHandler,
  finish: getFinishActionContent as ActionContentHandler,
};

export const getActionContent = (event: ForgeAction): string => {
  const handler = ACTION_HANDLERS[event.action];
  if (handler) {
    return handler(event);
  }
  return getDefaultEventContent(event);
};
