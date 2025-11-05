import React, { useState } from "react";
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
    openhands_version: string | null;
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

export function SystemMessageModal({
  isOpen,
  onClose,
  systemMessage,
}: SystemMessageModalProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"system" | "tools">("system");
  const [expandedTools, setExpandedTools] = useState<Record<number, boolean>>(
    {},
  );

  if (!systemMessage) {
    return null;
  }

  const toggleTool = (index: number) => {
    setExpandedTools((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  return (
    isOpen && (
      <ModalBackdrop onClose={onClose}>
        <ModalBody
          width="medium"
          className="max-h-[80vh] flex flex-col items-start"
        >
          <div className="flex flex-col gap-6 w-full">
            <BaseModalTitle title={t("SYSTEM_MESSAGE_MODAL$TITLE")} />
            <div className="flex flex-col gap-2">
              {systemMessage.agent_class && (
                <div className="text-sm">
                  <span className="font-semibold text-foreground-secondary">
                    {t("SYSTEM_MESSAGE_MODAL$AGENT_CLASS")}
                  </span>{" "}
                  <span className="font-medium text-foreground">
                    {systemMessage.agent_class}
                  </span>
                </div>
              )}
              {systemMessage.openhands_version && (
                <div className="text-sm">
                  <span className="font-semibold text-foreground-secondary">
                    {t("SYSTEM_MESSAGE_MODAL$OPENHANDS_VERSION")}
                  </span>{" "}
                  <span className="text-foreground">
                    {systemMessage.openhands_version}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="w-full">
            <div className="flex border-b border-border mb-2">
              <button
                type="button"
                className={cn(
                  "px-4 py-2 font-medium border-b-2 transition-colors",
                  activeTab === "system"
                    ? "border-brand-500 text-foreground"
                    : "border-transparent text-foreground-secondary hover:text-foreground",
                )}
                onClick={() => setActiveTab("system")}
              >
                {t("SYSTEM_MESSAGE_MODAL$SYSTEM_MESSAGE_TAB")}
              </button>
              {systemMessage.tools && systemMessage.tools.length > 0 && (
                <button
                  type="button"
                  className={cn(
                    "px-4 py-2 font-medium border-b-2 transition-colors",
                    activeTab === "tools"
                      ? "border-brand-500 text-foreground"
                      : "border-transparent text-foreground-secondary hover:text-foreground",
                  )}
                  onClick={() => setActiveTab("tools")}
                >
                  {t("SYSTEM_MESSAGE_MODAL$TOOLS_TAB")}
                </button>
              )}
            </div>

            <div className="max-h-[51vh] overflow-auto rounded-md">
              {activeTab === "system" && (
                <div className="p-4 whitespace-pre-wrap font-mono text-sm leading-relaxed text-foreground-secondary bg-background-tertiary rounded-lg">
                  {systemMessage.content}
                </div>
              )}

              {activeTab === "tools" &&
                systemMessage.tools &&
                systemMessage.tools.length > 0 && (
                  <div className="p-2 space-y-3">
                    {systemMessage.tools.map((tool, index) => {
                      // Extract function data from the nested structure
                      const toolData = tool as ToolData;
                      const functionData = toolData.function || toolData;
                      const name =
                        functionData.name ||
                        (toolData.type === "function" &&
                          toolData.function?.name) ||
                        "";
                      const description =
                        functionData.description ||
                        (toolData.type === "function" &&
                          toolData.function?.description) ||
                        "";
                      const parameters =
                        functionData.parameters ||
                        (toolData.type === "function" &&
                          toolData.function?.parameters) ||
                        null;

                      const isExpanded = expandedTools[index] || false;

                      const key =
                        String(name) || String(tool.type) || `tool-${index}`;

                      return (
                        <div
                          key={String(key)}
                          className="rounded-md overflow-hidden"
                        >
                          <button
                            type="button"
                            onClick={() => toggleTool(index)}
                            className="w-full py-3 px-2 text-left flex items-center justify-between hover:bg-background-tertiary transition-colors rounded-lg"
                          >
                            <div className="flex items-center">
                              <h3 className="font-bold text-foreground">
                                {String(name)}
                              </h3>
                            </div>
                            <span className="text-foreground-secondary">
                              {isExpanded ? (
                                <ChevronDown size={18} />
                              ) : (
                                <ChevronRight size={18} />
                              )}
                            </span>
                          </button>

                          {isExpanded && (
                            <div className="px-2 pb-3 pt-1">
                              <div className="mt-2 mb-3">
                                <p className="text-sm whitespace-pre-wrap text-foreground-secondary leading-relaxed">
                                  {String(description)}
                                </p>
                              </div>

                              {/* Parameters section */}
                              {parameters && (
                                <div className="mt-2">
                                  <h4 className="text-sm font-semibold text-foreground-secondary">
                                    {t("SYSTEM_MESSAGE_MODAL$PARAMETERS")}
                                  </h4>
                                  <div className="text-sm mt-2 p-3 bg-background-tertiary rounded-md overflow-auto text-foreground-secondary max-h-[400px]">
                                    <ReactJsonView
                                      name={false}
                                      src={parameters}
                                      theme={JSON_VIEW_THEME}
                                    />
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

              {activeTab === "tools" &&
                (!systemMessage.tools || systemMessage.tools.length === 0) && (
                  <div className="flex items-center justify-center h-full p-4">
                    <p className="text-foreground-secondary">
                      {t("SYSTEM_MESSAGE_MODAL$NO_TOOLS")}
                    </p>
                  </div>
                )}
            </div>
          </div>
        </ModalBody>
      </ModalBackdrop>
    )
  );
}
