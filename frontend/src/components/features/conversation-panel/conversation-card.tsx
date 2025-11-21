import React from "react";
import { Clock3 } from "lucide-react";
import { useSelector } from "react-redux";
import posthog from "posthog-js";
import { useTranslation } from "react-i18next";
import ClientTimeDelta from "#/components/shared/ClientTimeDelta";
import ClientNumber from "#/components/shared/ClientNumber";
import { ConversationRepoLink } from "./conversation-repo-link";
import { ConversationStateIndicator } from "./conversation-state-indicator";
import { EllipsisButton } from "./ellipsis-button";
import { ConversationCardContextMenu } from "./conversation-card-context-menu";
import { SystemMessageModal } from "./system-message-modal";
import { MicroagentsModal } from "./microagents-modal";
import { BudgetDisplay } from "./budget-display";
import { cn } from "#/utils/utils";
import { BaseModal } from "../../shared/modals/base-modal/base-modal";
import { RootState } from "#/store";
import { I18nKey } from "#/i18n/declaration";
import { transformVSCodeUrl } from "#/utils/vscode-url-helper";
import Forge from "#/api/forge";
import { useWsClient } from "#/context/ws-client-provider";
import { isSystemMessage } from "#/types/core/guards";
import { ConversationStatus } from "#/types/conversation-status";
import { RepositorySelection } from "#/api/forge.types";

interface ConversationCardProps {
  onClick?: () => void;
  onDelete?: () => void;
  onStop?: () => void;
  onChangeTitle?: (title: string) => void;
  showOptions?: boolean;
  isActive?: boolean;
  title: string;
  selectedRepository: RepositorySelection | null;
  lastUpdatedAt: string;
  createdAt?: string;
  conversationStatus?: ConversationStatus;
  variant?: "compact" | "default";
  conversationId?: string;
  contextMenuOpen?: boolean;
  onContextMenuToggle?: (isOpen: boolean) => void;
}

const MAX_TIME_BETWEEN_CREATION_AND_UPDATE = 1000 * 60 * 30;
type TitleMode = "view" | "edit";

// Helper functions - defined before useConversationCardController hook
function createBlurHandler({
  inputRef,
  title,
  onChangeTitle,
  setTitleMode,
}: {
  inputRef: React.RefObject<HTMLInputElement>;
  title: string;
  onChangeTitle?: (title: string) => void;
  setTitleMode: React.Dispatch<React.SetStateAction<TitleMode>>;
}) {
  return () => {
    const node = inputRef.current;
    if (node?.value) {
      const trimmed = node.value.trim();
      onChangeTitle?.(trimmed);
      node.value = trimmed;
    } else if (node) {
      node.value = title;
    }
    setTitleMode("view");
  };
}

function createKeyUpHandler() {
  return (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
    }
  };
}

function createInputClickHandler(isEditMode: () => boolean) {
  return (event: React.MouseEvent<HTMLInputElement>) => {
    if (isEditMode()) {
      event.preventDefault();
      event.stopPropagation();
    }
  };
}

function createDeleteHandler(
  onDelete?: () => void,
  toggle?: (open: boolean) => void,
) {
  return (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onDelete?.();
    toggle?.(false);
  };
}

function createStopHandler(
  onStop?: () => void,
  toggle?: (open: boolean) => void,
) {
  return (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onStop?.();
    toggle?.(false);
  };
}

function createEditHandler(
  setTitleMode: React.Dispatch<React.SetStateAction<TitleMode>>,
  toggle?: (open: boolean) => void,
) {
  return (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setTitleMode("edit");
    toggle?.(false);
  };
}

function createDownloadHandler({
  conversationId,
  onToggle,
}: {
  conversationId?: string;
  onToggle?: (open: boolean) => void;
}) {
  return async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    posthog.capture("download_via_vscode_button_clicked");

    if (!conversationId) {
      onToggle?.(false);
      return;
    }

    try {
      const data = await Forge.getVSCodeUrl(conversationId);
      if (data.vscode_url) {
        const transformedUrl = transformVSCodeUrl(data.vscode_url);
        if (transformedUrl) {
          window.open(transformedUrl, "_blank");
        }
      }
    } catch (error) {
      // Ignore download failures.
    } finally {
      onToggle?.(false);
    }
  };
}

function createDisplayCostHandler(
  setMetricsModalVisible: React.Dispatch<React.SetStateAction<boolean>>,
) {
  return (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    setMetricsModalVisible(true);
  };
}

function createShowAgentToolsHandler(
  setSystemModalVisible: React.Dispatch<React.SetStateAction<boolean>>,
) {
  return (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    setSystemModalVisible(true);
  };
}

function createShowMicroagentsHandler(
  setMicroagentsModalVisible: React.Dispatch<React.SetStateAction<boolean>>,
) {
  return (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    setMicroagentsModalVisible(true);
  };
}

function hasContextMenuOptions({
  onDelete,
  onStop,
  onChangeTitle,
  conversationId,
  showOptions,
  conversationStatus,
  systemMessage,
}: {
  onDelete?: () => void;
  onStop?: () => void;
  onChangeTitle?: (title: string) => void;
  conversationId?: string;
  showOptions?: boolean;
  conversationStatus: ConversationStatus;
  systemMessage:
    | ReturnType<typeof useWsClient>["parsedEvents"][number]
    | undefined;
}): boolean {
  return (
    Boolean(onDelete) ||
    (conversationStatus !== "STOPPED" && Boolean(onStop)) ||
    Boolean(onChangeTitle) ||
    Boolean(conversationId && showOptions) ||
    Boolean(showOptions) ||
    Boolean(showOptions && systemMessage) ||
    Boolean(showOptions && conversationId)
  );
}

function shouldShowUpdateTime({
  lastUpdatedAt,
  createdAt,
}: {
  lastUpdatedAt: string;
  createdAt?: string;
}): boolean {
  if (!createdAt) return true;
  const timeBetweenUpdateAndCreation =
    new Date(lastUpdatedAt).getTime() - new Date(createdAt).getTime();
  return timeBetweenUpdateAndCreation > MAX_TIME_BETWEEN_CREATION_AND_UPDATE;
}

function buildMenuActions({
  onDelete,
  onStop,
  onChangeTitle,
  conversationId,
  showOptions,
  conversationStatus,
  systemMessage,
}: {
  onDelete?: () => void;
  onStop?: () => void;
  onChangeTitle?: (title: string) => void;
  conversationId?: string;
  showOptions?: boolean;
  conversationStatus: ConversationStatus;
  systemMessage:
    | ReturnType<typeof useWsClient>["parsedEvents"][number]
    | undefined;
}): ConversationCardMenuActions {
  return {
    canDelete: Boolean(onDelete),
    canStop: conversationStatus !== "STOPPED" && Boolean(onStop),
    canEdit: Boolean(onChangeTitle),
    canDownload: Boolean(conversationId && showOptions),
    canDisplayCost: Boolean(showOptions),
    canShowAgentTools: Boolean(showOptions && systemMessage),
    canShowMicroagents: Boolean(showOptions && conversationId),
  };
}

function buildMenuHandlers({
  onContextMenuToggle,
  onDelete,
  onStop,
  onChangeTitle,
  conversationId,
  showOptions,
  handleDelete,
  handleStop,
  handleEdit,
  handleDownloadViaVSCode,
  handleDisplayCost,
  handleShowAgentTools,
  handleShowMicroagents,
  systemMessage,
}: {
  onContextMenuToggle?: (isOpen: boolean) => void;
  onDelete?: () => void;
  onStop?: () => void;
  onChangeTitle?: (title: string) => void;
  conversationId?: string;
  showOptions?: boolean;
  handleDelete: ReturnType<typeof createDeleteHandler>;
  handleStop: ReturnType<typeof createStopHandler>;
  handleEdit: ReturnType<typeof createEditHandler>;
  handleDownloadViaVSCode: ReturnType<typeof createDownloadHandler>;
  handleDisplayCost: ReturnType<typeof createDisplayCostHandler>;
  handleShowAgentTools: ReturnType<typeof createShowAgentToolsHandler>;
  handleShowMicroagents: ReturnType<typeof createShowMicroagentsHandler>;
  systemMessage:
    | ReturnType<typeof useWsClient>["parsedEvents"][number]
    | undefined;
}): ConversationCardMenuHandlers {
  const conditionalHandlers: Array<{
    condition: boolean;
    key: keyof Omit<ConversationCardMenuHandlers, "toggle">;
    handler: ConversationCardMenuHandlers[keyof ConversationCardMenuHandlers];
  }> = [
    { condition: Boolean(onDelete), key: "delete", handler: handleDelete },
    { condition: Boolean(onStop), key: "stop", handler: handleStop },
    { condition: Boolean(onChangeTitle), key: "edit", handler: handleEdit },
    {
      condition: Boolean(conversationId && showOptions),
      key: "download",
      handler: handleDownloadViaVSCode,
    },
    {
      condition: Boolean(showOptions),
      key: "displayCost",
      handler: handleDisplayCost,
    },
    {
      condition: Boolean(showOptions && systemMessage),
      key: "showAgentTools",
      handler: handleShowAgentTools,
    },
    {
      condition: Boolean(showOptions && conversationId),
      key: "showMicroagents",
      handler: handleShowMicroagents,
    },
  ];

  return conditionalHandlers.reduce<ConversationCardMenuHandlers>(
    (handlers, { condition, key, handler }) => {
      if (condition) {
        return {
          ...handlers,
          [key]: handler as ConversationCardMenuHandlers[typeof key],
        };
      }
      return handlers;
    },
    { toggle: onContextMenuToggle },
  );
}

interface ConversationCardControllerParams {
  title: string;
  lastUpdatedAt: string;
  createdAt?: string;
  onChangeTitle?: (title: string) => void;
  onDelete?: () => void;
  onStop?: () => void;
  showOptions?: boolean;
  variant: ConversationCardProps["variant"];
  conversationStatus: ConversationStatus;
  conversationId?: string;
  contextMenuOpen: boolean;
  onContextMenuToggle?: (isOpen: boolean) => void;
}

interface ConversationCardController {
  titleMode: TitleMode;
  inputRef: React.RefObject<HTMLInputElement>;
  handleInputClick: (event: React.MouseEvent<HTMLInputElement>) => void;
  handleBlur: (event: React.FocusEvent<HTMLInputElement>) => void;
  handleKeyUp: (event: React.KeyboardEvent<HTMLInputElement>) => void;
  menuConfig: ConversationCardMenuConfig;
  hasContextMenu: boolean;
  showUpdateTime: boolean;
  metricsModalVisible: boolean;
  setMetricsModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
  systemModalVisible: boolean;
  setSystemModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
  microagentsModalVisible: boolean;
  setMicroagentsModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
  systemMessage:
    | ReturnType<typeof useWsClient>["parsedEvents"][number]
    | undefined;
  metrics: RootState["metrics"];
}

function useConversationCardController({
  title,
  lastUpdatedAt,
  createdAt,
  onChangeTitle,
  onDelete,
  onStop,
  showOptions,
  variant,
  conversationStatus,
  conversationId,
  contextMenuOpen,
  onContextMenuToggle,
}: ConversationCardControllerParams): ConversationCardController {
  const { parsedEvents } = useWsClient();
  const systemMessage = React.useMemo(
    () => parsedEvents.find(isSystemMessage),
    [parsedEvents],
  );
  const metrics = useSelector((state: RootState) => state.metrics);

  const inputRef = React.useRef<HTMLInputElement>(null);
  const [titleMode, setTitleMode] = React.useState<TitleMode>("view");
  const [metricsModalVisible, setMetricsModalVisible] = React.useState(false);
  const [systemModalVisible, setSystemModalVisible] = React.useState(false);
  const [microagentsModalVisible, setMicroagentsModalVisible] =
    React.useState(false);

  const handleBlur = React.useMemo(
    () =>
      createBlurHandler({
        inputRef: inputRef as React.RefObject<HTMLInputElement>,
        title,
        onChangeTitle,
        setTitleMode,
      }),
    [title, onChangeTitle],
  );

  const handleKeyUp = React.useMemo(() => createKeyUpHandler(), []);

  const handleInputClick = React.useMemo(
    () => createInputClickHandler(() => titleMode === "edit"),
    [titleMode],
  );

  const handleDelete = React.useMemo(
    () => createDeleteHandler(onDelete, onContextMenuToggle),
    [onDelete, onContextMenuToggle],
  );

  const handleStop = React.useMemo(
    () => createStopHandler(onStop, onContextMenuToggle),
    [onStop, onContextMenuToggle],
  );

  const handleEdit = React.useMemo(
    () => createEditHandler(setTitleMode, onContextMenuToggle),
    [onContextMenuToggle],
  );

  const handleDownloadViaVSCode = React.useMemo(
    () =>
      createDownloadHandler({ conversationId, onToggle: onContextMenuToggle }),
    [conversationId, onContextMenuToggle],
  );

  const handleDisplayCost = React.useMemo(
    () => createDisplayCostHandler(setMetricsModalVisible),
    [],
  );

  const handleShowAgentTools = React.useMemo(
    () => createShowAgentToolsHandler(setSystemModalVisible),
    [],
  );

  const handleShowMicroagents = React.useMemo(
    () => createShowMicroagentsHandler(setMicroagentsModalVisible),
    [],
  );

  React.useEffect(() => {
    if (titleMode === "edit") {
      inputRef.current?.focus();
    }
  }, [titleMode]);

  const hasContextMenu = React.useMemo(
    () =>
      hasContextMenuOptions({
        onDelete,
        onChangeTitle,
        showOptions,
        conversationStatus,
        systemMessage,
      }),
    [onDelete, onChangeTitle, showOptions, conversationStatus, systemMessage],
  );

  const showUpdateTime = React.useMemo(
    () => shouldShowUpdateTime({ createdAt, lastUpdatedAt }),
    [createdAt, lastUpdatedAt],
  );

  const menuActions = React.useMemo(
    () =>
      buildMenuActions({
        onDelete,
        onStop,
        onChangeTitle,
        conversationId,
        showOptions,
        conversationStatus,
        systemMessage,
      }),
    [
      onDelete,
      onStop,
      onChangeTitle,
      conversationId,
      showOptions,
      conversationStatus,
      systemMessage,
    ],
  );

  const menuHandlers = React.useMemo(
    () =>
      buildMenuHandlers({
        onContextMenuToggle,
        onDelete,
        onStop,
        onChangeTitle,
        conversationId,
        showOptions,
        handleDelete,
        handleStop,
        handleEdit,
        handleDownloadViaVSCode,
        handleDisplayCost,
        handleShowAgentTools,
        handleShowMicroagents,
        systemMessage,
      }),
    [
      onContextMenuToggle,
      onDelete,
      onStop,
      onChangeTitle,
      conversationId,
      showOptions,
      handleDelete,
      handleStop,
      handleEdit,
      handleDownloadViaVSCode,
      handleDisplayCost,
      handleShowAgentTools,
      handleShowMicroagents,
      systemMessage,
    ],
  );

  const menuConfig = React.useMemo<ConversationCardMenuConfig>(
    () => ({
      isOpen: contextMenuOpen,
      position: variant === "compact" ? "top" : "bottom",
      actions: menuActions,
      handlers: menuHandlers,
    }),
    [contextMenuOpen, variant, menuActions, menuHandlers],
  );

  return {
    titleMode,
    inputRef: inputRef as React.RefObject<HTMLInputElement>,
    handleInputClick,
    handleBlur,
    handleKeyUp,
    menuConfig,
    hasContextMenu,
    showUpdateTime,
    metricsModalVisible,
    setMetricsModalVisible,
    systemModalVisible,
    setSystemModalVisible,
    microagentsModalVisible,
    setMicroagentsModalVisible,
    systemMessage,
    metrics,
  };
}

type ConversationCardMenuActions = {
  canDelete: boolean;
  canStop: boolean;
  canEdit: boolean;
  canDownload: boolean;
  canDisplayCost: boolean;
  canShowAgentTools: boolean;
  canShowMicroagents: boolean;
};

type ConversationCardMenuHandlers = {
  toggle?: (open: boolean) => void;
  delete?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  stop?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  edit?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  download?: (
    event: React.MouseEvent<HTMLButtonElement>,
  ) => Promise<void> | void;
  displayCost?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  showAgentTools?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  showMicroagents?: (event: React.MouseEvent<HTMLButtonElement>) => void;
};

type ConversationCardMenuConfig = {
  isOpen: boolean;
  position: "top" | "bottom";
  actions: ConversationCardMenuActions;
  handlers: ConversationCardMenuHandlers;
};

// Component definitions - must be defined before ConversationCard
// Order: leaf components first, then components that use them

// Leaf components (no dependencies on other local components)
function CardActiveIndicator() {
  return (
    <span
      className="w-3 h-3 rounded-full flex-shrink-0 animate-pulse bg-gradient-to-r from-brand-500 to-accent-500"
      style={{ boxShadow: "0 0 8px 3px rgba(59, 130, 246, 0.4)" }}
    />
  );
}

interface ConversationCardTitleProps {
  title: string;
  mode: TitleMode;
  inputRef: React.RefObject<HTMLInputElement>;
  onInputClick: (event: React.MouseEvent<HTMLInputElement>) => void;
  onBlur: (event: React.FocusEvent<HTMLInputElement>) => void;
  onKeyUp: (event: React.KeyboardEvent<HTMLInputElement>) => void;
}

function ConversationCardTitle({
  title,
  mode,
  inputRef,
  onInputClick,
  onBlur,
  onKeyUp,
}: ConversationCardTitleProps) {
  if (mode === "edit") {
    return (
      <input
        ref={inputRef}
        data-testid="conversation-card-title"
        onClick={onInputClick}
        onBlur={onBlur}
        onKeyUp={onKeyUp}
        type="text"
        defaultValue={title}
        className="text-sm leading-6 font-semibold bg-transparent w-full text-foreground placeholder:text-foreground-secondary/50 focus:outline-none focus:ring-2 focus:ring-brand-500/50 rounded px-2 py-1"
      />
    );
  }

  return (
    <div className="relative flex-1 min-w-0">
      <p
        data-testid="conversation-card-title"
        className="text-sm leading-6 font-semibold bg-transparent truncate pr-4 text-foreground group-hover:text-violet-500 transition-colors duration-300"
        title={title}
      >
        {title}
      </p>
      <div className="pointer-events-none absolute right-0 top-0 h-full w-6 bg-gradient-to-l from-background-secondary via-background-secondary/40 to-transparent" />
    </div>
  );
}

function ConversationCardMenuContent({
  config,
}: {
  config: ConversationCardMenuConfig;
}) {
  if (!config.isOpen) {
    return null;
  }

  const {
    position,
    actions,
    handlers: {
      toggle,
      delete: handleDelete,
      stop: handleStop,
      edit: handleEdit,
      download: handleDownload,
      displayCost,
      showAgentTools,
      showMicroagents,
    },
  } = config;

  return (
    <div className="relative">
      <ConversationCardContextMenu
        onClose={() => toggle?.(false)}
        onDelete={actions.canDelete ? handleDelete : undefined}
        onStop={actions.canStop ? handleStop : undefined}
        onEdit={actions.canEdit ? handleEdit : undefined}
        onDownloadViaVSCode={actions.canDownload ? handleDownload : undefined}
        onDisplayCost={actions.canDisplayCost ? displayCost : undefined}
        onShowAgentTools={
          actions.canShowAgentTools ? showAgentTools : undefined
        }
        onShowMicroagents={
          actions.canShowMicroagents ? showMicroagents : undefined
        }
        position={position}
      />
    </div>
  );
}

// Helper functions for metrics
function hasMetricsData(metrics: RootState["metrics"]) {
  return Boolean(metrics?.cost !== null || metrics?.usage !== null);
}

function MetricsCostSection({
  metrics,
  t,
}: {
  metrics: RootState["metrics"];
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (metrics?.cost == null) {
    return null;
  }

  return (
    <div className="flex justify-between items-center pb-2">
      <span className="text-lg font-semibold text-foreground">
        {t(I18nKey.CONVERSATION$TOTAL_COST)}
      </span>
      <span className="font-semibold text-violet-500">
        ${metrics.cost.toFixed(4)}
      </span>
    </div>
  );
}

function MetricsContextWindow({
  usage,
  contextUsagePercentage,
  t,
}: {
  usage: NonNullable<RootState["metrics"]>["usage"];
  contextUsagePercentage: string;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-foreground">
          {t(I18nKey.CONVERSATION$CONTEXT_WINDOW)}
        </span>
      </div>
      <div className="w-full h-2 bg-background-tertiary rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-500 to-accent-500 transition-all duration-300"
          style={{
            width: `${Math.min(100, ((usage?.per_turn_token ?? 0) / (usage?.context_window ?? 1)) * 100)}%`,
          }}
        />
      </div>
      <div className="flex justify-end">
        <span className="text-xs text-foreground-secondary">
          <ClientNumber value={usage?.per_turn_token ?? 0} /> {"/"}{" "}
          <ClientNumber value={usage?.context_window ?? 0} /> (
          {contextUsagePercentage}% {t(I18nKey.CONVERSATION$USED)})
        </span>
      </div>
    </div>
  );
}

function MetricsUsageSection({
  metrics,
  t,
}: {
  metrics: RootState["metrics"];
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (!metrics?.usage) {
    return null;
  }

  const { usage } = metrics;
  const totalTokens = usage.prompt_tokens + usage.completion_tokens;
  const contextUsagePercentage = (
    (usage.per_turn_token / usage.context_window) *
    100
  ).toFixed(2);

  return (
    <>
      <div className="flex justify-between items-center pb-2">
        <span className="text-foreground-secondary">
          {t(I18nKey.CONVERSATION$INPUT)}
        </span>
        <span className="font-semibold text-foreground">
          <ClientNumber value={usage.prompt_tokens} />
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 pl-4 text-sm">
        <span className="text-foreground-secondary">
          {t(I18nKey.CONVERSATION$CACHE_HIT)}
        </span>
        <span className="text-right text-foreground">
          <ClientNumber value={usage.cache_read_tokens} />
        </span>
        <span className="text-foreground-secondary">
          {t(I18nKey.CONVERSATION$CACHE_WRITE)}
        </span>
        <span className="text-right text-foreground">
          <ClientNumber value={usage.cache_write_tokens} />
        </span>
      </div>

      <div className="flex justify-between items-center border-b border-border pb-2">
        <span className="text-foreground-secondary">
          {t(I18nKey.CONVERSATION$OUTPUT)}
        </span>
        <span className="font-semibold text-foreground">
          <ClientNumber value={usage.completion_tokens} />
        </span>
      </div>

      <div className="flex justify-between items-center border-b border-border pb-2">
        <span className="font-semibold text-foreground">
          {t(I18nKey.CONVERSATION$TOTAL)}
        </span>
        <span className="font-bold text-violet-500">
          <ClientNumber value={totalTokens} />
        </span>
      </div>

      <MetricsContextWindow
        usage={usage}
        contextUsagePercentage={contextUsagePercentage}
        t={t}
      />
    </>
  );
}

function MetricsContent({
  metrics,
  t,
}: {
  metrics: RootState["metrics"];
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (!hasMetricsData(metrics)) {
    return (
      <div className="card-modern text-center">
        <p className="text-foreground-secondary">
          {t(I18nKey.CONVERSATION$NO_METRICS)}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="card-modern">
        <div className="grid gap-3">
          <MetricsCostSection metrics={metrics} t={t} />
          <BudgetDisplay
            cost={metrics?.cost ?? null}
            maxBudgetPerTask={metrics?.max_budget_per_task ?? null}
          />
          <MetricsUsageSection metrics={metrics} t={t} />
        </div>
      </div>
    </div>
  );
}

function MetricsModal({
  isOpen,
  onOpenChange,
  metrics,
  t,
}: {
  isOpen: boolean;
  onOpenChange: React.Dispatch<React.SetStateAction<boolean>>;
  metrics: RootState["metrics"];
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <BaseModal
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      title={t(I18nKey.CONVERSATION$METRICS_INFO)}
      testID="metrics-modal"
    >
      <MetricsContent metrics={metrics} t={t} />
    </BaseModal>
  );
}

// Components that use other local components
interface ConversationCardMenuProps {
  hasContextMenu: boolean;
  conversationStatus: ConversationStatus;
  config: ConversationCardMenuConfig;
}

function ConversationCardMenu({
  hasContextMenu,
  conversationStatus,
  config,
}: ConversationCardMenuProps) {
  return (
    <div className="flex items-center">
      <ConversationStateIndicator conversationStatus={conversationStatus} />
      {hasContextMenu && (
        <div className="pl-2">
          <EllipsisButton
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              config.handlers.toggle?.(!config.isOpen);
            }}
          />
        </div>
      )}
      <ConversationCardMenuContent config={config} />
    </div>
  );
}

interface ConversationCardHeaderProps {
  title: string;
  titleMode: TitleMode;
  inputRef: React.RefObject<HTMLInputElement>;
  onInputClick: (event: React.MouseEvent<HTMLInputElement>) => void;
  onBlur: (event: React.FocusEvent<HTMLInputElement>) => void;
  onKeyUp: (event: React.KeyboardEvent<HTMLInputElement>) => void;
  isActive: boolean;
  conversationStatus: ConversationStatus;
  hasContextMenu: boolean;
  menuConfig: ConversationCardMenuConfig;
}

function ConversationCardHeader({
  title,
  titleMode,
  inputRef,
  onInputClick,
  onBlur,
  onKeyUp,
  isActive,
  conversationStatus,
  hasContextMenu,
  menuConfig,
}: ConversationCardHeaderProps) {
  return (
    <div className="flex items-center justify-between w-full">
      <div className="flex items-center gap-2 flex-1 min-w-0 overflow-hidden mr-2">
        {isActive && <CardActiveIndicator />}
        <ConversationCardTitle
          title={title}
          mode={titleMode}
          inputRef={inputRef}
          onInputClick={onInputClick}
          onBlur={onBlur}
          onKeyUp={onKeyUp}
        />
      </div>
      <ConversationCardMenu
        conversationStatus={conversationStatus}
        hasContextMenu={hasContextMenu}
        config={menuConfig}
      />
    </div>
  );
}

interface ConversationCardMetadataProps {
  createdAt?: string;
  lastUpdatedAt: string;
  selectedRepository: RepositorySelection | null;
  showUpdateTime: boolean;
  variant: ConversationCardProps["variant"];
  t: ReturnType<typeof useTranslation>["t"];
}

function ConversationCardMetadata({
  createdAt,
  lastUpdatedAt,
  selectedRepository,
  showUpdateTime,
  variant,
  t,
}: ConversationCardMetadataProps) {
  return (
    <div
      className={cn(
        "mt-1 space-y-1",
        variant === "compact" && "flex flex-col justify-between",
      )}
    >
      {selectedRepository?.selected_repository && (
        <ConversationRepoLink
          selectedRepository={selectedRepository}
          variant={variant ?? "default"}
        />
      )}
      {(createdAt || lastUpdatedAt) && (
        <div className="flex items-center gap-1 text-[11px] text-foreground-secondary font-medium tracking-wide">
          <Clock3 className="w-3 h-3 opacity-60 text-foreground-secondary" />
          <span>
            {t(I18nKey.CONVERSATION$CREATED)}
            <ClientTimeDelta dateIso={createdAt || lastUpdatedAt} />
            {t(I18nKey.CONVERSATION$AGO)}
          </span>
          {showUpdateTime && (
            <span className="inline-flex items-center gap-1 before:content-['•'] before:text-foreground-secondary/60 before:px-1">
              {t(I18nKey.CONVERSATION$UPDATED)}
              <ClientTimeDelta dateIso={lastUpdatedAt} />
              {t(I18nKey.CONVERSATION$AGO)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

interface ConversationCardModalsProps {
  metricsModalVisible: boolean;
  setMetricsModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
  systemModalVisible: boolean;
  setSystemModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
  microagentsModalVisible: boolean;
  setMicroagentsModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
  systemMessage?: unknown;
  metrics: RootState["metrics"];
  t: ReturnType<typeof useTranslation>["t"];
}

function ConversationCardModals({
  metricsModalVisible,
  setMetricsModalVisible,
  systemModalVisible,
  setSystemModalVisible,
  microagentsModalVisible,
  setMicroagentsModalVisible,
  systemMessage,
  metrics,
  t,
}: ConversationCardModalsProps) {
  return (
    <>
      <MetricsModal
        isOpen={metricsModalVisible}
        onOpenChange={setMetricsModalVisible}
        metrics={metrics}
        t={t}
      />

      <SystemMessageModal
        isOpen={systemModalVisible}
        onClose={() => setSystemModalVisible(false)}
        systemMessage={
          systemMessage && isSystemMessage(systemMessage)
            ? systemMessage.args
            : null
        }
      />

      {microagentsModalVisible && (
        <MicroagentsModal onClose={() => setMicroagentsModalVisible(false)} />
      )}
    </>
  );
}

interface ConversationCardShellProps
  extends React.HTMLAttributes<HTMLDivElement> {
  variant: ConversationCardProps["variant"];
  isActive: boolean;
  "data-testid"?: string;
}

function ConversationCardShell({
  children,
  variant,
  isActive,
  className,
  onClick,
  onMouseEnter,
  onMouseLeave,
  onFocus,
  onBlur,
  "data-testid": dataTestId,
  ...rest
}: ConversationCardShellProps) {
  return (
    <div
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onFocus={onFocus}
      onBlur={onBlur}
      data-testid={dataTestId}
      // eslint-disable-next-line react/jsx-props-no-spreading
      {...rest}
      className={cn(
        "group relative h-auto w-full px-4 py-4 cursor-pointer transition-all duration-300",
        "before:absolute before:inset-y-0 before:left-0 before:w-1 before:rounded-r before:transition-all before:duration-300",
        isActive
          ? "before:bg-gradient-to-b before:from-brand-500 before:to-accent-500 bg-brand-500/5 hover:bg-violet-500/10"
          : "before:bg-brand-500/0 group-hover:before:bg-brand-500/70",
        "hover:bg-background-tertiary hover:shadow-lg",
        variant === "compact" &&
          "md:w-fit h-auto rounded-2xl border border-border bg-background-secondary shadow-lg",
        !isActive && variant !== "compact" && "border-b border-border",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function ConversationCard({
  onClick,
  onDelete,
  onStop,
  onChangeTitle,
  showOptions,
  isActive,
  title,
  selectedRepository,
  lastUpdatedAt,
  createdAt,
  conversationStatus = "STOPPED",
  variant = "default",
  conversationId,
  contextMenuOpen = false,
  onContextMenuToggle,
}: ConversationCardProps) {
  const { t } = useTranslation();
  const controller = useConversationCardController({
    title,
    lastUpdatedAt,
    createdAt,
    onChangeTitle,
    onDelete,
    onStop,
    showOptions,
    variant,
    conversationStatus,
    conversationId,
    contextMenuOpen,
    onContextMenuToggle,
  });

  return (
    <>
      <ConversationCardShell
        data-testid="conversation-card"
        onClick={onClick}
        variant={variant}
        isActive={Boolean(isActive)}
      >
        <ConversationCardHeader
          title={title}
          titleMode={controller.titleMode}
          inputRef={controller.inputRef}
          onInputClick={controller.handleInputClick}
          onBlur={controller.handleBlur}
          onKeyUp={controller.handleKeyUp}
          isActive={Boolean(isActive)}
          conversationStatus={conversationStatus}
          hasContextMenu={controller.hasContextMenu}
          menuConfig={controller.menuConfig}
        />

        <ConversationCardMetadata
          createdAt={createdAt}
          lastUpdatedAt={lastUpdatedAt}
          selectedRepository={selectedRepository}
          showUpdateTime={controller.showUpdateTime}
          variant={variant}
          t={t}
        />
      </ConversationCardShell>

      <ConversationCardModals
        metricsModalVisible={controller.metricsModalVisible}
        setMetricsModalVisible={controller.setMetricsModalVisible}
        systemModalVisible={controller.systemModalVisible}
        setSystemModalVisible={controller.setSystemModalVisible}
        microagentsModalVisible={controller.microagentsModalVisible}
        setMicroagentsModalVisible={controller.setMicroagentsModalVisible}
        systemMessage={controller.systemMessage}
        metrics={controller.metrics}
        t={t}
      />
    </>
  );
}
