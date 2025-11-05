/**
 * Modern Flow Diagram
 * 
 * Custom node-based visualization for MetaSOP orchestration flow
 * Shows real-time agent collaboration and progress
 */

import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  Settings,
  Code,
  TestTube,
  CheckCircle,
  Clock,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  Loader2,
  Play,
  Pause,
  RotateCw,
  Maximize2,
} from "lucide-react";
import type { OrchestrationStep, AgentRole } from "#/types/metasop-artifacts";

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

interface FlowNode {
  id: string;
  step: OrchestrationStep;
  position: { x: number; y: number };
  size: { width: number; height: number };
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
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [zoom, setZoom] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  const hasSteps = steps && steps.length > 0;

  if (!hasSteps) {
    return (
      <div className={`modern-flow-empty ${className}`}>
        <div className="text-center py-12">
          <Loader2 className="w-12 h-12 text-brand-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-neutral-400">Waiting for orchestration to start...</p>
        </div>
      </div>
    );
  }

  const isRunning = status === "running" || status === "in_progress";
  const isComplete = status === "complete" || status === "completed";
  const hasError = status === "error" || status === "failed";

  return (
    <div className={`modern-flow-diagram ${className}`} ref={containerRef}>
      {/* Controls */}
      {showControls && (
        <div className="flow-controls">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className="flow-control-btn"
            title={isPaused ? "Resume" : "Pause"}
          >
            {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
            className="flow-control-btn"
            title="Zoom Out"
          >
            -
          </button>
          <span className="text-xs text-neutral-400 mx-2">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom(Math.min(2, zoom + 0.1))}
            className="flow-control-btn"
            title="Zoom In"
          >
            +
          </button>
          <button
            onClick={() => setZoom(1)}
            className="flow-control-btn"
            title="Reset Zoom"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => window.location.reload()}
            className="flow-control-btn"
            title="Refresh"
          >
            <RotateCw className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Status Banner */}
      <div className={`flow-status-banner ${getStatusClass(status)}`}>
        {isRunning && <Loader2 className="w-4 h-4 animate-spin" />}
        {isComplete && <CheckCircle className="w-4 h-4" />}
        {hasError && <AlertTriangle className="w-4 h-4" />}
        <span className="text-sm font-medium">
          {isRunning && "Orchestration in Progress"}
          {isComplete && "Orchestration Complete"}
          {hasError && "Orchestration Failed"}
          {!isRunning && !isComplete && !hasError && `Status: ${status}`}
        </span>
        <span className="text-xs text-neutral-400 ml-2">
          {steps.length} {steps.length === 1 ? "step" : "steps"}
        </span>
      </div>

      {/* Flow Canvas */}
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
            selectedStep={selectedStep}
            onStepClick={(step) => {
              setSelectedStep(step.id);
              onStepClick?.(step);
            }}
            animated={animated && !isPaused}
          />
        ) : (
          <HorizontalFlow
            steps={steps}
            selectedStep={selectedStep}
            onStepClick={(step) => {
              setSelectedStep(step.id);
              onStepClick?.(step);
            }}
            animated={animated && !isPaused}
          />
        )}
      </div>

      {/* Step Details Panel */}
      <AnimatePresence>
        {selectedStep && (
          <StepDetailsPanel
            step={steps.find((s) => s.id === selectedStep)!}
            onClose={() => setSelectedStep(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// VERTICAL FLOW LAYOUT
// ============================================================================

function VerticalFlow({
  steps,
  selectedStep,
  onStepClick,
  animated,
}: {
  steps: OrchestrationStep[];
  selectedStep: string | null;
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
            isSelected={selectedStep === step.id}
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
  selectedStep,
  onStepClick,
  animated,
}: {
  steps: OrchestrationStep[];
  selectedStep: string | null;
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
            isSelected={selectedStep === step.id}
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
  const statusColors = {
    pending: "bg-neutral-500/10 border-neutral-500/30 text-neutral-400",
    in_progress: "bg-brand-500/20 border-brand-500/50 text-brand-300",
    complete: "bg-green-500/20 border-green-500/50 text-green-300",
    blocked: "bg-red-500/20 border-red-500/50 text-red-300",
  };

  const roleIcons = {
    product_manager: User,
    architect: Settings,
    engineer: Code,
    qa: TestTube,
  };

  const roleColors = {
    product_manager: "text-purple-400 bg-purple-500/20",
    architect: "text-blue-400 bg-blue-500/20",
    engineer: "text-green-400 bg-green-500/20",
    qa: "text-orange-400 bg-orange-500/20",
  };

  const RoleIcon = roleIcons[step.role];
  const statusColor = statusColors[step.status] || statusColors.pending;
  const roleColor = roleColors[step.role];

  const isPending = step.status === "pending";
  const isInProgress = step.status === "in_progress";
  const isComplete = step.status === "complete";
  const isBlocked = step.status === "blocked";

  return (
    <motion.div
      initial={animated ? { opacity: 0, scale: 0.8, y: 20 } : undefined}
      animate={animated ? { opacity: 1, scale: 1, y: 0 } : undefined}
      transition={{ delay: index * 0.1, type: "spring", stiffness: 200, damping: 20 }}
      className={`flow-step-node ${statusColor} ${isSelected ? "flow-step-selected" : ""}`}
      onClick={onClick}
    >
      {/* Status Indicator */}
      <div className="flow-step-status">
        {isPending && <Clock className="w-4 h-4 text-neutral-400" />}
        {isInProgress && <Loader2 className="w-4 h-4 animate-spin text-brand-400" />}
        {isComplete && <CheckCircle className="w-4 h-4 text-green-400" />}
        {isBlocked && <AlertTriangle className="w-4 h-4 text-red-400" />}
      </div>

      {/* Role Icon */}
      <div className={`flow-step-icon ${roleColor}`}>
        <RoleIcon className="w-5 h-5" />
      </div>

      {/* Content */}
      <div className="flow-step-content">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-brand-400">
            Step {index + 1}
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-black/30 capitalize">
            {step.role.replace("_", " ")}
          </span>
        </div>
        <h4 className="text-sm font-medium text-white mb-1">{step.title}</h4>
        {step.description && (
          <p className="text-xs text-neutral-400 line-clamp-2">{step.description}</p>
        )}

        {/* Progress Bar */}
        {isInProgress && step.progress !== undefined && (
          <div className="mt-2">
            <div className="w-full bg-neutral-800 rounded-full h-1.5">
              <motion.div
                className="bg-brand-500 h-1.5 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${step.progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <p className="text-xs text-neutral-500 mt-1">{step.progress}% complete</p>
          </div>
        )}

        {/* Timestamps */}
        <div className="flex items-center gap-3 mt-2 text-xs text-neutral-500">
          {step.started_at && (
            <span>Started: {new Date(step.started_at).toLocaleTimeString()}</span>
          )}
          {step.completed_at && (
            <span>Completed: {new Date(step.completed_at).toLocaleTimeString()}</span>
          )}
        </div>

        {/* Error Message */}
        {step.error && (
          <div className="mt-2 bg-red-500/10 border border-red-500/20 rounded p-2">
            <p className="text-xs text-red-300">{step.error}</p>
          </div>
        )}
      </div>

      {/* Artifact Indicator */}
      {step.artifact && (
        <div className="flow-step-artifact-badge">
          <CheckCircle className="w-3 h-3 text-green-400" />
          <span className="text-xs">Artifact</span>
        </div>
      )}

      {/* Glow Effect for Active Step */}
      {isInProgress && (
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
      )}
    </motion.div>
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
  const isActive = fromStep.status === "complete" && toStep.status !== "pending";
  const isAnimated = fromStep.status === "in_progress" || toStep.status === "in_progress";

  return (
    <div className={`flow-connector flow-connector-${type}`}>
      <div className={`flow-connector-line ${isActive ? "flow-connector-active" : ""}`}>
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
  const roleColors = {
    product_manager: "bg-purple-500/10 border-purple-500/20",
    architect: "bg-blue-500/10 border-blue-500/20",
    engineer: "bg-green-500/10 border-green-500/20",
    qa: "bg-orange-500/10 border-orange-500/20",
  };

  const roleColor = roleColors[step.role];

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
        className={`flow-details-panel ${roleColor}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flow-details-header">
          <div>
            <h3 className="text-lg font-semibold text-white">{step.title}</h3>
            <p className="text-sm text-neutral-400 capitalize">
              {step.role.replace("_", " ")} • {step.status}
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
              <h4 className="text-sm font-medium text-neutral-300 mb-2">Description</h4>
              <p className="text-sm text-neutral-400">{step.description}</p>
            </div>
          )}

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            {step.started_at && (
              <div>
                <p className="text-xs text-neutral-500 mb-1">Started</p>
                <p className="text-sm text-neutral-300">
                  {new Date(step.started_at).toLocaleString()}
                </p>
              </div>
            )}
            {step.completed_at && (
              <div>
                <p className="text-xs text-neutral-500 mb-1">Completed</p>
                <p className="text-sm text-neutral-300">
                  {new Date(step.completed_at).toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {/* Progress */}
          {step.progress !== undefined && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-neutral-300">Progress</h4>
                <span className="text-sm text-brand-400">{step.progress}%</span>
              </div>
              <div className="w-full bg-neutral-800 rounded-full h-2">
                <div
                  className="bg-brand-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${step.progress}%` }}
                />
              </div>
            </div>
          )}

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
                <h4 className="text-sm font-medium text-green-300">Artifact Available</h4>
              </div>
              <p className="text-xs text-neutral-400">
                This step has generated an artifact. View it in the orchestration panel.
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
// HELPER FUNCTIONS
// ============================================================================

function getStatusClass(status: string): string {
  const classes: Record<string, string> = {
    running: "bg-brand-500/20 border-brand-500/30 text-brand-300",
    in_progress: "bg-brand-500/20 border-brand-500/30 text-brand-300",
    complete: "bg-green-500/20 border-green-500/30 text-green-300",
    completed: "bg-green-500/20 border-green-500/30 text-green-300",
    error: "bg-red-500/20 border-red-500/30 text-red-300",
    failed: "bg-red-500/20 border-red-500/30 text-red-300",
    idle: "bg-neutral-500/20 border-neutral-500/30 text-neutral-300",
  };
  return classes[status] || "bg-neutral-500/20 border-neutral-500/30 text-neutral-300";
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
      <div className={`compact-flow-status ${getStatusClass(status)}`}>
        <span className="text-xs font-medium capitalize">{status}</span>
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
  const roleIcons = {
    product_manager: User,
    architect: Settings,
    engineer: Code,
    qa: TestTube,
  };

  const RoleIcon = roleIcons[step.role];

  const statusColors = {
    pending: "bg-neutral-500/10 border-neutral-500/30",
    in_progress: "bg-brand-500/20 border-brand-500/50",
    complete: "bg-green-500/20 border-green-500/50",
    blocked: "bg-red-500/20 border-red-500/50",
  };

  const statusColor = statusColors[step.status] || statusColors.pending;
  const isActive = step.status === "in_progress";
  const isComplete = step.status === "complete";

  return (
    <div className="compact-step-wrapper">
      <motion.button
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: index * 0.05 }}
        className={`compact-step-badge ${statusColor}`}
        onClick={onClick}
        title={`${step.title} (${step.status})`}
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
          <div className={`w-full h-0.5 ${isComplete ? "bg-green-500/50" : "bg-neutral-700"}`} />
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
  const roleColors = {
    product_manager: "bg-purple-500/20 border-purple-500/50",
    architect: "bg-blue-500/20 border-blue-500/50",
    engineer: "bg-green-500/20 border-green-500/50",
    qa: "bg-orange-500/20 border-orange-500/50",
  };

  const roleColor = roleColors[step.role];
  const isComplete = step.status === "complete";
  const isActive = step.status === "in_progress";

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className="timeline-item"
      onClick={onClick}
    >
      <div className="timeline-marker">
        <div className={`timeline-dot ${roleColor}`}>
          {isComplete && <CheckCircle className="w-3 h-3 text-green-400" />}
          {isActive && <Loader2 className="w-3 h-3 text-brand-400 animate-spin" />}
          {!isComplete && !isActive && <Clock className="w-3 h-3 text-neutral-400" />}
        </div>
        {!isLast && <div className="timeline-line" />}
      </div>
      <div className="timeline-content">
        <div className="timeline-header">
          <span className="text-xs text-neutral-500">
            Step {index + 1} • {step.role.replace("_", " ")}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded ${roleColor} capitalize`}>
            {step.status}
          </span>
        </div>
        <h4 className="text-sm font-medium text-white mb-1">{step.title}</h4>
        {step.description && (
          <p className="text-xs text-neutral-400">{step.description}</p>
        )}
        {step.started_at && (
          <p className="text-xs text-neutral-500 mt-1">
            {new Date(step.started_at).toLocaleString()}
          </p>
        )}
      </div>
    </motion.div>
  );
}

