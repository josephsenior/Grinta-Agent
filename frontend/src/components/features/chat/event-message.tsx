import React, { useMemo, useCallback } from "react";
import { useSelector } from "react-redux";
import { ConfirmationButtons } from "#/components/shared/buttons/confirmation-buttons";
import { ForgeAction } from "#/types/core/actions";
import {
  isUserMessage,
  isErrorObservation,
  isAssistantMessage,
  isForgeAction,
  isForgeObservation,
  isFinishAction,
  isRejectObservation,
  isMcpObservation,
  isTaskTrackingObservation,
  isFileWriteAction,
  isFileEditAction,
  isStreamingChunkAction,
  hasArgs,
  hasExtras,
} from "#/types/core/guards";
import { ForgeObservation } from "#/types/core/observations";
import { ImageCarousel } from "../images/image-carousel";
import { ChatMessage } from "./chat-message";
import { ErrorMessage } from "./error-message";
import { MCPObservationContent } from "./mcp-observation-content";
import { TaskTrackingObservationContent } from "./task-tracking-observation-content";
import { getObservationResult } from "./event-content-helpers/get-observation-result";
import { getEventContent } from "./event-content-helpers/get-event-content";
import { GenericEventMessage } from "./generic-event-message";
import { MicroagentStatus } from "#/types/microagent-status";
import { MicroagentStatusIndicator } from "./microagent/microagent-status-indicator";
import { FileList } from "../files/file-list";
import { parseMessageFromEvent } from "./event-content-helpers/parse-message-from-event";
import { LikertScale } from "../feedback/likert-scale";
import { useWsClient } from "#/context/ws-client-provider";
import { StreamingTerminal } from "../terminal/streaming-terminal";
import { StreamingThought } from "./streaming-thought";
import { CodeArtifact } from "./code-artifact";
import { StreamingCodeArtifact } from "./streaming-code-artifact";

import { useConfig } from "#/hooks/query/use-config";
import { useFeedbackExists } from "#/hooks/query/use-feedback-exists";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";

// Detect important commands that should be shown even when technical details are hidden
const isImportantCommand = (cmd?: string | null): boolean => {
  if (!cmd) return false;
  const command = String(cmd).toLowerCase();
  const importantPatterns = [
    /npm\s+(install|i|run|build|start|test)/,
    /yarn\s+(install|add|build|start|test)/,
    /pnpm\s+(install|add|build|start|test)/,
    /pip\s+install/,
    /docker\s+(build|run|compose)/,
    /git\s+(clone|pull|push|commit|checkout|branch)/,
    /pytest/,
    /cargo\s+(build|run|test)/,
    /make\s+(build|install|test)/,
    /cmake/,
    /deploy/,
    /build/,
  ];
  return importantPatterns.some((pattern) => pattern.test(command));
};

// small heuristic reused from CommandConsole to detect shell-like lines
export const looksLikeShell = (s?: string | null): boolean => {
  if (!s) {
    return false;
  }
  const text = String(s);
  const shellTokens = [
    "rm -",
    "&&",
    "||",
    "npm ",
    "yarn ",
    "docker ",
    "kubectl ",
    "/workspace/",
    "cd ",
    "git ",
    "ls ",
    "pwd",
    "echo ",
  ];
  if (text.startsWith("Ran ") || text.startsWith("ran ")) {
    return true;
  }
  for (const tk of shellTokens)
    if (text.includes(tk)) {
      return true;
    }
  if (/\/[\w\-./~]/.test(text)) {
    return true;
  }
  return false;
};

const hasThoughtProperty = (
  obj: Record<string, unknown>,
): obj is { thought: string } => "thought" in obj && !!obj.thought;

// Detect language from file extension
const getLanguageFromPath = (filePath: string): string => {
  const ext = filePath.split(".").pop()?.toLowerCase();
  const languageMap: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    java: "java",
    cpp: "cpp",
    c: "c",
    h: "c",
    hpp: "cpp",
    cs: "csharp",
    go: "go",
    rs: "rust",
    rb: "ruby",
    php: "php",
    swift: "swift",
    kt: "kotlin",
    scala: "scala",
    sql: "sql",
    sh: "shell",
    bash: "shell",
    yaml: "yaml",
    yml: "yaml",
    json: "json",
    xml: "xml",
    html: "html",
    css: "css",
    scss: "scss",
    less: "less",
    md: "markdown",
    dockerfile: "dockerfile",
  };
  return languageMap[ext || ""] || "plaintext";
};

type HiddenRenderPredicate = (context: {
  event: ForgeAction | ForgeObservation;
  extras: Record<string, unknown>;
  args: Record<string, unknown>;
}) => boolean;

const HIDDEN_RENDER_PREDICATES: HiddenRenderPredicate[] = [
  ({ event }) => isUserMessage(event) || isAssistantMessage(event),
  ({ event }) => isStreamingChunkAction(event) || isErrorObservation(event),
  ({ event }) => isFileWriteAction(event) || isFileEditAction(event),
  ({ event, extras }) =>
    isForgeObservation(event) &&
    event.observation === "run" &&
    isImportantCommand(
      typeof extras.command === "string" ? extras.command : undefined,
    ),
  ({ event, args }) =>
    isForgeAction(event) &&
    hasThoughtProperty(args as Record<string, unknown>) &&
    event.action !== "think",
  ({ event }) =>
    isFinishAction(event) ||
    isRejectObservation(event) ||
    isMcpObservation(event) ||
    isTaskTrackingObservation(event),
];

const shouldRenderWhenTechnicalDetailsHidden = (
  event: ForgeAction | ForgeObservation,
  extras: Record<string, unknown>,
  args: Record<string, unknown>,
): boolean =>
  HIDDEN_RENDER_PREDICATES.some((predicate) =>
    predicate({ event, extras, args }),
  );

type RenderDecisionType =
  | "error"
  | "paired-thought"
  | "paired-indicator"
  | "file-write"
  | "file-edit"
  | "streaming-chunk"
  | "finish"
  | "chat-message"
  | "reject"
  | "mcp"
  | "task-tracking"
  | "run"
  | "generic";

type RenderDecision = { type: RenderDecisionType };

const decisionResolvers: Array<
  (context: {
    event: ForgeAction | ForgeObservation;
    hasObservationPair: boolean;
    args: Record<string, unknown>;
  }) => RenderDecision | null
> = [
  ({ event }) => (isErrorObservation(event) ? { type: "error" } : null),
  ({ event, hasObservationPair, args }) =>
    resolvePairedDecision(event, hasObservationPair, args),
  ({ event }) => (isFileWriteAction(event) ? { type: "file-write" } : null),
  ({ event }) => (isFileEditAction(event) ? { type: "file-edit" } : null),
  ({ event }) => (isStreamingChunkAction(event) ? { type: "streaming-chunk" } : null),
  ({ event }) => (isFinishAction(event) ? { type: "finish" } : null),
  ({ event }) =>
    isUserMessage(event) || isAssistantMessage(event)
      ? { type: "chat-message" }
      : null,
  ({ event }) => (isRejectObservation(event) ? { type: "reject" } : null),
  ({ event }) => resolveObservationSpecificDecision(event),
];

const determineRenderDecision = ({
  event,
  hasObservationPair,
  args,
}: {
  event: ForgeAction | ForgeObservation;
  hasObservationPair: boolean;
  args: Record<string, unknown>;
}): RenderDecision => {
  for (const resolver of decisionResolvers) {
    const decision = resolver({ event, hasObservationPair, args });
    if (decision) {
      return decision;
    }
  }

  return { type: "generic" };
};

function resolvePairedDecision(
  event: ForgeAction | ForgeObservation,
  hasObservationPair: boolean,
  args: Record<string, unknown>,
): RenderDecision | null {
  if (!hasObservationPair || !isForgeAction(event)) {
    return null;
  }

  if (hasThoughtProperty(args) && event.action !== "think") {
    return { type: "paired-thought" };
  }

  return { type: "paired-indicator" };
}

function resolveObservationSpecificDecision(
  event: ForgeAction | ForgeObservation,
): RenderDecision | null {
  if (!isForgeObservation(event)) {
    return null;
  }

  const observation = event as ForgeObservation;

  if (isMcpObservation(observation)) {
    return { type: "mcp" };
  }

  if (isTaskTrackingObservation(observation)) {
    return { type: "task-tracking" };
  }

  if (
    observation.observation === "run" &&
    typeof observation.content === "string" &&
    observation.content
  ) {
    return { type: "run" };
  }

  return null;
}

const extractEditCode = (args: Record<string, unknown>): string => {
  if (typeof args.content === "string") return args.content;
  if (typeof args.file_text === "string") return args.file_text;
  if (typeof args.new_str === "string") return args.new_str;
  return "";
};

const renderStreamingThoughtNode = (eventId: string, thought?: string) => {
  if (!thought) {
    return null;
  }
  return <StreamingThought eventId={eventId} thought={thought} />;
};

const renderMicroagentStatus = ({
  status,
  actions,
  conversationId,
  prUrl,
}: {
  status?: MicroagentStatus | null;
  actions?: EventMessageProps["actions"];
  conversationId?: string;
  prUrl?: string;
}) => {
  if (!status || !actions) {
    return null;
  }

  return (
    <MicroagentStatusIndicator
      status={status}
      conversationId={conversationId}
      prUrl={prUrl}
    />
  );
};

interface RenderContext {
  event: ForgeAction | ForgeObservation;
  extras: Record<string, unknown>;
  args: Record<string, unknown>;
  attachments: Record<string, unknown>;
  actions?: EventMessageProps["actions"];
  onAskAboutCode?: EventMessageProps["onAskAboutCode"];
  onRunCode?: EventMessageProps["onRunCode"];
  hideAvatar: boolean;
  compactMode: boolean;
  microagentIndicator: React.ReactNode;
  renderLikertScale: () => React.ReactNode;
  shouldShowConfirmationButtons: boolean;
  renderCodeArtifactBlock: (
    action: "create" | "edit",
    code: string,
    path: string,
    thought?: string,
  ) => React.ReactNode;
  hydratedEventIds: Set<string>;
  getEventHydratedFlag: (ev: ForgeAction | ForgeObservation) => boolean;
  isLastMessage: boolean;
  renderStreamingThought: (thought?: string) => React.ReactNode;
}

type DecisionHandler = (context: RenderContext) => React.ReactNode;

const renderErrorDecision: DecisionHandler = ({
  event,
  extras,
  microagentIndicator,
  renderLikertScale,
}) => (
  <div>
    <ErrorMessage
      errorId={
        typeof extras.error_id === "string" ? extras.error_id : undefined
      }
      defaultMessage={event.message}
    />
    {microagentIndicator}
    {renderLikertScale()}
  </div>
);

const renderPairedThoughtDecision: DecisionHandler = ({
  args,
  actions,
  onAskAboutCode,
  onRunCode,
  hideAvatar,
  compactMode,
  microagentIndicator,
}) => (
  <div>
    <ChatMessage
      type="agent"
      message={typeof args.thought === "string" ? args.thought : ""}
      actions={actions}
      onAskAboutCode={onAskAboutCode}
      onRunCode={onRunCode}
      hideAvatar={hideAvatar}
      compactMode={compactMode}
    />
    {microagentIndicator}
  </div>
);

const renderPairedIndicatorDecision: DecisionHandler = ({
  microagentIndicator,
}) => microagentIndicator ?? null;

const renderFileWriteDecision: DecisionHandler = ({
  args,
  renderCodeArtifactBlock,
}) => {
  const code = typeof args.content === "string" ? args.content : "";
  const path = typeof args.path === "string" ? args.path : "";
  const thought = typeof args.thought === "string" ? args.thought : undefined;
  return renderCodeArtifactBlock("create", code, path, thought);
};

const renderFileEditDecision: DecisionHandler = ({
  args,
  renderCodeArtifactBlock,
}) => {
  const code = extractEditCode(args);
  const path = typeof args.path === "string" ? args.path : "";
  const thought = typeof args.thought === "string" ? args.thought : undefined;
  return renderCodeArtifactBlock("edit", code, path, thought);
};

const renderStreamingChunkDecision: DecisionHandler = ({
  args,
  onAskAboutCode,
  onRunCode,
  hideAvatar,
  compactMode,
}) => (
  <ChatMessage
    type="agent"
    message={typeof args.accumulated === "string" ? args.accumulated : ""}
    animate
    onAskAboutCode={onAskAboutCode}
    onRunCode={onRunCode}
    hideAvatar={hideAvatar}
    compactMode={compactMode}
  />
);

const renderFinishDecision: DecisionHandler = ({
  event,
  actions,
  onAskAboutCode,
  onRunCode,
  hideAvatar,
  compactMode,
  microagentIndicator,
  renderLikertScale,
}) => (
  <>
    <ChatMessage
      type="agent"
      message={getEventContent(event).details}
      actions={actions}
      onAskAboutCode={onAskAboutCode}
      onRunCode={onRunCode}
      hideAvatar={hideAvatar}
      compactMode={compactMode}
    />
    {microagentIndicator}
    {renderLikertScale()}
  </>
);

const renderChatMessageDecision: DecisionHandler = (context) => {
  const { event, actions, onAskAboutCode, onRunCode, hideAvatar, compactMode } = context;
  if (!isUserMessage(event) && !isAssistantMessage(event)) {
    return null;
  }

  const message = parseMessageFromEvent(event);
  const animateDecision = shouldAnimateChatMessage(context);

  return (
    <>
      <ChatMessage
        type={event.source}
        message={message}
        actions={actions}
        animate={animateDecision}
        onAskAboutCode={onAskAboutCode}
        onRunCode={onRunCode}
        hideAvatar={hideAvatar}
        compactMode={compactMode}
      >
        {renderChatMessageChildren(context)}
      </ChatMessage>
      {context.microagentIndicator}
      {shouldRenderLikertAfterChat(context) && context.renderLikertScale()}
    </>
  );
};

const renderRejectDecision: DecisionHandler = ({
  event,
  onAskAboutCode,
  onRunCode,
  hideAvatar,
  compactMode,
}) => (
  <div>
    <ChatMessage
      type="agent"
      message={
        isForgeObservation(event) && typeof event.content === "string"
          ? event.content
          : ""
      }
      onAskAboutCode={onAskAboutCode}
      onRunCode={onRunCode}
      hideAvatar={hideAvatar}
      compactMode={compactMode}
    />
  </div>
);

const renderMcpDecision: DecisionHandler = ({
  event,
  shouldShowConfirmationButtons,
}) => {
  if (!canRenderMcpObservation(event)) {
    return null;
  }

  const eventContent = getEventContent(event);
  if (!hasRenderableMcpTitle(event, eventContent)) {
    return null;
  }

  return (
    <div>
      <GenericEventMessage
        title={eventContent.title}
        details={<MCPObservationContent event={event} />}
        success={getObservationResult(event)}
      />
      {shouldShowConfirmationButtons && <ConfirmationButtons />}
    </div>
  );
};

const renderTaskTrackingDecision: DecisionHandler = ({ event }) => (
  isTaskTrackingObservation(event) ? (
    <TaskTrackingObservationContent event={event} />
  ) : null
);

function canRenderMcpObservation(event: ForgeAction | ForgeObservation) {
  return isForgeObservation(event) && isMcpObservation(event);
}

function hasRenderableMcpTitle(
  event: ForgeObservation,
  eventContent: ReturnType<typeof getEventContent>,
) {
  if (event.observation == null) {
    return false;
  }

  const title = eventContent.title;
  if (typeof title !== "string") {
    return Boolean(title);
  }

  const trimmedTitle = title.trim();
  return trimmedTitle.length > 0 && trimmedTitle.toUpperCase() !== "NULL";
}

const renderRunDecision: DecisionHandler = ({
  event,
  extras,
  renderLikertScale,
  shouldShowConfirmationButtons,
}) => (
  isForgeObservation(event) ? (
    <div>
      <StreamingTerminal
        eventId={String(event.id)}
        content={
          String(
            typeof event.content === "string" ? event.content : "",
          )
        }
        exitCode={
          typeof extras.exit_code === "number" ? extras.exit_code : undefined
        }
        command={
          typeof extras.command === "string" ? extras.command : undefined
        }
      />
      {shouldShowConfirmationButtons && <ConfirmationButtons />}
      {renderLikertScale()}
    </div>
  ) : null
);

const renderGenericDecision: DecisionHandler = (context) => {
  const { event, attachments, renderStreamingThought, shouldShowConfirmationButtons } = context;
  const eventContent = getEventContent(event);

  if (!shouldRenderGenericContent(event, eventContent)) {
    return null;
  }

  return (
    <div>
      {renderStreamingThought(
        typeof attachments.thought === "string"
          ? attachments.thought
          : undefined,
      )}
      <GenericEventMessage
        title={eventContent.title}
        details={eventContent.details}
        success={
          isForgeObservation(event) ? getObservationResult(event) : undefined
        }
      />
      {shouldShowConfirmationButtons && <ConfirmationButtons />}
    </div>
  );
};

const decisionHandlers: Record<RenderDecisionType, DecisionHandler> = {
  error: renderErrorDecision,
  "paired-thought": renderPairedThoughtDecision,
  "paired-indicator": renderPairedIndicatorDecision,
  "file-write": renderFileWriteDecision,
  "file-edit": renderFileEditDecision,
  "streaming-chunk": renderStreamingChunkDecision,
  finish: renderFinishDecision,
  "chat-message": renderChatMessageDecision,
  reject: renderRejectDecision,
  mcp: renderMcpDecision,
  "task-tracking": renderTaskTrackingDecision,
  run: renderRunDecision,
  generic: renderGenericDecision,
};

function shouldAnimateChatMessage(context: RenderContext) {
  const { event, hydratedEventIds, getEventHydratedFlag, isLastMessage } = context;
  return (
    isAssistantMessage(event) &&
    isLastMessage &&
    !hydratedEventIds.has(String(event.id)) &&
    !getEventHydratedFlag(event)
  );
}

function renderChatMessageChildren(context: RenderContext) {
  const elements: React.ReactNode[] = [];
  const { attachments, shouldShowConfirmationButtons } = context;

  if (Array.isArray(attachments.image_urls) && attachments.image_urls.length > 0) {
    elements.push(
      <ImageCarousel
        key="images"
        size="small"
        images={attachments.image_urls as string[]}
      />,
    );
  }

  if (Array.isArray(attachments.file_urls) && attachments.file_urls.length > 0) {
    elements.push(<FileList key="files" files={attachments.file_urls as string[]} />);
  }

  if (shouldShowConfirmationButtons) {
    elements.push(<ConfirmationButtons key="confirm" />);
  }

  return elements.length > 0 ? elements : null;
}

function shouldRenderLikertAfterChat(context: RenderContext) {
  const { event } = context;
  return isAssistantMessage(event) && event.action === "message";
}

function shouldRenderGenericContent(
  event: ForgeAction | ForgeObservation,
  eventContent: ReturnType<typeof getEventContent>,
) {
  if (!isForgeObservation(event)) {
    return true;
  }

  if (event.observation === null || event.observation === undefined) {
    return false;
  }

  if (isTitleEmpty(eventContent.title) && isDetailsEmpty(eventContent.details)) {
    return false;
  }

  return true;
}

function isTitleEmpty(title: unknown): boolean {
  if (typeof title !== "string") {
    return false;
  }
  const trimmed = title.trim();
  return trimmed === "" || trimmed.toUpperCase() === "NULL";
}

function isDetailsEmpty(details: unknown): boolean {
  return typeof details === "string" && details.trim() === "";
}

interface EventMessageProps {
  event: ForgeAction | ForgeObservation;
  hasObservationPair: boolean;
  isAwaitingUserConfirmation: boolean;
  isLastMessage: boolean;
  showTechnicalDetails?: boolean;
  microagentStatus?: MicroagentStatus | null;
  microagentConversationId?: string;
  microagentPRUrl?: string;
  actions?: Array<{
    icon: React.ReactNode;
    onClick: () => void;
    tooltip?: string;
  }>;
  isInLast10Actions: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
  // New props for turn-based grouping
  hideAvatar?: boolean;
  compactMode?: boolean;
}

function EventMessageComponent(props: EventMessageProps) {
  const controller = useEventMessageController(props);

  if (!controller.shouldRender) {
    return null;
  }

  return decisionHandlers[controller.decision.type](controller.handlerContext);
}

export const EventMessage = React.memo(EventMessageComponent);

function useEventMessageController({
  event,
  hasObservationPair,
  isAwaitingUserConfirmation,
  isLastMessage,
  showTechnicalDetails = false,
  microagentStatus,
  microagentConversationId,
  microagentPRUrl,
  actions,
  isInLast10Actions,
  onAskAboutCode,
  onRunCode,
  hideAvatar = false,
  compactMode = false,
}: EventMessageProps) {
  const { curAgentState } = useSelector((state: RootState) => state.agent);
  const { data: config } = useConfig();
  const { hydratedEventIds } = useWsClient();
  const {
    data: feedbackData = { exists: false },
    isLoading: isCheckingFeedback,
  } = useFeedbackExists(event.id);

  const shouldShowConfirmationButtons = useMemo(
    () => isLastMessage && event.source === "agent" && isAwaitingUserConfirmation,
    [event.source, isAwaitingUserConfirmation, isLastMessage],
  );

  const extras = useMemo(
    () => (hasExtras(event) ? event.extras : ({} as Record<string, unknown>)),
    [event],
  );
  const args = useMemo(
    () => (hasArgs(event) ? event.args : ({} as Record<string, unknown>)),
    [event],
  );
  const attachments = args;

  const shouldRender = useMemo(() => {
    if (showTechnicalDetails) {
      return true;
    }
    return shouldRenderWhenTechnicalDetailsHidden(event, extras, args);
  }, [args, event, extras, showTechnicalDetails]);

  const microagentIndicator = useMemo(
    () =>
      renderMicroagentStatus({
        status: microagentStatus,
        actions,
        conversationId: microagentConversationId,
        prUrl: microagentPRUrl,
      }),
    [actions, microagentConversationId, microagentPRUrl, microagentStatus],
  );

  const renderLikertScale = useCallback(() => {
    if (config?.APP_MODE !== "saas" || isCheckingFeedback) {
      return null;
    }

    const shouldShow = isErrorObservation(event)
      ? isInLast10Actions
      : isLastMessage;

    if (!shouldShow) {
      return null;
    }

    return (
      <LikertScale
        eventId={event.id}
        initiallySubmitted={feedbackData.exists}
        initialRating={feedbackData.rating}
        initialReason={feedbackData.reason}
      />
    );
  }, [config?.APP_MODE, event, feedbackData, isCheckingFeedback, isInLast10Actions, isLastMessage]);

  const shouldStreamCodeArtifact =
    curAgentState === AgentState.RUNNING && isLastMessage;

  const renderStreamingThought = useCallback(
    (thought?: string) => renderStreamingThoughtNode(String(event.id), thought),
    [event.id],
  );

  const renderCodeArtifactBlock = useCallback(
    (
      action: "create" | "edit",
      code: string,
      path: string,
      thought?: string,
    ) => {
      const language = getLanguageFromPath(path);
      return (
        <div>
          {renderStreamingThought(thought)}
          {shouldStreamCodeArtifact ? (
            <StreamingCodeArtifact
              filePath={path}
              language={language}
              code={code}
              action={action}
              eventId={String(event.id)}
              isStreaming
              onCopy={() => {}}
            />
          ) : (
            <CodeArtifact
              filePath={path}
              language={language}
              code={code}
              action={action}
              onCopy={() => {}}
            />
          )}
          {microagentIndicator}
        </div>
      );
    },
    [event.id, microagentIndicator, renderStreamingThought, shouldStreamCodeArtifact],
  );

  const getEventHydratedFlag = useCallback((ev: ForgeAction | ForgeObservation) => {
    try {
      const v = ev as unknown as Record<string, unknown>;
      return Boolean(v.__hydrated);
    } catch (_e) {
      return false;
    }
  }, []);

  const decision = useMemo(
    () =>
      determineRenderDecision({
        event,
        hasObservationPair,
        args,
      }),
    [args, event, hasObservationPair],
  );

  const handlerContext: RenderContext = useMemo(
    () => ({
      event,
      extras,
      args,
      attachments,
      actions,
      onAskAboutCode,
      onRunCode,
      hideAvatar,
      compactMode,
      microagentIndicator,
      renderLikertScale,
      shouldShowConfirmationButtons,
      renderCodeArtifactBlock,
      hydratedEventIds,
      getEventHydratedFlag,
      isLastMessage,
      renderStreamingThought,
    }),
    [
      actions,
      args,
      attachments,
      compactMode,
      event,
      extras,
      getEventHydratedFlag,
      hideAvatar,
      hydratedEventIds,
      isLastMessage,
      microagentIndicator,
      onAskAboutCode,
      onRunCode,
      renderCodeArtifactBlock,
      renderLikertScale,
      renderStreamingThought,
      shouldShowConfirmationButtons,
    ],
  );

  return {
    shouldRender,
    decision,
    handlerContext,
  };
}
