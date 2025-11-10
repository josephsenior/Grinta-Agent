/**
 * Orchestration Diagram Panel
 */
import React, { useEffect, useMemo, useState } from "react";
import { MermaidDiagramViewer } from "./mermaid-diagram-viewer";
import { useMetaSOPOrchestration } from "#/hooks/use-metasop-orchestration";
import { applyAllNodeEnhancements } from "#/utils/diagram-node-enhancements";
import { CleanVisualAdapter } from "./clean-visualizations";
import { ModernFlowDiagram } from "./modern-flow-diagram";
import type { ParsedArtifact } from "#/types/metasop-artifacts";
import {
  buildOrchestrationDiagramState,
  convertToOrchestrationStep,
  DiagramTab,
} from "./orchestration-diagram-utils";

interface OrchestrationDiagramPanelProps {
  className?: string;
  onNavigateToStep?: (stepId: string) => void;
  onClose?: () => void;
}

export function OrchestrationDiagramPanel({
  className = "",
  onNavigateToStep,
  onClose,
}: OrchestrationDiagramPanelProps) {
  const [activeTab, setActiveTab] = useState<DiagramTab>("flow");
  const orchestration = useMetaSOPOrchestration();

  const diagramState = useMemo(
    () =>
      buildOrchestrationDiagramState(
        orchestration.steps,
        orchestration.hasSteps,
      ),
    [orchestration.steps, orchestration.hasSteps],
  );

  useActiveTabFallback(diagramState.tabs, activeTab, setActiveTab);
  useMermaidNodeEnhancements(orchestration.steps, activeTab, onNavigateToStep);

  const enrichedSteps = useMemo(
    () =>
      (orchestration.steps ?? []).map((step) => ({
        raw: step,
        orchestration: convertToOrchestrationStep(step),
      })),
    [orchestration.steps],
  );

  const orchestrationSteps = useMemo(
    () => enrichedSteps.map((entry) => entry.orchestration),
    [enrichedSteps],
  );

  const contentProps: DiagramContentProps = {
    activeTab,
    tabs: diagramState.tabs,
    onTabChange: setActiveTab,
    diagramState,
    orchestration,
    enrichedSteps,
    orchestrationSteps,
    onNavigateToStep,
  };

  return (
    <div
      className={`orchestration-diagram-panel flex flex-col h-full bg-background-secondary rounded-lg border border-border ${className}`}
    >
      <OrchestrationDiagramHeader
        onClose={onClose}
        isOrchestrating={orchestration.isOrchestrating}
        stepCount={orchestration.steps?.length ?? 0}
      />

      <PassToCodeActSection
        hasSteps={orchestration.hasSteps}
        steps={orchestration.steps}
      />

      <DiagramTabs
        tabs={diagramState.tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <DiagramContent {...contentProps} />
    </div>
  );
}

function OrchestrationDiagramHeader({
  onClose,
  isOrchestrating,
  stepCount,
}: {
  onClose?: () => void;
  isOrchestrating: boolean;
  stepCount: number;
}) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-border bg-background-secondary">
      <div className="flex items-center gap-3">
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-background-tertiary/70 transition-colors"
            title="Close panel"
          >
            <svg
              className="w-5 h-5 text-foreground-secondary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
        )}
        <svg
          className="w-5 h-5 text-primary-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <h3 className="text-lg font-semibold text-foreground">
          Orchestration Diagrams
        </h3>
        {isOrchestrating && (
          <span className="ml-2 px-2 py-1 text-xs bg-blue-900 text-blue-200 rounded-full animate-pulse">
            Live
          </span>
        )}
      </div>
      <div className="text-sm text-foreground-secondary">
        {stepCount > 0 ? `${stepCount} steps` : "Waiting for orchestration..."}
      </div>
    </div>
  );
}

function PassToCodeActSection({
  hasSteps,
  steps,
}: {
  hasSteps: boolean;
  steps: ReturnType<typeof useMetaSOPOrchestration>["steps"];
}) {
  if (!hasSteps) {
    return null;
  }

  return (
    <div className="px-4 pt-4 pb-2">
      <button
        onClick={() => {
          console.log("Pass to CodeAct clicked with steps:", steps);
        }}
        className="w-full bg-gradient-to-r from-emerald-500 to-green-600 text-white font-semibold py-3 px-4 rounded-lg hover:from-emerald-600 hover:to-green-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        Pass to CodeAct
      </button>
    </div>
  );
}

function DiagramTabs({
  tabs,
  activeTab,
  onTabChange,
}: {
  tabs: Array<{ id: DiagramTab; label: string }>;
  activeTab: DiagramTab;
  onTabChange: (tab: DiagramTab) => void;
}) {
  return (
    <div className="flex gap-2 p-2 border-b border-border overflow-x-auto bg-background-secondary">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
            activeTab === tab.id
              ? "bg-primary-500 text-white shadow-md"
              : "bg-background-tertiary/70 text-foreground-secondary hover:bg-background-tertiary"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

interface DiagramContentProps {
  activeTab: DiagramTab;
  tabs: Array<{ id: DiagramTab; label: string }>;
  onTabChange: (tab: DiagramTab) => void;
  diagramState: ReturnType<typeof buildOrchestrationDiagramState>;
  orchestration: ReturnType<typeof useMetaSOPOrchestration>;
  enrichedSteps: Array<{
    raw: any;
    orchestration: ReturnType<typeof convertToOrchestrationStep>;
  }>;
  orchestrationSteps: ReturnType<typeof convertToOrchestrationStep>[];
  onNavigateToStep?: (stepId: string) => void;
}

function DiagramContent({
  activeTab,
  diagramState,
  orchestration,
  enrichedSteps,
  orchestrationSteps,
  onNavigateToStep,
}: DiagramContentProps) {
  const renderers = useMemo(
    () =>
      buildTabRenderers({
        diagramState,
        orchestration,
        enrichedSteps,
        orchestrationSteps,
        onNavigateToStep,
      }),
    [
      diagramState,
      orchestration,
      enrichedSteps,
      orchestrationSteps,
      onNavigateToStep,
    ],
  );

  const renderer = renderers[activeTab];
  return (
    <div className="flex-1 overflow-auto p-4 bg-background-secondary">
      {renderer()}
    </div>
  );
}

function buildTabRenderers({
  diagramState,
  orchestration,
  enrichedSteps,
  orchestrationSteps,
  onNavigateToStep,
}: {
  diagramState: ReturnType<typeof buildOrchestrationDiagramState>;
  orchestration: ReturnType<typeof useMetaSOPOrchestration>;
  enrichedSteps: Array<{
    raw: any;
    orchestration: ReturnType<typeof convertToOrchestrationStep>;
  }>;
  orchestrationSteps: ReturnType<typeof convertToOrchestrationStep>[];
  onNavigateToStep?: (stepId: string) => void;
}): Record<DiagramTab, () => React.ReactNode> {
  return {
    flow: () => (
      <FlowTab
        steps={orchestrationSteps}
        rawSteps={orchestration.steps}
        isOrchestrating={orchestration.isOrchestrating}
        onNavigateToStep={onNavigateToStep}
      />
    ),
    agents: () => (
      <AgentsTab
        enrichedSteps={enrichedSteps}
        hasSteps={orchestration.steps?.length ?? 0}
      />
    ),
    overview: () => (
      <OverviewTab
        diagram={diagramState.overviewDiagram}
        steps={orchestration.steps}
        isOrchestrating={orchestration.isOrchestrating}
        onNavigateToStep={onNavigateToStep}
      />
    ),
    architecture: () => (
      <SimpleDiagramTab
        title="System Architecture"
        diagram={diagramState.architectureDiagram}
        emptyState="Waiting for architect step to complete..."
        exportName="system-architecture"
      />
    ),
    api: () => (
      <SimpleDiagramTab
        title="API Sequence Flow"
        diagram={diagramState.apiDiagram}
        emptyState="No API specifications available"
        exportName="api-sequence"
      />
    ),
    ui: () => (
      <SimpleDiagramTab
        title="UI Component Tree"
        diagram={diagramState.uiDiagram}
        emptyState="No UI design specifications available"
        exportName="ui-components"
      />
    ),
    database: () => (
      <SimpleDiagramTab
        title="Database Schema (ER Diagram)"
        diagram={diagramState.databaseDiagram}
        emptyState="No database schema available"
        exportName="database-schema"
      />
    ),
    timeline: () => (
      <SimpleDiagramTab
        title="Project Timeline (Gantt Chart)"
        diagram={diagramState.timelineDiagram}
        emptyState="No timeline available"
        exportName="project-timeline"
      />
    ),
    classes: () => (
      <SimpleDiagramTab
        title="Class Diagram"
        diagram={diagramState.classDiagram}
        emptyState="No class diagram available"
        exportName="class-diagram"
      />
    ),
    raw: () => (
      <RawJsonTab
        orchestrationSteps={orchestrationSteps}
        isOrchestrating={orchestration.isOrchestrating}
      />
    ),
  };
}

function FlowTab({
  steps,
  rawSteps,
  isOrchestrating,
  onNavigateToStep,
}: {
  steps: ReturnType<typeof convertToOrchestrationStep>[];
  rawSteps?: ReturnType<typeof useMetaSOPOrchestration>["steps"];
  isOrchestrating: boolean;
  onNavigateToStep?: (stepId: string) => void;
}) {
  const hasSteps = (rawSteps?.length ?? 0) > 0;
  return (
    <div className="h-full">
      <h4 className="text-sm font-semibold text-foreground-secondary mb-4">
        Modern Orchestration Flow
        {isOrchestrating && (
          <span className="ml-2 text-xs text-violet-500">● Live Updates</span>
        )}
      </h4>
      {hasSteps ? (
        <ModernFlowDiagram
          steps={steps}
          status={isOrchestrating ? "in_progress" : "idle"}
          onStepClick={(step) => onNavigateToStep?.(step.id)}
          layout="vertical"
          animated
          showControls
        />
      ) : (
        <TabEmptyState
          title="No orchestration flow available"
          subtitle="Enable MetaSOP and send a message to start orchestration"
        />
      )}
    </div>
  );
}

function AgentsTab({
  enrichedSteps,
  hasSteps,
}: {
  enrichedSteps: Array<{
    raw: any;
    orchestration: ReturnType<typeof convertToOrchestrationStep>;
  }>;
  hasSteps: number;
}) {
  if (!hasSteps) {
    return (
      <TabEmptyState
        title="No agent details available"
        subtitle="Agents will display their work here as they complete tasks"
      />
    );
  }

  const artifactSteps = enrichedSteps.filter(({ raw }) => raw.artifact);
  if (artifactSteps.length === 0) {
    return (
      <TabEmptyState
        title="Waiting for agents to generate artifacts..."
        subtitle="Artifacts will be displayed as soon as they are available"
      />
    );
  }

  return (
    <div className="space-y-6">
      {artifactSteps.map(({ raw, orchestration }) => (
        <CleanVisualAdapter
          key={raw.step_id ?? raw.id}
          artifact={orchestration.artifact as ParsedArtifact}
          animated
          onInteraction={(action, data) => {
            console.log("Interaction:", action, data);
          }}
        />
      ))}
    </div>
  );
}

function OverviewTab({
  diagram,
  steps,
  isOrchestrating,
  onNavigateToStep,
}: {
  diagram?: string;
  steps?: ReturnType<typeof useMetaSOPOrchestration>["steps"];
  isOrchestrating: boolean;
  onNavigateToStep?: (stepId: string) => void;
}) {
  const hasSteps = (steps?.length ?? 0) > 0;
  if (!diagram || !hasSteps) {
    return (
      <TabEmptyState
        title="No orchestration data available"
        subtitle="Enable SOP and send a message to start orchestration"
      />
    );
  }

  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground-secondary mb-4">
        Orchestration Flow
        {isOrchestrating && (
          <span className="ml-2 text-xs text-violet-500">● In Progress</span>
        )}
      </h4>
      <MermaidDiagramViewer
        diagram={diagram}
        onNodeClick={onNavigateToStep}
        exportFilename="orchestration-overview"
      />
    </div>
  );
}

function SimpleDiagramTab({
  title,
  diagram,
  emptyState,
  exportName,
}: {
  title: string;
  diagram?: string;
  emptyState: string;
  exportName: string;
}) {
  if (!diagram) {
    return (
      <div className="text-center text-foreground-secondary py-8 bg-background-secondary">
        {emptyState}
      </div>
    );
  }

  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground-secondary mb-4">
        {title}
      </h4>
      <MermaidDiagramViewer diagram={diagram} exportFilename={exportName} />
    </div>
  );
}

function RawJsonTab({
  orchestrationSteps,
  isOrchestrating,
}: {
  orchestrationSteps: ReturnType<typeof convertToOrchestrationStep>[];
  isOrchestrating: boolean;
}) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground-secondary mb-4">
        Raw JSON Data
      </h4>
      <div className="space-y-4">
        {(orchestrationSteps ?? []).map((step) => (
          <div
            key={step.id}
            className="bg-white dark:bg-background-secondary rounded-lg p-4 border border-border dark:border-border"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-foreground">{step.role}</span>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  step.status === "success"
                    ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                    : step.status === "running"
                      ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                      : "bg-background-tertiary text-foreground-secondary"
                }`}
              >
                {step.status}
              </span>
            </div>
            {step.artifact
              ? (() => {
                  const artifactJson = JSON.stringify(step.artifact, null, 2);
                  return (
                    <pre className="text-xs text-foreground-secondary/70 dark:text-foreground-secondary overflow-auto max-h-64 bg-background-tertiary p-2 rounded">
                      {artifactJson}
                    </pre>
                  );
                })()
              : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function TabEmptyState({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-foreground-secondary py-12 bg-background-secondary">
      <svg
        className="w-16 h-16 mb-4 opacity-50"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
      <p className="text-sm">{title}</p>
      <p className="text-xs mt-2 opacity-70">{subtitle}</p>
    </div>
  );
}

function useActiveTabFallback(
  tabs: Array<{ id: DiagramTab; label: string }>,
  activeTab: DiagramTab,
  setActiveTab: (tab: DiagramTab) => void,
) {
  useEffect(() => {
    if (tabs.length > 0 && !tabs.some((tab) => tab.id === activeTab)) {
      setActiveTab(tabs[0].id);
    }
  }, [tabs, activeTab, setActiveTab]);
}

function useMermaidNodeEnhancements(
  steps: ReturnType<typeof useMetaSOPOrchestration>["steps"],
  activeTab: DiagramTab,
  onNavigateToStep?: (stepId: string) => void,
) {
  useEffect(() => {
    const applyEnhancements = () => {
      const svgElement = document.querySelector(
        ".mermaid-diagram-container svg",
      );
      if (svgElement && (steps?.length ?? 0) > 0) {
        applyAllNodeEnhancements(
          svgElement as SVGElement,
          steps,
          onNavigateToStep,
        );
      }
    };

    // Delay to ensure diagram is fully rendered
    const timeoutId = setTimeout(applyEnhancements, 200);
    return () => clearTimeout(timeoutId);
  }, [steps, activeTab, onNavigateToStep]);
}
