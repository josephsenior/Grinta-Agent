/* eslint-disable @typescript-eslint/no-use-before-define */
import React, { useMemo, useCallback } from "react";
import { DiffEditor } from "@monaco-editor/react";
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
  isFileWriteAction,
  isFileEditAction,
  isStreamingChunkAction,
  hasArgs,
  hasExtras,
  hasThoughtProperty,
} from "#/types/core/guards";
import { ForgeObservation } from "#/types/core/observations";
import { ImageCarousel } from "../images/image-carousel";
import { ChatMessage } from "./chat-message";
import { ErrorMessage } from "./error-message";
import { MCPObservationContent } from "./mcp-observation-content";
import { getObservationResult } from "./event-content-helpers/get-observation-result";
import { getEventContent } from "./event-content-helpers/get-event-content";
import { GenericEventMessage } from "./generic-event-message";
import { FileList } from "../files/file-list";
import { parseMessageFromEvent } from "./event-content-helpers/parse-message-from-event";
import { useWsClient } from "#/context/ws-client-provider";
import { StreamingTerminal } from "../terminal/streaming-terminal";
import { StreamingThought } from "./streaming-thought";
import { CodeArtifact } from "./code-artifact";
import { StreamingCodeArtifact } from "./streaming-code-artifact";

import { useConfig } from "#/hooks/query/use-config";
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

  return null;
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

  if (
    observation.observation === "run" &&
    typeof observation.content === "string" &&
    observation.content
  ) {
    return { type: "run" };
  }

  if (observation.observation === "edit") {
    return { type: "file-edit-observation" };
  }

  return null;
}

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

  const { title } = eventContent;
  if (typeof title !== "string") {
    return Boolean(title);
  }

  const trimmedTitle = title.trim();
  return trimmedTitle.length > 0 && trimmedTitle.toUpperCase() !== "NULL";
}

function shouldAnimateChatMessage(context: RenderContext) {
  const { event, hydratedEventIds, getEventHydratedFlag, isLastMessage } =
    context;
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

  if (
    Array.isArray(attachments.image_urls) &&
    attachments.image_urls.length > 0
  ) {
    elements.push(
      <ImageCarousel
        key="images"
        size="small"
        images={attachments.image_urls as string[]}
      />,
    );
  }

  if (
    Array.isArray(attachments.file_urls) &&
    attachments.file_urls.length > 0
  ) {
    elements.push(
      <FileList key="files" files={attachments.file_urls as string[]} />,
    );
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

// Helper functions defined before use
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

  if (
    isTitleEmpty(eventContent.title) &&
    isDetailsEmpty(eventContent.details)
  ) {
    return false;
  }

  return true;
}

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
    isMcpObservation(event),
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
  | "file-write"
  | "file-edit"
  | "file-edit-observation"
  | "streaming-chunk"
  | "finish"
  | "chat-message"
  | "reject"
  | "mcp"
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
  ({ event }) =>
    isStreamingChunkAction(event) ? { type: "streaming-chunk" } : null,
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
}) => {
  // Extract error details for user-friendly formatting
  let errorMessage =
    event.message ||
    (isForgeObservation(event) && typeof event.content === "string"
      ? event.content
      : "");
  
  let errorObject: unknown = null;
  
  // Try to parse JSON from content if it's a string
  if (isForgeObservation(event) && typeof event.content === "string") {
    try {
      const parsed = JSON.parse(event.content);
      if (parsed && typeof parsed === "object" && "title" in parsed) {
        errorObject = parsed; // Use structured error
        errorMessage = parsed.message || parsed.title || errorMessage;
      }
    } catch {
      // Not JSON, use as string
      errorMessage = event.content;
    }
  } else if (isForgeObservation(event) && typeof event.content === "object") {
    errorObject = event.content;
  }
  
  // Fallback to simple error object if no structured error found
  if (!errorObject) {
    errorObject = { message: errorMessage, ...extras };
  }

  return (
    <div>
      <ErrorMessage
        errorId={
          typeof extras.error_id === "string" ? extras.error_id : undefined
        }
        defaultMessage={errorMessage}
        error={errorObject}
      />
    </div>
  );
};

const renderPairedThoughtDecision: DecisionHandler = ({
  args,
  actions,
  onAskAboutCode,
  onRunCode,
  hideAvatar,
  compactMode,
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
  </div>
);

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
  </>
);

const renderChatMessageDecision: DecisionHandler = (context) => {
  const { event, actions, onAskAboutCode, onRunCode, hideAvatar, compactMode } =
    context;
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


const renderRunDecision: DecisionHandler = ({
  event,
  extras,
  shouldShowConfirmationButtons,
}) =>
  isForgeObservation(event) ? (
    <div>
      <StreamingTerminal
        eventId={String(event.id)}
        content={String(typeof event.content === "string" ? event.content : "")}
        exitCode={
          typeof extras.exit_code === "number" ? extras.exit_code : undefined
        }
        command={
          typeof extras.command === "string" ? extras.command : undefined
        }
      />
      {shouldShowConfirmationButtons && <ConfirmationButtons />}
    </div>
  ) : null;

const renderFileEditObservationDecision: DecisionHandler = ({
  event,
  extras,
  shouldShowConfirmationButtons,
}) => {
  if (!isForgeObservation(event) || event.observation !== "edit") {
    return null;
  }

  const path = typeof extras.path === "string" ? extras.path : "";
  const oldContent = typeof extras.old_content === "string" ? extras.old_content : "";
  const newContent = typeof extras.new_content === "string" ? extras.new_content : "";
  const diffText =
    typeof extras.diff === "string"
      ? extras.diff
      : typeof event.content === "string"
        ? event.content
        : "";
  const isPreview = extras.preview === true;
  const canRenderDiff =
    typeof extras.old_content === "string" || typeof extras.new_content === "string";
  const language = getLanguageFromPath(path);

  return (
    <div className="space-y-2">
      <GenericEventMessage
        title={isPreview ? "Edit preview" : "File edit"}
        details={path || "File changes"}
        success
      />
      {canRenderDiff ? (
        <div className="h-[280px] rounded-lg overflow-hidden border border-border">
          <DiffEditor
            theme="vs-dark"
            language={language}
            original={oldContent}
            modified={newContent}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              renderSideBySide: true,
              wordWrap: "on",
              automaticLayout: true,
            }}
          />
        </div>
      ) : (
        <GenericEventMessage
          title={path || "File edit diff"}
          details={diffText || "No diff available."}
          success
        />
      )}
      {shouldShowConfirmationButtons && <ConfirmationButtons />}
    </div>
  );
};

const renderGenericDecision: DecisionHandler = (context) => {
  const {
    event,
    attachments,
    renderStreamingThought,
    shouldShowConfirmationButtons,
  } = context;
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
  "file-write": renderFileWriteDecision,
  "file-edit": renderFileEditDecision,
  "file-edit-observation": renderFileEditObservationDecision,
  "streaming-chunk": renderStreamingChunkDecision,
  finish: renderFinishDecision,
  "chat-message": renderChatMessageDecision,
  reject: renderRejectDecision,
  mcp: renderMcpDecision,
  run: renderRunDecision,
  generic: renderGenericDecision,
};

interface EventMessageProps {
  event: ForgeAction | ForgeObservation;
  hasObservationPair: boolean;
  isAwaitingUserConfirmation: boolean;
  isLastMessage: boolean;
  showTechnicalDetails?: boolean;
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

function EventMessageComponent({
  event,
  hasObservationPair,
  isAwaitingUserConfirmation,
  isLastMessage,
  showTechnicalDetails,
  actions,
  isInLast10Actions,
  onAskAboutCode,
  onRunCode,
  hideAvatar,
  compactMode,
}: EventMessageProps) {
  const controller = useEventMessageController({
    event,
    hasObservationPair,
    isAwaitingUserConfirmation,
    isLastMessage,
    showTechnicalDetails,
    actions,
    isInLast10Actions,
    onAskAboutCode,
    onRunCode,
    hideAvatar,
    compactMode,
  });

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
  actions,
  isInLast10Actions,
  onAskAboutCode,
  onRunCode,
  hideAvatar = false,
  compactMode = false,
}: EventMessageProps) {
  const { curAgentState } = useSelector((state: RootState) => state.agent);
  const { hydratedEventIds } = useWsClient();

  const shouldShowConfirmationButtons = useMemo(
    () => isLastMessage && isAwaitingUserConfirmation,
    [isAwaitingUserConfirmation, isLastMessage],
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
        </div>
      );
    },
    [
      event.id,
      renderStreamingThought,
      shouldStreamCodeArtifact,
    ],
  );

  const getEventHydratedFlag = useCallback(
    (ev: ForgeAction | ForgeObservation) => {
      try {
        const v = ev as unknown as Record<string, unknown>;
        return Boolean(v.__hydrated);
      } catch (_e) {
        return false;
      }
    },
    [],
  );

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
      onAskAboutCode,
      onRunCode,
      renderCodeArtifactBlock,
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
