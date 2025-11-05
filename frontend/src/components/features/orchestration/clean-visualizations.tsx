/**
 * MetaSOP Clean Visualizations
 * 
 * Beautiful, role-specific visualizations for MetaSOP agent artifacts
 * Zero code exposure, pure UI components
 */

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  Circle,
  AlertTriangle,
  Clock,
  User,
  Settings,
  Code,
  TestTube,
  FileText,
  Database,
  Globe,
  Lock,
  Zap,
  TrendingUp,
  Activity,
  Shield,
  AlertCircle,
  FolderOpen,
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  Play,
  Package,
  Terminal,
} from "lucide-react";
import type {
  ParsedArtifact,
  PMSpecArtifact,
  ArchitectSpecArtifact,
  EngineerSpecArtifact,
  QASpecArtifact,
  UserStory,
  AcceptanceCriteria,
  FileNode,
  ImplementationStep,
  TestScenario,
  VisualizationProps,
} from "#/types/metasop-artifacts";

// ============================================================================
// MAIN VISUAL ADAPTER
// ============================================================================

export function CleanVisualAdapter({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: VisualizationProps) {
  if (artifact.error) {
    return (
      <div className={`metasop-viz-error ${className}`}>
        <AlertCircle className="w-8 h-8 text-red-500" />
        <p className="mt-2 text-sm text-red-400">{artifact.error}</p>
      </div>
    );
  }

  switch (artifact.role) {
    case "product_manager":
      return (
        <PMVisualization
          artifact={artifact.data as PMSpecArtifact}
          animated={animated}
          className={className}
          onInteraction={onInteraction}
        />
      );
    case "architect":
      return (
        <ArchitectVisualization
          artifact={artifact.data as ArchitectSpecArtifact}
          animated={animated}
          className={className}
          onInteraction={onInteraction}
        />
      );
    case "engineer":
      return (
        <EngineerVisualization
          artifact={artifact.data as EngineerSpecArtifact}
          animated={animated}
          className={className}
          onInteraction={onInteraction}
        />
      );
    case "qa":
      return (
        <QAVisualization
          artifact={artifact.data as QASpecArtifact}
          animated={animated}
          className={className}
          onInteraction={onInteraction}
        />
      );
    default:
      return (
        <div className={`metasop-viz-unknown ${className}`}>
          <p>Unknown role: {artifact.role}</p>
        </div>
      );
  }
}

// ============================================================================
// PRODUCT MANAGER VISUALIZATION (PURPLE THEME)
// ============================================================================

interface PMVisualizationProps {
  artifact: PMSpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: any) => void;
}

function PMVisualization({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: PMVisualizationProps) {
  const hasUserStories = artifact.user_stories && artifact.user_stories.length > 0;
  const hasAcceptanceCriteria = artifact.acceptance_criteria && artifact.acceptance_criteria.length > 0;
  const hasEpics = artifact.epics && artifact.epics.length > 0;
  const hasMetrics = artifact.success_metrics && artifact.success_metrics.length > 0;

  if (!hasUserStories && !hasAcceptanceCriteria && !hasEpics && !hasMetrics) {
    return (
      <div className={`metasop-viz-empty ${className}`}>
        <User className="w-12 h-12 text-purple-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">No product specifications yet...</p>
      </div>
    );
  }

  return (
    <div className={`metasop-viz-pm ${className}`}>
      {/* Header */}
      <div className="metasop-viz-header bg-purple-500/10 border-purple-500/20">
        <User className="w-5 h-5 text-purple-400" />
        <h3 className="text-sm font-semibold text-purple-300">Product Manager</h3>
        <span className="text-xs text-purple-400/60">Requirements & User Stories</span>
      </div>

      <div className="p-4 space-y-6">
        {/* Epics */}
        {hasEpics && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Epics
            </h4>
            {artifact.epics!.map((epic, index) => (
              <motion.div
                key={epic.id || index}
                initial={animated ? { opacity: 0, x: -20 } : undefined}
                animate={animated ? { opacity: 1, x: 0 } : undefined}
                transition={{ delay: index * 0.1 }}
                className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h5 className="text-sm font-medium text-purple-200">{epic.title}</h5>
                    {epic.description && (
                      <p className="text-xs text-neutral-400 mt-1">{epic.description}</p>
                    )}
                    {epic.stories && epic.stories.length > 0 && (
                      <div className="mt-2 text-xs text-purple-400">
                        {epic.stories.length} {epic.stories.length === 1 ? "story" : "stories"}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* User Stories */}
        {hasUserStories && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
              <User className="w-4 h-4" />
              User Stories ({artifact.user_stories!.length})
            </h4>
            {artifact.user_stories!.map((story, index) => (
              <UserStoryCard
                key={story.id || index}
                story={story}
                index={index}
                animated={animated}
                onClick={() => onInteraction?.("story_click", story)}
              />
            ))}
          </div>
        )}

        {/* Acceptance Criteria */}
        {hasAcceptanceCriteria && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Acceptance Criteria ({artifact.acceptance_criteria!.length})
            </h4>
            {artifact.acceptance_criteria!.map((criteria, index) => (
              <AcceptanceCriteriaCard
                key={criteria.id || index}
                criteria={criteria}
                index={index}
                animated={animated}
              />
            ))}
          </div>
        )}

        {/* Success Metrics */}
        {hasMetrics && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Success Metrics
            </h4>
            {artifact.success_metrics!.map((metric, index) => (
              <motion.div
                key={index}
                initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
                animate={animated ? { opacity: 1, scale: 1 } : undefined}
                transition={{ delay: index * 0.05 }}
                className="bg-purple-500/5 border border-purple-500/20 rounded px-3 py-2"
              >
                <div className="flex items-start justify-between">
                  <p className="text-sm text-purple-200">{metric.metric}</p>
                  {metric.target && (
                    <span className="text-xs text-purple-400 ml-2">Target: {metric.target}</span>
                  )}
                </div>
                {metric.description && (
                  <p className="text-xs text-neutral-400 mt-1">{metric.description}</p>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// User Story Card Component
function UserStoryCard({
  story,
  index,
  animated,
  onClick,
}: {
  story: UserStory;
  index: number;
  animated?: boolean;
  onClick?: () => void;
}) {
  const priorityColors = {
    critical: "text-red-400 bg-red-500/20 border-red-500/30",
    high: "text-orange-400 bg-orange-500/20 border-orange-500/30",
    medium: "text-yellow-400 bg-yellow-500/20 border-yellow-500/30",
    low: "text-green-400 bg-green-500/20 border-green-500/30",
  };

  const priorityColor = story.priority
    ? priorityColors[story.priority]
    : "text-neutral-400 bg-neutral-500/20 border-neutral-500/30";

  return (
    <motion.div
      initial={animated ? { opacity: 0, y: 20 } : undefined}
      animate={animated ? { opacity: 1, y: 0 } : undefined}
      transition={{ delay: index * 0.1 }}
      className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-4 hover:bg-purple-500/10 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <h5 className="text-sm font-medium text-purple-100">{story.title}</h5>
        {story.priority && (
          <span className={`text-xs px-2 py-1 rounded border ${priorityColor}`}>
            {story.priority.toUpperCase()}
          </span>
        )}
      </div>

      {/* Story Format */}
      {(story.as_a || story.i_want || story.so_that) && (
        <div className="space-y-1 text-xs text-neutral-300 bg-black/20 rounded p-2 border border-purple-500/10">
          {story.as_a && <p><span className="text-purple-400">As a</span> {story.as_a}</p>}
          {story.i_want && <p><span className="text-purple-400">I want</span> {story.i_want}</p>}
          {story.so_that && <p><span className="text-purple-400">So that</span> {story.so_that}</p>}
        </div>
      )}

      {/* Description */}
      {(story.description || story.story) && !story.as_a && (
        <p className="text-xs text-neutral-400 mt-2">
          {story.description || story.story}
        </p>
      )}

      {/* Metadata */}
      <div className="flex items-center gap-3 mt-3 text-xs text-neutral-500">
        {story.estimate && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {story.estimate}
          </span>
        )}
        {story.status && (
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3" />
            {story.status}
          </span>
        )}
        {story.tags && story.tags.length > 0 && (
          <div className="flex gap-1">
            {story.tags.map((tag, i) => (
              <span key={i} className="px-1.5 py-0.5 bg-purple-500/20 rounded text-purple-300">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Acceptance Criteria Card Component
function AcceptanceCriteriaCard({
  criteria,
  index,
  animated,
}: {
  criteria: AcceptanceCriteria;
  index: number;
  animated?: boolean;
}) {
  const [isCompleted, setIsCompleted] = React.useState(criteria.completed || false);

  return (
    <motion.div
      initial={animated ? { opacity: 0, x: -20 } : undefined}
      animate={animated ? { opacity: 1, x: 0 } : undefined}
      transition={{ delay: index * 0.05 }}
      className={`bg-purple-500/5 border border-purple-500/20 rounded p-3 ${
        isCompleted ? "opacity-60" : ""
      }`}
    >
      <div className="flex items-start gap-3">
        <button
          onClick={() => setIsCompleted(!isCompleted)}
          className="mt-0.5 text-purple-400 hover:text-purple-300 transition-colors"
        >
          {isCompleted ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <Circle className="w-4 h-4" />
          )}
        </button>
        <div className="flex-1">
          <p className={`text-sm ${isCompleted ? "line-through text-neutral-500" : "text-neutral-300"}`}>
            {criteria.criteria || criteria.description}
          </p>

          {/* Given/When/Then Format */}
          {(criteria.given || criteria.when || criteria.then) && (
            <div className="mt-2 space-y-1 text-xs text-neutral-400 bg-black/20 rounded p-2 border border-purple-500/10">
              {criteria.given && <p><span className="text-purple-400">Given</span> {criteria.given}</p>}
              {criteria.when && <p><span className="text-purple-400">When</span> {criteria.when}</p>}
              {criteria.then && <p><span className="text-purple-400">Then</span> {criteria.then}</p>}
            </div>
          )}

          {criteria.scenario && !criteria.given && (
            <p className="text-xs text-neutral-500 mt-1">{criteria.scenario}</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ============================================================================
// ARCHITECT VISUALIZATION (BLUE THEME)
// ============================================================================

interface ArchitectVisualizationProps {
  artifact: ArchitectSpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: any) => void;
}

function ArchitectVisualization({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: ArchitectVisualizationProps) {
  const hasArchitecture = artifact.system_architecture?.components && artifact.system_architecture.components.length > 0;
  const hasAPIs = artifact.api_endpoints && artifact.api_endpoints.length > 0;
  const hasDatabase = artifact.database_schema && artifact.database_schema.length > 0;
  const hasDecisions = artifact.technical_decisions && artifact.technical_decisions.length > 0;
  const hasTechStack = artifact.technology_stack && Object.keys(artifact.technology_stack).length > 0;

  if (!hasArchitecture && !hasAPIs && !hasDatabase && !hasDecisions && !hasTechStack) {
    return (
      <div className={`metasop-viz-empty ${className}`}>
        <Settings className="w-12 h-12 text-blue-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">No architecture details yet...</p>
      </div>
    );
  }

  return (
    <div className={`metasop-viz-architect ${className}`}>
      {/* Header */}
      <div className="metasop-viz-header bg-blue-500/10 border-blue-500/20">
        <Settings className="w-5 h-5 text-blue-400" />
        <h3 className="text-sm font-semibold text-blue-300">Architect</h3>
        <span className="text-xs text-blue-400/60">System Design & Architecture</span>
      </div>

      <div className="p-4 space-y-6">
        {/* System Architecture */}
        {hasArchitecture && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-blue-300 uppercase tracking-wide flex items-center gap-2">
              <Database className="w-4 h-4" />
              System Components ({artifact.system_architecture!.components!.length})
            </h4>
            <div className="grid grid-cols-1 gap-3">
              {artifact.system_architecture!.components!.map((component, index) => (
                <motion.div
                  key={component.id}
                  initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
                  animate={animated ? { opacity: 1, scale: 1 } : undefined}
                  transition={{ delay: index * 0.05 }}
                  className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h5 className="text-sm font-medium text-blue-200">{component.name}</h5>
                        <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded border border-blue-500/30">
                          {component.type}
                        </span>
                      </div>
                      {component.description && (
                        <p className="text-xs text-neutral-400 mt-1">{component.description}</p>
                      )}
                      {component.technologies && component.technologies.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {component.technologies.map((tech, i) => (
                            <span key={i} className="text-xs px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded">
                              {tech}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* API Endpoints */}
        {hasAPIs && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-blue-300 uppercase tracking-wide flex items-center gap-2">
              <Globe className="w-4 h-4" />
              API Endpoints ({artifact.api_endpoints!.length})
            </h4>
            {artifact.api_endpoints!.map((endpoint, index) => (
              <motion.div
                key={index}
                initial={animated ? { opacity: 0, x: -20 } : undefined}
                animate={animated ? { opacity: 1, x: 0 } : undefined}
                transition={{ delay: index * 0.05 }}
                className="bg-blue-500/5 border border-blue-500/20 rounded p-3"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs font-mono px-2 py-1 rounded ${getMethodColor(endpoint.method)}`}>
                    {endpoint.method}
                  </span>
                  <code className="text-xs text-blue-300 font-mono">{endpoint.path}</code>
                  {endpoint.auth_required && (
                    <Lock className="w-3 h-3 text-yellow-400" />
                  )}
                </div>
                {endpoint.description && (
                  <p className="text-xs text-neutral-400">{endpoint.description}</p>
                )}
              </motion.div>
            ))}
          </div>
        )}

        {/* Database Schema */}
        {hasDatabase && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-blue-300 uppercase tracking-wide flex items-center gap-2">
              <Database className="w-4 h-4" />
              Database Schema ({artifact.database_schema!.length} tables)
            </h4>
            {artifact.database_schema!.map((schema, index) => (
              <motion.div
                key={index}
                initial={animated ? { opacity: 0, y: 20 } : undefined}
                animate={animated ? { opacity: 1, y: 0 } : undefined}
                transition={{ delay: index * 0.05 }}
                className="bg-blue-500/5 border border-blue-500/20 rounded p-3"
              >
                <h5 className="text-sm font-mono text-blue-300 mb-2">{schema.table_name}</h5>
                {schema.columns && schema.columns.length > 0 && (
                  <div className="text-xs text-neutral-400 space-y-1">
                    {schema.columns.slice(0, 5).map((col, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="text-blue-400">{col.name}</span>
                        <span className="text-neutral-500">{col.type}</span>
                      </div>
                    ))}
                    {schema.columns.length > 5 && (
                      <p className="text-neutral-500">+ {schema.columns.length - 5} more columns</p>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}

        {/* Technical Decisions */}
        {hasDecisions && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-blue-300 uppercase tracking-wide flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Key Decisions ({artifact.technical_decisions!.length})
            </h4>
            {artifact.technical_decisions!.map((decision, index) => (
              <motion.div
                key={index}
                initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
                animate={animated ? { opacity: 1, scale: 1 } : undefined}
                transition={{ delay: index * 0.05 }}
                className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3"
              >
                <div className="flex items-start justify-between mb-2">
                  <h5 className="text-sm font-medium text-blue-200">{decision.decision}</h5>
                  {decision.confidence && (
                    <span className={`text-xs px-2 py-1 rounded ${getConfidenceColor(decision.confidence)}`}>
                      {decision.confidence}
                    </span>
                  )}
                </div>
                {decision.rationale && (
                  <p className="text-xs text-neutral-400 mt-2">{decision.rationale}</p>
                )}
                {decision.alternatives && decision.alternatives.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-blue-400 mb-1">Alternatives considered:</p>
                    <ul className="text-xs text-neutral-500 space-y-0.5 pl-4">
                      {decision.alternatives.map((alt, i) => (
                        <li key={i}>• {alt}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}

        {/* Technology Stack */}
        {hasTechStack && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-blue-300 uppercase tracking-wide flex items-center gap-2">
              <Package className="w-4 h-4" />
              Technology Stack
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(artifact.technology_stack!).map(([key, value], index) => (
                <motion.div
                  key={key}
                  initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
                  animate={animated ? { opacity: 1, scale: 1 } : undefined}
                  transition={{ delay: index * 0.03 }}
                  className="bg-blue-500/5 border border-blue-500/20 rounded px-3 py-2"
                >
                  <p className="text-xs text-blue-400">{key}</p>
                  <p className="text-xs text-neutral-300 font-mono">{value}</p>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function getMethodColor(method: string): string {
  const colors: Record<string, string> = {
    GET: "bg-green-500/20 text-green-300 border border-green-500/30",
    POST: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
    PUT: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
    PATCH: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
    DELETE: "bg-red-500/20 text-red-300 border border-red-500/30",
  };
  return colors[method] || "bg-neutral-500/20 text-neutral-300 border border-neutral-500/30";
}

function getConfidenceColor(confidence: string): string {
  const colors: Record<string, string> = {
    high: "bg-green-500/20 text-green-300 border border-green-500/30",
    medium: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
    low: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
  };
  return colors[confidence] || "bg-neutral-500/20 text-neutral-300 border border-neutral-500/30";
}

// ============================================================================
// ENGINEER VISUALIZATION (GREEN THEME)
// ============================================================================

interface EngineerVisualizationProps {
  artifact: EngineerSpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: any) => void;
}

function EngineerVisualization({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: EngineerVisualizationProps) {
  const hasFileStructure = artifact.file_structure && artifact.file_structure.length > 0;
  const hasImplementationPlan = artifact.implementation_plan && artifact.implementation_plan.length > 0;
  const hasDependencies = artifact.dependencies && artifact.dependencies.length > 0;
  const hasCodeSnippets = artifact.code_snippets && artifact.code_snippets.length > 0;

  if (!hasFileStructure && !hasImplementationPlan && !hasDependencies && !hasCodeSnippets) {
    return (
      <div className={`metasop-viz-empty ${className}`}>
        <Code className="w-12 h-12 text-green-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">No implementation details yet...</p>
      </div>
    );
  }

  return (
    <div className={`metasop-viz-engineer ${className}`}>
      {/* Header */}
      <div className="metasop-viz-header bg-green-500/10 border-green-500/20">
        <Code className="w-5 h-5 text-green-400" />
        <h3 className="text-sm font-semibold text-green-300">Engineer</h3>
        <span className="text-xs text-green-400/60">Implementation Plan</span>
      </div>

      <div className="p-4 space-y-6">
        {/* File Structure */}
        {hasFileStructure && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
              <FolderOpen className="w-4 h-4" />
              File Structure
            </h4>
            <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-3">
              {artifact.file_structure!.map((node, index) => (
                <FileTreeNode
                  key={index}
                  node={node}
                  depth={0}
                  animated={animated}
                  index={index}
                />
              ))}
            </div>
          </div>
        )}

        {/* Implementation Plan */}
        {hasImplementationPlan && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
              <Play className="w-4 h-4" />
              Implementation Steps ({artifact.implementation_plan!.length})
            </h4>
            {artifact.implementation_plan!.map((step, index) => (
              <ImplementationStepCard
                key={index}
                step={step}
                index={index}
                animated={animated}
              />
            ))}
          </div>
        )}

        {/* Dependencies */}
        {hasDependencies && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
              <Package className="w-4 h-4" />
              Dependencies ({artifact.dependencies!.length})
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {artifact.dependencies!.map((dep, index) => (
                <motion.div
                  key={index}
                  initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
                  animate={animated ? { opacity: 1, scale: 1 } : undefined}
                  transition={{ delay: index * 0.02 }}
                  className={`bg-green-500/5 border rounded px-3 py-2 ${
                    dep.dev ? "border-green-500/10" : "border-green-500/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-mono text-green-300">{dep.name}</p>
                    {dep.dev && (
                      <span className="text-xs text-neutral-500">dev</span>
                    )}
                  </div>
                  {dep.version && (
                    <p className="text-xs text-neutral-500 mt-0.5">{dep.version}</p>
                  )}
                  {dep.purpose && (
                    <p className="text-xs text-neutral-600 mt-1">{dep.purpose}</p>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Commands */}
        {(artifact.setup_commands?.length || artifact.run_commands?.length || artifact.test_commands?.length) && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              Commands
            </h4>
            {artifact.setup_commands && artifact.setup_commands.length > 0 && (
              <div>
                <p className="text-xs text-green-400 mb-1">Setup:</p>
                {artifact.setup_commands.map((cmd, i) => (
                  <div key={i} className="bg-black/40 border border-green-500/20 rounded px-3 py-2 mb-1">
                    <code className="text-xs text-green-300 font-mono">{cmd}</code>
                  </div>
                ))}
              </div>
            )}
            {artifact.run_commands && artifact.run_commands.length > 0 && (
              <div>
                <p className="text-xs text-green-400 mb-1">Run:</p>
                {artifact.run_commands.map((cmd, i) => (
                  <div key={i} className="bg-black/40 border border-green-500/20 rounded px-3 py-2 mb-1">
                    <code className="text-xs text-green-300 font-mono">{cmd}</code>
                  </div>
                ))}
              </div>
            )}
            {artifact.test_commands && artifact.test_commands.length > 0 && (
              <div>
                <p className="text-xs text-green-400 mb-1">Test:</p>
                {artifact.test_commands.map((cmd, i) => (
                  <div key={i} className="bg-black/40 border border-green-500/20 rounded px-3 py-2 mb-1">
                    <code className="text-xs text-green-300 font-mono">{cmd}</code>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Estimated Effort */}
        {artifact.estimated_effort && (
          <div className="bg-green-500/5 border border-green-500/20 rounded p-3">
            <p className="text-xs text-green-400 mb-1">Estimated Effort:</p>
            <p className="text-sm text-green-300">{artifact.estimated_effort}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// File Tree Node Component
function FileTreeNode({
  node,
  depth,
  animated,
  index,
}: {
  node: FileNode;
  depth: number;
  animated?: boolean;
  index: number;
}) {
  const [isExpanded, setIsExpanded] = React.useState(depth < 2); // Auto-expand first 2 levels
  const isFolder = node.type === "folder" || node.type === "directory" || (node.children && node.children.length > 0);

  return (
    <motion.div
      initial={animated ? { opacity: 0, x: -10 } : undefined}
      animate={animated ? { opacity: 1, x: 0 } : undefined}
      transition={{ delay: index * 0.02 }}
      style={{ paddingLeft: `${depth * 16}px` }}
      className="select-none"
    >
      <div
        className="flex items-center gap-2 py-1 hover:bg-green-500/5 rounded cursor-pointer group"
        onClick={() => isFolder && setIsExpanded(!isExpanded)}
      >
        {isFolder ? (
          <>
            {isExpanded ? (
              <ChevronDown className="w-3 h-3 text-green-400" />
            ) : (
              <ChevronRight className="w-3 h-3 text-green-400" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-green-400" />
            ) : (
              <Folder className="w-4 h-4 text-green-500" />
            )}
          </>
        ) : (
          <>
            <span className="w-3 h-3" />
            <File className="w-4 h-4 text-neutral-500" />
          </>
        )}
        <span className={`text-xs ${isFolder ? "text-green-300 font-medium" : "text-neutral-400"}`}>
          {node.name}
        </span>
        {node.purpose && (
          <span className="text-xs text-neutral-600 hidden group-hover:inline ml-2">
            - {node.purpose}
          </span>
        )}
      </div>

      {isFolder && isExpanded && node.children && (
        <div>
          {node.children.map((child, i) => (
            <FileTreeNode
              key={i}
              node={child}
              depth={depth + 1}
              animated={animated}
              index={i}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}

// Implementation Step Card
function ImplementationStepCard({
  step,
  index,
  animated,
}: {
  step: ImplementationStep;
  index: number;
  animated?: boolean;
}) {
  const [isCompleted, setIsCompleted] = React.useState(step.completed || false);

  return (
    <motion.div
      initial={animated ? { opacity: 0, x: -20 } : undefined}
      animate={animated ? { opacity: 1, x: 0 } : undefined}
      transition={{ delay: index * 0.1 }}
      className={`bg-green-500/5 border border-green-500/20 rounded-lg p-3 ${
        isCompleted ? "opacity-60" : ""
      }`}
    >
      <div className="flex items-start gap-3">
        <button
          onClick={() => setIsCompleted(!isCompleted)}
          className="mt-0.5 text-green-400 hover:text-green-300 transition-colors"
        >
          {isCompleted ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <Circle className="w-5 h-5" />
          )}
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-green-400">
              Step {step.step_number || index + 1}
            </span>
            {step.estimated_time && (
              <span className="text-xs text-neutral-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {step.estimated_time}
              </span>
            )}
          </div>
          <h5 className={`text-sm font-medium ${isCompleted ? "line-through text-neutral-500" : "text-green-200"}`}>
            {step.title}
          </h5>
          {step.description && (
            <p className="text-xs text-neutral-400 mt-1">{step.description}</p>
          )}

          {/* Files */}
          {(step.files_to_create?.length || step.files_to_modify?.length) && (
            <div className="mt-2 text-xs space-y-1">
              {step.files_to_create && step.files_to_create.length > 0 && (
                <div>
                  <span className="text-green-400">Create:</span>
                  <ul className="text-neutral-500 pl-4 mt-0.5">
                    {step.files_to_create.map((file, i) => (
                      <li key={i}>• {file}</li>
                    ))}
                  </ul>
                </div>
              )}
              {step.files_to_modify && step.files_to_modify.length > 0 && (
                <div>
                  <span className="text-yellow-400">Modify:</span>
                  <ul className="text-neutral-500 pl-4 mt-0.5">
                    {step.files_to_modify.map((file, i) => (
                      <li key={i}>• {file}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Commands */}
          {step.commands && step.commands.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-green-400 mb-1">Commands:</p>
              {step.commands.map((cmd, i) => (
                <div key={i} className="bg-black/40 border border-green-500/20 rounded px-2 py-1 mb-1">
                  <code className="text-xs text-green-300 font-mono">{cmd}</code>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ============================================================================
// QA VISUALIZATION (ORANGE THEME)
// ============================================================================

interface QAVisualizationProps {
  artifact: QASpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: any) => void;
}

function QAVisualization({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: QAVisualizationProps) {
  const hasTestScenarios = artifact.test_scenarios && artifact.test_scenarios.length > 0;
  const hasTestResults = artifact.test_results && artifact.test_results.total !== undefined;
  const hasCoverage = artifact.code_coverage && Object.keys(artifact.code_coverage).length > 0;
  const hasSecurityFindings = artifact.security_findings && artifact.security_findings.length > 0;
  const hasPerformanceMetrics = artifact.performance_metrics && Object.keys(artifact.performance_metrics).length > 0;

  if (!hasTestScenarios && !hasTestResults && !hasCoverage && !hasSecurityFindings && !hasPerformanceMetrics) {
    return (
      <div className={`metasop-viz-empty ${className}`}>
        <TestTube className="w-12 h-12 text-orange-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">No test results yet...</p>
      </div>
    );
  }

  const passRate = hasTestResults && artifact.test_results!.total! > 0
    ? Math.round((artifact.test_results!.passed! / artifact.test_results!.total!) * 100)
    : 0;

  return (
    <div className={`metasop-viz-qa ${className}`}>
      {/* Header */}
      <div className="metasop-viz-header bg-orange-500/10 border-orange-500/20">
        <TestTube className="w-5 h-5 text-orange-400" />
        <h3 className="text-sm font-semibold text-orange-300">QA Engineer</h3>
        <span className="text-xs text-orange-400/60">Testing & Quality Assurance</span>
      </div>

      <div className="p-4 space-y-6">
        {/* Test Results Summary */}
        {hasTestResults && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide">Test Results</h4>
            <div className="grid grid-cols-4 gap-2">
              <motion.div
                initial={animated ? { opacity: 0, y: 20 } : undefined}
                animate={animated ? { opacity: 1, y: 0 } : undefined}
                className="bg-green-500/10 border border-green-500/20 rounded p-3 text-center"
              >
                <p className="text-2xl font-bold text-green-400">{artifact.test_results!.passed || 0}</p>
                <p className="text-xs text-green-300 mt-1">Passed</p>
              </motion.div>
              <motion.div
                initial={animated ? { opacity: 0, y: 20 } : undefined}
                animate={animated ? { opacity: 1, y: 0 } : undefined}
                transition={{ delay: 0.05 }}
                className="bg-red-500/10 border border-red-500/20 rounded p-3 text-center"
              >
                <p className="text-2xl font-bold text-red-400">{artifact.test_results!.failed || 0}</p>
                <p className="text-xs text-red-300 mt-1">Failed</p>
              </motion.div>
              <motion.div
                initial={animated ? { opacity: 0, y: 20 } : undefined}
                animate={animated ? { opacity: 1, y: 0 } : undefined}
                transition={{ delay: 0.1 }}
                className="bg-yellow-500/10 border border-yellow-500/20 rounded p-3 text-center"
              >
                <p className="text-2xl font-bold text-yellow-400">{artifact.test_results!.skipped || 0}</p>
                <p className="text-xs text-yellow-300 mt-1">Skipped</p>
              </motion.div>
              <motion.div
                initial={animated ? { opacity: 0, y: 20 } : undefined}
                animate={animated ? { opacity: 1, y: 0 } : undefined}
                transition={{ delay: 0.15 }}
                className="bg-orange-500/10 border border-orange-500/20 rounded p-3 text-center"
              >
                <p className="text-2xl font-bold text-orange-400">{passRate}%</p>
                <p className="text-xs text-orange-300 mt-1">Pass Rate</p>
              </motion.div>
            </div>
          </div>
        )}

        {/* Code Coverage */}
        {hasCoverage && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Code Coverage
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(artifact.code_coverage!).map(([key, value]) => (
                <motion.div
                  key={key}
                  initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
                  animate={animated ? { opacity: 1, scale: 1 } : undefined}
                  className="bg-orange-500/5 border border-orange-500/20 rounded p-2"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-orange-300 capitalize">{key}</p>
                    <p className="text-sm font-bold text-orange-400">{value}%</p>
                  </div>
                  <div className="w-full bg-neutral-800 rounded-full h-1.5 mt-2">
                    <div
                      className="bg-orange-500 h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${value}%` }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Test Scenarios */}
        {hasTestScenarios && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
              <TestTube className="w-4 h-4" />
              Test Scenarios ({artifact.test_scenarios!.length})
            </h4>
            {artifact.test_scenarios!.slice(0, 10).map((scenario, index) => (
              <TestScenarioCard
                key={scenario.id || index}
                scenario={scenario}
                index={index}
                animated={animated}
              />
            ))}
            {artifact.test_scenarios!.length > 10 && (
              <p className="text-xs text-neutral-500 text-center py-2">
                + {artifact.test_scenarios!.length - 10} more scenarios
              </p>
            )}
          </div>
        )}

        {/* Security Findings */}
        {hasSecurityFindings && artifact.security_findings!.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Security Findings ({artifact.security_findings!.length})
            </h4>
            {artifact.security_findings!.map((finding, index) => (
              <motion.div
                key={index}
                initial={animated ? { opacity: 0, x: -20 } : undefined}
                animate={animated ? { opacity: 1, x: 0 } : undefined}
                transition={{ delay: index * 0.05 }}
                className="bg-red-500/10 border border-red-500/20 rounded p-3"
              >
                <div className="flex items-start justify-between mb-1">
                  <h5 className="text-sm font-medium text-red-300">{finding.title}</h5>
                  <span className={`text-xs px-2 py-1 rounded ${getSeverityColor(finding.severity)}`}>
                    {finding.severity}
                  </span>
                </div>
                {finding.description && (
                  <p className="text-xs text-neutral-400 mt-1">{finding.description}</p>
                )}
                {finding.file && (
                  <p className="text-xs text-neutral-500 mt-1">
                    {finding.file}
                    {finding.line && `:${finding.line}`}
                  </p>
                )}
                {finding.recommendation && (
                  <div className="mt-2 bg-black/20 rounded p-2">
                    <p className="text-xs text-orange-300">Recommendation:</p>
                    <p className="text-xs text-neutral-400 mt-0.5">{finding.recommendation}</p>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}

        {/* No Security Issues */}
        {hasSecurityFindings && artifact.security_findings!.length === 0 && (
          <motion.div
            initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
            animate={animated ? { opacity: 1, scale: 1 } : undefined}
            className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-center"
          >
            <Shield className="w-8 h-8 text-green-400 mx-auto mb-2" />
            <p className="text-sm text-green-300 font-medium">No security vulnerabilities found</p>
          </motion.div>
        )}

        {/* Performance Metrics */}
        {hasPerformanceMetrics && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Performance Metrics
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(artifact.performance_metrics!).map(([key, value]) => (
                <motion.div
                  key={key}
                  initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
                  animate={animated ? { opacity: 1, scale: 1 } : undefined}
                  className="bg-orange-500/5 border border-orange-500/20 rounded px-3 py-2"
                >
                  <p className="text-xs text-orange-400 capitalize">
                    {key.replace(/_/g, " ")}
                  </p>
                  <p className="text-sm font-mono text-orange-300 mt-0.5">{value}</p>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Lint Status */}
        {artifact.lint_status && (
          <motion.div
            initial={animated ? { opacity: 0, y: 20 } : undefined}
            animate={animated ? { opacity: 1, y: 0 } : undefined}
            className={`rounded-lg p-3 border ${getLintStatusColor(artifact.lint_status)}`}
          >
            <div className="flex items-center gap-2">
              {artifact.lint_status === "clean" ? (
                <CheckCircle className="w-5 h-5 text-green-400" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
              )}
              <p className="text-sm font-medium">
                Lint Status: {artifact.lint_status === "clean" ? "Clean ✓" : artifact.lint_status}
              </p>
            </div>
          </motion.div>
        )}

        {/* Quality Score */}
        {artifact.quality_score !== undefined && (
          <motion.div
            initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
            animate={animated ? { opacity: 1, scale: 1 } : undefined}
            className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 text-center"
          >
            <p className="text-3xl font-bold text-orange-400">{artifact.quality_score}/100</p>
            <p className="text-xs text-orange-300 mt-1">Overall Quality Score</p>
          </motion.div>
        )}
      </div>
    </div>
  );
}

// Test Scenario Card
function TestScenarioCard({
  scenario,
  index,
  animated,
}: {
  scenario: TestScenario;
  index: number;
  animated?: boolean;
}) {
  const statusIcons = {
    passed: <CheckCircle className="w-4 h-4 text-green-400" />,
    failed: <AlertCircle className="w-4 h-4 text-red-400" />,
    skipped: <Circle className="w-4 h-4 text-yellow-400" />,
    pending: <Clock className="w-4 h-4 text-neutral-400" />,
  };

  const statusColors = {
    passed: "border-green-500/20 bg-green-500/5",
    failed: "border-red-500/20 bg-red-500/5",
    skipped: "border-yellow-500/20 bg-yellow-500/5",
    pending: "border-neutral-500/20 bg-neutral-500/5",
  };

  const status = scenario.status || "pending";

  return (
    <motion.div
      initial={animated ? { opacity: 0, y: 20 } : undefined}
      animate={animated ? { opacity: 1, y: 0 } : undefined}
      transition={{ delay: index * 0.05 }}
      className={`border rounded-lg p-3 ${statusColors[status]}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{statusIcons[status]}</div>
        <div className="flex-1">
          <div className="flex items-start justify-between mb-1">
            <h5 className="text-sm font-medium text-orange-200">{scenario.title}</h5>
            <div className="flex items-center gap-1">
              {scenario.priority && (
                <span className={`text-xs px-2 py-1 rounded ${getPriorityBadgeColor(scenario.priority)}`}>
                  {scenario.priority}
                </span>
              )}
              {scenario.type && (
                <span className="text-xs px-2 py-1 bg-orange-500/10 text-orange-400 rounded border border-orange-500/20">
                  {scenario.type}
                </span>
              )}
            </div>
          </div>

          {scenario.description && (
            <p className="text-xs text-neutral-400 mt-1">{scenario.description}</p>
          )}

          {scenario.tags && scenario.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {scenario.tags.map((tag, i) => (
                <span key={i} className="text-xs px-1.5 py-0.5 bg-orange-500/10 text-orange-400 rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: "bg-red-500/30 text-red-200 border border-red-500/50",
    high: "bg-orange-500/30 text-orange-200 border border-orange-500/50",
    medium: "bg-yellow-500/30 text-yellow-200 border border-yellow-500/50",
    low: "bg-blue-500/30 text-blue-200 border border-blue-500/50",
    info: "bg-neutral-500/30 text-neutral-200 border border-neutral-500/50",
  };
  return colors[severity] || colors.info;
}

function getLintStatusColor(status: string): string {
  const colors: Record<string, string> = {
    clean: "bg-green-500/10 border-green-500/20 text-green-300",
    warnings: "bg-yellow-500/10 border-yellow-500/20 text-yellow-300",
    errors: "bg-red-500/10 border-red-500/20 text-red-300",
  };
  return colors[status] || "bg-neutral-500/10 border-neutral-500/20 text-neutral-300";
}

function getPriorityBadgeColor(priority: string): string {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-300 border border-red-500/30",
    high: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
    medium: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
    low: "bg-green-500/20 text-green-300 border border-green-500/30",
  };
  return colors[priority] || "bg-neutral-500/20 text-neutral-300 border border-neutral-500/30";
}

