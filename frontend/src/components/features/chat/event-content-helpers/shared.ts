import { ForgeAction } from "#/types/core/actions";
import { ForgeObservation } from "#/types/core/observations";

export const MAX_CONTENT_LENGTH = 1000;

export const getDefaultEventContent = (
  event: ForgeAction | ForgeObservation,
): string => `\`\`\`json\n${JSON.stringify(event, null, 2)}\n\`\`\``;
