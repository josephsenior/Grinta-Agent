import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";
import { BaseModalTitle } from "#/components/shared/modals/confirmation-modals/base-modal";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import { I18nKey } from "#/i18n/declaration";
import { useConversationMicroagents } from "#/hooks/query/use-conversation-microagents";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";
import { BrandButton } from "../settings/brand-button";

interface MicroagentsModalProps {
  onClose: () => void;
}

export function MicroagentsModal({ onClose }: MicroagentsModalProps) {
  const { t } = useTranslation();
  const { curAgentState } = useSelector((state: RootState) => state.agent);
  const controller = useMicroagentsModalController(curAgentState);

  return (
    <ModalBackdrop onClose={onClose}>
      <ModalBody
        width="medium"
        className="max-h-[80vh] flex flex-col items-start"
        testID="microagents-modal"
      >
        <ModalHeader controller={controller} t={t} />

        <AgentWarning isVisible={controller.isAgentReady} t={t} />

        <MicroagentsContent controller={controller} t={t} />
      </ModalBody>
    </ModalBackdrop>
  );
}

function useMicroagentsModalController(curAgentState: AgentState) {
  const [expandedAgents, setExpandedAgents] = useState<Record<string, boolean>>(
    {},
  );
  const { data, isLoading, isError, refetch, isRefetching } =
    useConversationMicroagents();

  const toggleAgent = (agentName: string) => {
    setExpandedAgents((previous) => ({
      ...previous,
      [agentName]: !previous[agentName],
    }));
  };

  return {
    isAgentReady: ![AgentState.LOADING, AgentState.INIT].includes(
      curAgentState,
    ),
    expandedAgents,
    toggleAgent,
    microagents: data,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } as const;
}

function ModalHeader({
  controller,
  t,
}: {
  controller: ReturnType<typeof useMicroagentsModalController>;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="flex flex-col gap-6 w-full">
      <div className="flex items-center justify-between w-full">
        <BaseModalTitle title={t(I18nKey.MICROAGENTS_MODAL$TITLE)} />
        {controller.isAgentReady && (
          <BrandButton
            testId="refresh-microagents"
            type="button"
            variant="primary"
            className="flex items-center gap-2"
            onClick={controller.refetch}
            isDisabled={controller.isLoading || controller.isRefetching}
          >
            <RefreshCw
              size={16}
              className={controller.isRefetching ? "animate-spin" : ""}
            />
            {t(I18nKey.BUTTON$REFRESH)}
          </BrandButton>
        )}
      </div>
    </div>
  );
}

function AgentWarning({
  isVisible,
  t,
}: {
  isVisible: boolean;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (!isVisible) {
    return null;
  }

  return (
    <span className="text-sm text-foreground-secondary">
      {t(I18nKey.MICROAGENTS_MODAL$WARNING)}
    </span>
  );
}

function MicroagentsContent({
  controller,
  t,
}: {
  controller: ReturnType<typeof useMicroagentsModalController>;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="w-full h-[60vh] overflow-auto rounded-md">
      <MicroagentsContentBody controller={controller} t={t} />
    </div>
  );
}

function MicroagentsContentBody({
  controller,
  t,
}: {
  controller: ReturnType<typeof useMicroagentsModalController>;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (!controller.isAgentReady) {
    return <EmptyState message={t(I18nKey.DIFF_VIEWER$WAITING_FOR_RUNTIME)} />;
  }

  if (controller.isLoading) {
    return <LoadingState />;
  }

  if (!controller.microagents || controller.microagents.length === 0) {
    return <EmptyState message={t(I18nKey.CONVERSATION$NO_MICROAGENTS)} />;
  }

  if (controller.isError) {
    return <EmptyState message={t(I18nKey.MICROAGENTS_MODAL$FETCH_ERROR)} />;
  }

  return (
    <div className="p-2 space-y-3">
      {controller.microagents.map((agent: any) => (
        <MicroagentAccordion
          key={agent.name}
          agent={agent}
          isExpanded={controller.expandedAgents[agent.name] || false}
          onToggle={controller.toggleAgent}
          t={t}
        />
      ))}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
      {message}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex justify-center items-center py-8">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-brand-500" />
    </div>
  );
}

function MicroagentAccordion({
  agent,
  isExpanded,
  onToggle,
  t,
}: {
  agent: any;
  isExpanded: boolean;
  onToggle: (name: string) => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const badgeLabel = agent.type === "repo" ? "Repository" : "Knowledge";

  return (
    <div className="rounded-md overflow-hidden">
      <button
        type="button"
        onClick={() => onToggle(agent.name)}
        className="w-full py-3 px-2 text-left flex items-center justify-between hover:bg-background-tertiary transition-colors rounded-lg"
      >
        <div className="flex items-center">
          <h3 className="font-bold text-foreground">{agent.name}</h3>
        </div>
        <div className="flex items-center">
          <span className="px-2 py-1 text-xs rounded-full bg-brand-500/10 text-violet-500 border border-brand-500/20 mr-2">
            {badgeLabel}
          </span>
          <span className="text-foreground-secondary">
            {isExpanded ? (
              <ChevronDown size={18} />
            ) : (
              <ChevronRight size={18} />
            )}
          </span>
        </div>
      </button>

      {isExpanded && <MicroagentDetails agent={agent} t={t} />}
    </div>
  );
}

function MicroagentDetails({
  agent,
  t,
}: {
  agent: any;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="px-2 pb-3 pt-1">
      {agent.triggers?.length ? (
        <TriggerSection triggers={agent.triggers} t={t} />
      ) : null}

      <div className="mt-2">
        <h4 className="text-sm font-semibold text-foreground-secondary mb-2">
          {t(I18nKey.MICROAGENTS_MODAL$CONTENT)}
        </h4>
        <div className="text-sm mt-2 p-3 bg-background-tertiary rounded-md overflow-auto text-foreground-secondary max-h-[400px]">
          <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
            {agent.content || t(I18nKey.MICROAGENTS_MODAL$NO_CONTENT)}
          </pre>
        </div>
      </div>
    </div>
  );
}

function TriggerSection({
  triggers,
  t,
}: {
  triggers: string[];
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="mt-2 mb-3">
      <h4 className="text-sm font-semibold text-foreground-secondary mb-2">
        {t(I18nKey.MICROAGENTS_MODAL$TRIGGERS)}
      </h4>
      <div className="flex flex-wrap gap-1">
        {triggers.map((trigger) => (
          <span
            key={trigger}
            className="px-2 py-1 text-xs rounded-full bg-accent-500/10 text-accent-500 border border-accent-500/20"
          >
            {trigger}
          </span>
        ))}
      </div>
    </div>
  );
}
