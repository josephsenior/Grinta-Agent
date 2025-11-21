import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronRight } from "lucide-react";
import ReactJsonView from "@microlink/react-json-view";
import { BaseModalTitle } from "#/components/shared/modals/confirmation-modals/base-modal";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import { cn } from "#/utils/utils";
import { JSON_VIEW_THEME } from "#/utils/constants";

interface SystemMessageModalProps {
  isOpen: boolean;
  onClose: () => void;
  systemMessage: {
    content: string;
    tools: Array<Record<string, unknown>> | null;
    Forge_version: string | null;
    agent_class: string | null;
  } | null;
}

interface FunctionData {
  name?: string;
  description?: string;
  parameters?: Record<string, unknown>;
}

interface ToolData {
  type?: string;
  function?: FunctionData;
  name?: string;
  description?: string;
  parameters?: Record<string, unknown>;
}

// Helper functions
const resolveFunctionData = (toolData: ToolData): FunctionData => {
  if (toolData.type === "function" && toolData.function) {
    return toolData.function;
  }

  return {
    name: toolData.name,
    description: toolData.description,
    parameters: toolData.parameters,
  };
};

const formatToolString = (value?: string | null) =>
  value != null ? String(value) : "";

const resolveToolKey = (
  toolData: ToolData,
  functionData: FunctionData,
  index: number,
) => String(functionData.name ?? toolData.type ?? `tool-${index}`);

function normalizeTools(
  tools: Array<Record<string, unknown>>,
): NormalizedTool[] {
  return tools.map((tool, index) => {
    const toolData = tool as ToolData;
    const functionData = resolveFunctionData(toolData);
    return {
      key: resolveToolKey(toolData, functionData, index),
      name: formatToolString(functionData.name),
      description: formatToolString(functionData.description),
      parameters: functionData.parameters ?? null,
    };
  });
}

type NormalizedTool = {
  key: string;
  name: string;
  description: string;
  parameters: Record<string, unknown> | null;
};

// Leaf components (no dependencies on other local components)
function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-sm">
      <span className="font-semibold text-foreground-secondary">{label}</span>{" "}
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}

function TabButton({
  isActive,
  onClick,
  label,
}: {
  isActive: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className={cn(
        "px-4 py-2 font-medium border-b-2 transition-colors",
        isActive
          ? "border-brand-500 text-foreground"
          : "border-transparent text-foreground-secondary hover:text-foreground",
      )}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function ToolAccordion({
  tool,
  isExpanded,
  onToggle,
  parametersLabel,
}: {
  tool: NormalizedTool;
  isExpanded: boolean;
  onToggle: () => void;
  parametersLabel: string;
}) {
  return (
    <div className="rounded-md overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full py-3 px-2 text-left flex items-center justify-between hover:bg-background-tertiary transition-colors rounded-lg"
      >
        <div className="flex items-center">
          <h3 className="font-bold text-foreground">{tool.name || tool.key}</h3>
        </div>
        <span className="text-foreground-secondary">
          {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        </span>
      </button>

      {isExpanded && (
        <div className="px-2 pb-3 pt-1">
          {tool.description && (
            <div className="mt-2 mb-3">
              <p className="text-sm whitespace-pre-wrap text-foreground-secondary leading-relaxed">
                {tool.description}
              </p>
            </div>
          )}

          {tool.parameters && (
            <div className="mt-2">
              <h4 className="text-sm font-semibold text-foreground-secondary">
                {parametersLabel}
              </h4>
              <div className="text-sm mt-2 p-3 bg-background-tertiary rounded-md overflow-auto text-foreground-secondary max-h-[400px]">
                <ReactJsonView
                  name={false}
                  src={tool.parameters}
                  theme={JSON_VIEW_THEME}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Components that use leaf components
function SystemMessageMetadata({
  agentClass,
  forgeVersion,
  t,
}: {
  agentClass: string | null;
  forgeVersion: string | null;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (!agentClass && !forgeVersion) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2">
      {agentClass && (
        <MetadataRow
          label={t("SYSTEM_MESSAGE_MODAL$AGENT_CLASS")}
          value={agentClass}
        />
      )}
      {forgeVersion && (
        <MetadataRow
          label={t("SYSTEM_MESSAGE_MODAL$Forge_VERSION")}
          value={forgeVersion}
        />
      )}
    </div>
  );
}

function SystemMessageTabs({
  activeTab,
  hasTools,
  onSelect,
  t,
}: {
  activeTab: "system" | "tools";
  hasTools: boolean;
  onSelect: (tab: "system" | "tools") => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="flex border-b border-border mb-2">
      <TabButton
        isActive={activeTab === "system"}
        onClick={() => onSelect("system")}
        label={t("SYSTEM_MESSAGE_MODAL$SYSTEM_MESSAGE_TAB")}
      />
      {hasTools && (
        <TabButton
          isActive={activeTab === "tools"}
          onClick={() => onSelect("tools")}
          label={t("SYSTEM_MESSAGE_MODAL$TOOLS_TAB")}
        />
      )}
    </div>
  );
}

function ToolsTabContent({
  controller,
  t,
}: {
  controller: ReturnType<typeof useSystemMessageModalController>;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (controller.tools.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <p className="text-foreground-secondary">
          {t("SYSTEM_MESSAGE_MODAL$NO_TOOLS")}
        </p>
      </div>
    );
  }

  return (
    <div className="p-2 space-y-3">
      {controller.tools.map((tool, index) => (
        <ToolAccordion
          key={tool.key || `tool-${index}`}
          tool={tool}
          isExpanded={controller.isToolExpanded(index)}
          onToggle={() => controller.toggleTool(index)}
          parametersLabel={t("SYSTEM_MESSAGE_MODAL$PARAMETERS")}
        />
      ))}
    </div>
  );
}

// Hook
function useSystemMessageModalController(
  systemMessage: SystemMessageModalProps["systemMessage"],
) {
  const [activeTab, setActiveTab] = useState<"system" | "tools">("system");
  const [expandedTools, setExpandedTools] = useState<Record<number, boolean>>(
    {},
  );

  const tools = useMemo(
    () => normalizeTools(systemMessage?.tools ?? []),
    [systemMessage?.tools],
  );

  const toggleTool = (index: number) => {
    setExpandedTools((previous) => ({
      ...previous,
      [index]: !previous[index],
    }));
  };

  const isToolExpanded = (index: number) => Boolean(expandedTools[index]);

  return {
    activeTab,
    setActiveTab,
    tools,
    toggleTool,
    isToolExpanded,
  } as const;
}

// Main component
export function SystemMessageModal({
  isOpen,
  onClose,
  systemMessage,
}: SystemMessageModalProps) {
  const { t } = useTranslation();
  // Hook must be called before early return to satisfy React Hooks rules
  const controller = useSystemMessageModalController(systemMessage);

  if (!isOpen || !systemMessage) {
    return null;
  }

  return (
    <ModalBackdrop onClose={onClose}>
      <ModalBody
        width="medium"
        className="max-h-[80vh] flex flex-col items-start"
      >
        <div className="flex flex-col gap-6 w-full">
          <BaseModalTitle title={t("SYSTEM_MESSAGE_MODAL$TITLE")} />
          <SystemMessageMetadata
            agentClass={systemMessage.agent_class}
            forgeVersion={systemMessage.Forge_version}
            t={t}
          />
        </div>

        <div className="w-full">
          <SystemMessageTabs
            activeTab={controller.activeTab}
            hasTools={controller.tools.length > 0}
            onSelect={controller.setActiveTab}
            t={t}
          />

          <div className="max-h-[51vh] overflow-auto rounded-md">
            {controller.activeTab === "system" && (
              <div className="p-4 whitespace-pre-wrap font-mono text-sm leading-relaxed text-foreground-secondary bg-background-tertiary rounded-lg">
                {systemMessage.content}
              </div>
            )}

            {controller.activeTab === "tools" && (
              <ToolsTabContent controller={controller} t={t} />
            )}
          </div>
        </div>
      </ModalBody>
    </ModalBackdrop>
  );
}
