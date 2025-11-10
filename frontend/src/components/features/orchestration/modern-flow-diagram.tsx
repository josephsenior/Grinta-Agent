import React, { useCallback, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  Clock,
  ArrowDown,
  ArrowRight,
  Loader2,
  Play,
  Pause,
  RotateCw,
  Maximize2,
} from "lucide-react";
import type { OrchestrationStep } from "#/types/metasop-artifacts";
import {
  formatStepDateTime,
  formatStepTimestamp,
  getRoleMeta,
  getStatusMeta,
  normalizeProgress,
  normalizeStatus,
} from "./modern-flow-utils";

// ============================================================================
// TYPES
// ============================================================================

interface ModernFlowDiagramProps {
  steps: OrchestrationStep[];
  status: string;
  onStepClick?: (step: OrchestrationStep) => void;
  className?: string;
  layout?: "vertical" | "horizontal";
  animated?: boolean;
  showControls?: boolean;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ModernFlowDiagram({
  steps,
  status,
  onStepClick,
  className = "",
  layout = "vertical",
  animated = true,
  showControls = true,
}: ModernFlowDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const handleRefresh = useCallback(() => window.location.reload(), []);
  const {
    hasSteps,
    statusMeta,
    totalSteps,
    selectedStep,
    selectedStepId,
    handleStepSelect,
    clearSelection,
    isPaused,
    togglePause,
    zoom,
    zoomIn,
    zoomOut,
    resetZoom,
    animatedState,
  } = useModernFlowDiagramState({ steps, status, onStepClick, animated });

  if (!hasSteps) {
    return <ModernFlowEmpty className={className} />;
  }

  return (
    <div className={`modern-flow-diagram ${className}`} ref={containerRef}>
      {showControls && (
        <FlowControls
          isPaused={isPaused}
          onTogglePause={togglePause}
          zoom={zoom}
          onZoomOut={zoomOut}
          onZoomIn={zoomIn}
          onResetZoom={resetZoom}
          onRefresh={handleRefresh}
        />
      )}

      <FlowStatusBanner statusMeta={statusMeta} totalSteps={totalSteps} />

      <FlowCanvas
        layout={layout}
        steps={steps}
        zoom={zoom}
        selectedStepId={selectedStepId}
        animated={animatedState}
        onStepSelect={handleStepSelect}
      />

      <StepDetailsSection
        selectedStep={selectedStep}
        onClose={clearSelection}
      />
    </div>
  );
}

function useModernFlowDiagramState({
  steps,
  status,
  onStepClick,
  animated,
}: {
  steps: OrchestrationStep[];
  status: string;
  onStepClick?: (step: OrchestrationStep) => void;
  animated: boolean;
}) {
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [zoom, setZoom] = useState(1);

  const hasSteps = steps.length > 0;
  const statusMeta = useMemo(() => getStatusMeta(status), [status]);
  const totalSteps = steps.length;

  const selectedStep = useMemo(
    () => steps.find((step) => step.id === selectedStepId) ?? null,
    [selectedStepId, steps],
  );

  const handleStepSelect = useCallback(
    (step: OrchestrationStep) => {
      setSelectedStepId(step.id);
      onStepClick?.(step);
    },
    [onStepClick],
  );

  const clearSelection = useCallback(() => setSelectedStepId(null), []);
  const togglePause = useCallback(() => setIsPaused((prev) => !prev), []);

  const zoomIn = useCallback(
    () =>
      setZoom((value) => Math.min(2, Math.round((value + 0.1) * 100) / 100)),
    [],
  );

  const zoomOut = useCallback(
    () =>
      setZoom((value) => Math.max(0.5, Math.round((value - 0.1) * 100) / 100)),
    [],
  );

  const resetZoom = useCallback(() => setZoom(1), []);

  const animatedState = animated && !isPaused;

  return {
    hasSteps,
    statusMeta,
    totalSteps,
    selectedStep,
    selectedStepId,
    handleStepSelect,
    clearSelection,
    isPaused,
    togglePause,
    zoom,
    zoomIn,
    zoomOut,
    resetZoom,
    animatedState,
  };
}

function ModernFlowEmpty({ className }: { className: string }) {
  return (
    <div className={`modern-flow-empty ${className}`}>
      <div className="text-center py-12">
        <Loader2 className="w-12 h-12 text-brand-400 animate-spin mx-auto mb-3" />
        <p className="text-sm text-neutral-400">
          Waiting for orchestration to start...
        </p>
      </div>
    </div>
  );
}

function FlowControls({
  isPaused,
  onTogglePause,
  zoom,
  onZoomOut,
  onZoomIn,
  onResetZoom,
  onRefresh,
}: {
  isPaused: boolean;
  onTogglePause: () => void;
  zoom: number;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onResetZoom: () => void;
  onRefresh: () => void;
}) {
  const zoomPercentage = Math.round(zoom * 100);

  return (
    <div className="flow-controls">
      <button
        onClick={onTogglePause}
        className="flow-control-btn"
        title={isPaused ? "Resume" : "Pause"}
      >
        {isPaused ? (
          <Play className="w-4 h-4" />
        ) : (
          <Pause className="w-4 h-4" />
        )}
      </button>
      <button onClick={onZoomOut} className="flow-control-btn" title="Zoom Out">
        -
      </button>
      <span className="text-xs text-neutral-400 mx-2">{zoomPercentage}%</span>
      <button onClick={onZoomIn} className="flow-control-btn" title="Zoom In">
        +
      </button>
      <button
        onClick={onResetZoom}
        className="flow-control-btn"
        title="Reset Zoom"
      >
        <Maximize2 className="w-4 h-4" />
      </button>
      <button onClick={onRefresh} className="flow-control-btn" title="Refresh">
        <RotateCw className="w-4 h-4" />
      </button>
    </div>
  );
}

function FlowStatusBanner({
  statusMeta,
  totalSteps,
}: {
  statusMeta: ReturnType<typeof getStatusMeta>;
  totalSteps: number;
}) {
  const StatusIcon = statusMeta.icon;
  const message = getStatusBannerLabel(statusMeta);

  return (
    <div className={`flow-status-banner ${statusMeta.bannerClass}`}>
      <StatusIcon
        className={`w-4 h-4 ${statusMeta.isInProgress ? "animate-spin" : ""}`}
      />
      <span className="text-sm font-medium">{message}</span>
      <span className="text-xs text-neutral-400 ml-2">
        {totalSteps} {totalSteps === 1 ? "step" : "steps"}
      </span>
    </div>
  );
}

function getStatusBannerLabel(meta: ReturnType<typeof getStatusMeta>): string {
  if (meta.isInProgress) {
    return "Orchestration in Progress";
  }

  if (meta.isComplete) {
    return "Orchestration Complete";
  }

  if (meta.isBlocked) {
    return "Orchestration Failed";
  }

  return `Status: ${meta.label}`;
}

function FlowCanvas({
  layout,
  steps,
  selectedStepId,
  animated,
  zoom,
  onStepSelect,
}: {
  layout: "vertical" | "horizontal";
  steps: OrchestrationStep[];
  selectedStepId: string | null;
  animated: boolean;
  zoom: number;
  onStepSelect: (step: OrchestrationStep) => void;
}) {
  return (
    <div
      className="flow-canvas"
      style={{
        transform: `scale(${zoom})`,
        transformOrigin: "top center",
      }}
    >
      {layout === "vertical" ? (
        <VerticalFlow
          steps={steps}
          selectedStepId={selectedStepId}
          onStepClick={onStepSelect}
          animated={animated}
        />
      ) : (
        <HorizontalFlow
          steps={steps}
          selectedStepId={selectedStepId}
          onStepClick={onStepSelect}
          animated={animated}
        />
      )}
    </div>
  );
}

function StepDetailsSection({
  selectedStep,
  onClose,
}: {
  selectedStep: OrchestrationStep | null;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {selectedStep && (
        <StepDetailsPanel step={selectedStep} onClose={onClose} />
      )}
    </AnimatePresence>
  );
}

// ============================================================================
// VERTICAL FLOW LAYOUT
// ============================================================================

function VerticalFlow({
  steps,
  selectedStepId,
  onStepClick,
  animated,
}: {
  steps: OrchestrationStep[];
  selectedStepId: string | null;
  onStepClick: (step: OrchestrationStep) => void;
  animated: boolean;
}) {
  return (
    <div className="flow-vertical">
      {steps.map((step, index) => (
        <React.Fragment key={step.id}>
          <FlowStepNode
            step={step}
            index={index}
            isSelected={selectedStepId === step.id}
            onClick={() => onStepClick(step)}
            animated={animated}
          />
          {index < steps.length - 1 && (
            <FlowConnector
              type="vertical"
              fromStep={step}
              toStep={steps[index + 1]}
              animated={animated}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ============================================================================
// HORIZONTAL FLOW LAYOUT
// ============================================================================

function HorizontalFlow({
  steps,
  selectedStepId,
  onStepClick,
  animated,
}: {
  steps: OrchestrationStep[];
  selectedStepId: string | null;
  onStepClick: (step: OrchestrationStep) => void;
  animated: boolean;
}) {
  return (
    <div className="flow-horizontal">
      {steps.map((step, index) => (
        <React.Fragment key={step.id}>
          <FlowStepNode
            step={step}
            index={index}
            isSelected={selectedStepId === step.id}
            onClick={() => onStepClick(step)}
            animated={animated}
          />
          {index < steps.length - 1 && (
            <FlowConnector
              type="horizontal"
              fromStep={step}
              toStep={steps[index + 1]}
              animated={animated}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ============================================================================
// FLOW STEP NODE
// ============================================================================

function FlowStepNode({
  step,
  index,
  isSelected,
  onClick,
  animated,
}: {
  step: OrchestrationStep;
  index: number;
  isSelected: boolean;
  onClick: () => void;
  animated: boolean;
}) {
  const meta = React.useMemo(() => createFlowStepMeta(step), [step]);
  const RoleIcon = meta.role.icon;
  const StatusIcon = meta.status.icon;

  return (
    <motion.div
      initial={animated ? { opacity: 0, scale: 0.8, y: 20 } : undefined}
      animate={animated ? { opacity: 1, scale: 1, y: 0 } : undefined}
      transition={{
        delay: index * 0.1,
        type: "spring",
        stiffness: 200,
        damping: 20,
      }}
      className={`flow-step-node ${meta.status.nodeClass} ${isSelected ? "flow-step-selected" : ""}`}
      onClick={onClick}
    >
      {/* Status Indicator */}
      <div className="flow-step-status">
        <StatusIcon className={meta.status.iconClass} />
      </div>

      {/* Role Icon */}
      <div className={`flow-step-icon ${meta.role.badgeClass}`}>
        <RoleIcon className="w-5 h-5" />
      </div>

      {/* Content */}
      <div className="flow-step-content">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-brand-400">
            Step {index + 1}
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-black/30 capitalize">
            {meta.role.label}
          </span>
        </div>
        <h4 className="text-sm font-medium text-white mb-1">{step.title}</h4>
        {step.description && (
          <p className="text-xs text-neutral-400 line-clamp-2">
            {step.description}
          </p>
        )}

        <FlowStepProgress
          progress={meta.progress}
          isActive={meta.status.isInProgress}
        />
        <FlowStepTimestamps
          startedAt={meta.startedAt}
          completedAt={meta.completedAt}
        />
        <FlowStepError error={step.error} />
      </div>

      <FlowStepArtifactBadge hasArtifact={Boolean(step.artifact)} />

      {/* Glow Effect for Active Step */}
      <FlowStepGlow isActive={meta.status.isInProgress} />
    </motion.div>
  );
}

function createFlowStepMeta(step: OrchestrationStep) {
  const status = getStatusMeta(step.status);
  const role = getRoleMeta(step.role);
  const progress = normalizeProgress(
    (step as Record<string, unknown>).progress,
  );
  const startedAt = formatStepTimestamp(step.started_at);
  const completedAt = formatStepTimestamp(step.completed_at);

  return {
    status: {
      ...status,
      iconClass: getStatusIconClass(status),
    },
    role,
    progress,
    startedAt,
    completedAt,
  } as const;
}

function getStatusIconClass(statusMeta: ReturnType<typeof getStatusMeta>) {
  if (statusMeta.isInProgress) {
    return "w-4 h-4 text-brand-400 animate-spin";
  }
  if (statusMeta.isComplete) {
    return "w-4 h-4 text-green-400";
  }
  if (statusMeta.isBlocked) {
    return "w-4 h-4 text-red-400";
  }
  return "w-4 h-4 text-neutral-400";
}

function FlowStepProgress({
  progress,
  isActive,
}: {
  progress: number | undefined;
  isActive: boolean;
}) {
  if (!isActive || progress === undefined) {
    return null;
  }

  return (
    <div className="mt-2">
      <div className="w-full bg-neutral-800 rounded-full h-1.5">
        <motion.div
          className="bg-brand-500 h-1.5 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
      <p className="text-xs text-neutral-500 mt-1">{progress}% complete</p>
    </div>
  );
}

function FlowStepTimestamps({
  startedAt,
  completedAt,
}: {
  startedAt?: string | null;
  completedAt?: string | null;
}) {
  if (!startedAt && !completedAt) {
    return null;
  }

  return (
    <div className="flex items-center gap-3 mt-2 text-xs text-neutral-500">
      {startedAt && <span>Started: {startedAt}</span>}
      {completedAt && <span>Completed: {completedAt}</span>}
    </div>
  );
}

function FlowStepError({ error }: { error?: string | null }) {
  if (!error) {
    return null;
  }

  return (
    <div className="mt-2 bg-red-500/10 border border-red-500/20 rounded p-2">
      <p className="text-xs text-red-300">{error}</p>
    </div>
  );
}

function FlowStepArtifactBadge({ hasArtifact }: { hasArtifact: boolean }) {
  if (!hasArtifact) {
    return null;
  }

  return (
    <div className="flow-step-artifact-badge">
      <CheckCircle className="w-3 h-3 text-green-400" />
      <span className="text-xs">Artifact</span>
    </div>
  );
}

function FlowStepGlow({ isActive }: { isActive: boolean }) {
  if (!isActive) {
    return null;
  }

  return (
    <motion.div
      className="flow-step-glow"
      animate={{
        opacity: [0.3, 0.6, 0.3],
        scale: [1, 1.05, 1],
      }}
      transition={{
        duration: 2,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    />
  );
}

// ============================================================================
// FLOW CONNECTOR
// ============================================================================

function FlowConnector({
  type,
  fromStep,
  toStep,
  animated,
}: {
  type: "vertical" | "horizontal";
  fromStep: OrchestrationStep;
  toStep: OrchestrationStep;
  animated: boolean;
}) {
  const fromStatus = normalizeStatus(fromStep.status);
  const toStatus = normalizeStatus(toStep.status);
  const isActive = fromStatus === "complete" && toStatus !== "pending";
  const isAnimated = fromStatus === "in_progress" || toStatus === "in_progress";

  return (
    <div className={`flow-connector flow-connector-${type}`}>
      <div
        className={`flow-connector-line ${isActive ? "flow-connector-active" : ""}`}
      >
        {isAnimated && animated && (
          <motion.div
            className="flow-connector-pulse"
            animate={{
              [type === "vertical" ? "y" : "x"]: ["0%", "100%"],
              opacity: [0, 1, 0],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "linear",
            }}
          />
        )}
      </div>
      <div className="flow-connector-arrow">
        {type === "vertical" ? (
          <ArrowDown className="w-4 h-4" />
        ) : (
          <ArrowRight className="w-4 h-4" />
        )}
      </div>
    </div>
  );
}

// ============================================================================
// STEP DETAILS PANEL
// ============================================================================

function StepDetailsPanel({
  step,
  onClose,
}: {
  step: OrchestrationStep;
  onClose: () => void;
}) {
  const roleMeta = getRoleMeta(step.role);
  const statusMeta = getStatusMeta(step.status);
  const progressValue = normalizeProgress(
    (step as Record<string, unknown>).progress,
  );
  const progress = progressValue as number | undefined;
  const startedAt = formatStepDateTime(step.started_at);
  const completedAt = formatStepDateTime(step.completed_at);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flow-details-overlay"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className={`flow-details-panel ${roleMeta.panelClass}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flow-details-header">
          <div>
            <h3 className="text-lg font-semibold text-white">{step.title}</h3>
            <p className="text-sm text-neutral-400 capitalize">
              {roleMeta.label} • {statusMeta.label}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flow-details-content">
          {step.description && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-neutral-300 mb-2">
                Description
              </h4>
              <p className="text-sm text-neutral-400">{step.description}</p>
            </div>
          )}

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            {startedAt && (
              <div>
                <p className="text-xs text-neutral-500 mb-1">Started</p>
                <p className="text-sm text-neutral-300">{startedAt}</p>
              </div>
            )}
            {completedAt && (
              <div>
                <p className="text-xs text-neutral-500 mb-1">Completed</p>
                <p className="text-sm text-neutral-300">{completedAt}</p>
              </div>
            )}
          </div>

          {/* Progress */}
          {
            (progress !== undefined && typeof progress === "number" && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-neutral-300">
                    Progress
                  </h4>
                  <span className="text-sm text-brand-400">
                    {progress as number}%
                  </span>
                </div>
                <div className="w-full bg-neutral-800 rounded-full h-2">
                  <div
                    className="bg-brand-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )) as any
          }

          {/* Error */}
          {step.error && (
            <div className="mb-4 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <h4 className="text-sm font-medium text-red-300 mb-2">Error</h4>
              <p className="text-sm text-red-400">{step.error}</p>
            </div>
          )}

          {/* Artifact */}
          {step.artifact && (
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <h4 className="text-sm font-medium text-green-300">
                  Artifact Available
                </h4>
              </div>
              <p className="text-xs text-neutral-400">
                This step has generated an artifact. View it in the
                orchestration panel.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flow-details-footer">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ============================================================================
// COMPACT FLOW VIEW (for smaller spaces)
// ============================================================================

export function CompactFlowView({
  steps,
  status,
  onStepClick,
  className = "",
}: {
  steps: OrchestrationStep[];
  status: string;
  onStepClick?: (step: OrchestrationStep) => void;
  className?: string;
}) {
  const hasSteps = steps && steps.length > 0;
  const statusMeta = useMemo(() => getStatusMeta(status), [status]);
  const StatusIcon = statusMeta.icon;

  if (!hasSteps) {
    return (
      <div className={`compact-flow-empty ${className}`}>
        <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className={`compact-flow-view ${className}`}>
      <div className="compact-flow-steps">
        {steps.map((step, index) => (
          <CompactStepBadge
            key={step.id}
            step={step}
            index={index}
            total={steps.length}
            onClick={() => onStepClick?.(step)}
          />
        ))}
      </div>
      <div className={`compact-flow-status ${statusMeta.bannerClass}`}>
        <StatusIcon
          className={`w-3 h-3 ${statusMeta.isInProgress ? "animate-spin" : ""}`}
        />
        <span className="text-xs font-medium ml-1">{statusMeta.label}</span>
      </div>
    </div>
  );
}

function CompactStepBadge({
  step,
  index,
  total,
  onClick,
}: {
  step: OrchestrationStep;
  index: number;
  total: number;
  onClick: () => void;
}) {
  const roleMeta = getRoleMeta(step.role);
  const RoleIcon = roleMeta.icon;
  const statusMeta = getStatusMeta(step.status);
  const isActive = statusMeta.isInProgress;
  const { isComplete } = statusMeta;

  return (
    <div className="compact-step-wrapper">
      <motion.button
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: index * 0.05 }}
        className={`compact-step-badge ${statusMeta.nodeClass}`}
        onClick={onClick}
        title={`${step.title} (${statusMeta.label})`}
      >
        <RoleIcon className="w-4 h-4" />
        {isActive && (
          <motion.div
            className="compact-step-pulse"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.5, 0, 0.5],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        )}
        {isComplete && (
          <CheckCircle className="w-3 h-3 text-green-400 absolute -top-1 -right-1" />
        )}
      </motion.button>
      {index < total - 1 && (
        <div className="compact-step-connector">
          <div
            className={`w-full h-0.5 ${isComplete ? "bg-green-500/50" : "bg-neutral-700"}`}
          />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// TIMELINE VIEW (alternative visualization)
// ============================================================================

export function TimelineView({
  steps,
  onStepClick,
  className = "",
}: {
  steps: OrchestrationStep[];
  onStepClick?: (step: OrchestrationStep) => void;
  className?: string;
}) {
  const hasSteps = steps && steps.length > 0;

  if (!hasSteps) {
    return (
      <div className={`timeline-empty ${className}`}>
        <p className="text-sm text-neutral-400">No steps yet</p>
      </div>
    );
  }

  return (
    <div className={`timeline-view ${className}`}>
      {steps.map((step, index) => (
        <TimelineItem
          key={step.id}
          step={step}
          index={index}
          isLast={index === steps.length - 1}
          onClick={() => onStepClick?.(step)}
        />
      ))}
    </div>
  );
}

function TimelineItem({
  step,
  index,
  isLast,
  onClick,
}: {
  step: OrchestrationStep;
  index: number;
  isLast: boolean;
  onClick: () => void;
}) {
  const roleMeta = getRoleMeta(step.role);
  const statusMeta = getStatusMeta(step.status);
  const startedAt = formatStepDateTime(step.started_at);

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className="timeline-item"
      onClick={onClick}
    >
      <div className="timeline-marker">
        <div className={`timeline-dot ${roleMeta.badgeClass}`}>
          {statusMeta.isComplete && (
            <CheckCircle className="w-3 h-3 text-green-400" />
          )}
          {statusMeta.isInProgress && (
            <Loader2 className="w-3 h-3 text-brand-400 animate-spin" />
          )}
          {!statusMeta.isComplete && !statusMeta.isInProgress && (
            <Clock className="w-3 h-3 text-neutral-400" />
          )}
        </div>
        {!isLast && <div className="timeline-line" />}
      </div>
      <div className="timeline-content">
        <div className="timeline-header">
          <span className="text-xs text-neutral-500">
            Step {index + 1} • {roleMeta.label}
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded ${roleMeta.badgeClass}`}
          >
            {statusMeta.label}
          </span>
        </div>
        <h4 className="text-sm font-medium text-white mb-1">{step.title}</h4>
        {step.description && (
          <p className="text-xs text-neutral-400">{step.description}</p>
        )}
        {startedAt && (
          <p className="text-xs text-neutral-500 mt-1">{startedAt}</p>
        )}
      </div>
    </motion.div>
  );
}
