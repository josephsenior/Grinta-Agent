import React from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  Code,
  FolderOpen,
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  Play,
  Package,
  Terminal,
  CheckCircle,
  Circle,
  Clock,
} from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import type {
  EngineerSpecArtifact,
  FileNode,
  ImplementationStep,
} from "#/types/metasop-artifacts";
import { cn } from "#/utils/utils";

export interface EngineerVisualizationProps {
  artifact: EngineerSpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: unknown) => void;
}

// Helper functions
const isNodeFolder = (node: FileNode) =>
  node.type === "folder" ||
  node.type === "directory" ||
  Boolean(node.children && node.children.length > 0);

const renderFileTreeLeadingIcons = ({
  isFolder,
  isExpanded,
}: {
  isFolder: boolean;
  isExpanded: boolean;
}) => {
  if (!isFolder) {
    return (
      <>
        <span className="w-3 h-3" />
        <File className="w-4 h-4 text-neutral-500" />
      </>
    );
  }

  const ChevronIcon = isExpanded ? ChevronDown : ChevronRight;
  const FolderIcon = isExpanded ? FolderOpen : Folder;

  return (
    <>
      <ChevronIcon className="w-3 h-3 text-green-400" />
      <FolderIcon className="w-4 h-4 text-green-400" />
    </>
  );
};

function ImplementationStepFileList({
  title,
  items,
  titleClassName,
}: {
  title: string;
  items: string[];
  titleClassName: string;
}) {
  return (
    <div>
      <span className={titleClassName}>{title}:</span>
      <ul className="text-neutral-500 pl-4 mt-0.5">
        {items.map((file, index) => (
          <li key={index}>• {file}</li>
        ))}
      </ul>
    </div>
  );
}

function buildFileSections(step: ImplementationStep) {
  const sections: React.ReactNode[] = [];

  if (step.files_to_create && step.files_to_create.length > 0) {
    sections.push(
      <ImplementationStepFileList
        key="create"
        title="Create"
        items={step.files_to_create}
        titleClassName="text-green-400"
      />,
    );
  }

  if (step.files_to_modify && step.files_to_modify.length > 0) {
    sections.push(
      <ImplementationStepFileList
        key="modify"
        title="Modify"
        items={step.files_to_modify}
        titleClassName="text-yellow-400"
      />,
    );
  }

  if (sections.length === 0) {
    return null;
  }

  return <div className="mt-2 text-xs space-y-1">{sections}</div>;
}

function CommandSection({ commands }: { commands?: string[] }) {
  const { t } = useTranslation();

  if (!commands || commands.length === 0) {
    return null;
  }

  return (
    <div className="mt-2">
      <p className="text-xs text-green-400 mb-1">
        {t(I18nKey.ORCHESTRATION$COMMANDS)}
      </p>
      {commands.map((cmd, index) => (
        <div
          key={index}
          className="bg-black/40 border border-green-500/20 rounded px-2 py-1 mb-1"
        >
          <code className="text-xs text-green-300 font-mono">{cmd}</code>
        </div>
      ))}
    </div>
  );
}

// Leaf components
function FileTreeNode({
  node,
  depth,
  animated,
  index,
  onInteraction,
}: {
  node: FileNode;
  depth: number;
  animated?: boolean;
  index: number;
  onInteraction?: (action: string, data: unknown) => void;
}) {
  const [isExpanded, setIsExpanded] = React.useState(depth < 2);
  const isFolder = isNodeFolder(node);

  const toggleExpanded = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isFolder) {
      setIsExpanded((prev) => !prev);
    }
  };

  const handleNodeClick = () => {
    onInteraction?.("file_node_click", { node, isFolder, depth });
  };

  return (
    <motion.div
      initial={animated ? { opacity: 0, x: -10 } : undefined}
      animate={animated ? { opacity: 1, x: 0 } : undefined}
      transition={{ delay: index * 0.02 }}
      style={{ paddingLeft: `${depth * 16}px` }}
      className="select-none"
    >
      <div className="flex items-center gap-2 py-1 hover:bg-green-500/5 rounded group">
        <div
          onClick={toggleExpanded}
          className="flex items-center gap-2 cursor-pointer"
        >
          {renderFileTreeLeadingIcons({ isFolder, isExpanded })}
        </div>
        <span
          className={cn(
            "text-xs cursor-pointer flex-1",
            isFolder ? "text-green-300 font-medium" : "text-neutral-400",
          )}
          onClick={handleNodeClick}
        >
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
          {node.children.map((child, childIndex) => (
            <FileTreeNode
              key={childIndex}
              node={child}
              depth={depth + 1}
              animated={animated}
              index={childIndex}
              onInteraction={onInteraction}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}

function CommandList({
  title,
  commands,
}: {
  title: string;
  commands: string[];
}) {
  return (
    <div>
      <p className="text-xs text-green-400 mb-1">{title}:</p>
      {commands.map((cmd, i) => (
        <div
          key={i}
          className="bg-black/40 border border-green-500/20 rounded px-3 py-2 mb-1"
        >
          <code className="text-xs text-green-300 font-mono">{cmd}</code>
        </div>
      ))}
    </div>
  );
}

function ImplementationStepCard({
  step,
  index,
  animated,
  onInteraction,
}: {
  step: ImplementationStep;
  index: number;
  animated?: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) {
  const { t } = useTranslation();
  const [isCompleted, setIsCompleted] = React.useState(step.completed || false);

  const fileSections = buildFileSections(step);

  return (
    <motion.div
      initial={animated ? { opacity: 0, x: -20 } : undefined}
      animate={animated ? { opacity: 1, x: 0 } : undefined}
      transition={{ delay: index * 0.1 }}
      className={cn(
        "bg-green-500/5 border border-green-500/20 rounded-lg p-3 hover:bg-green-500/10 transition-colors cursor-pointer",
        isCompleted && "opacity-60",
      )}
      onClick={() => onInteraction?.("step_click", step)}
    >
      <div className="flex items-start gap-3">
        <button
          type="button"
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
              {t(I18nKey.ORCHESTRATION$STEP, {
                number: step.step_number || index + 1,
              })}
            </span>
            {step.estimated_time && (
              <span className="text-xs text-neutral-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {step.estimated_time}
              </span>
            )}
          </div>
          <h5
            className={cn(
              "text-sm font-medium",
              isCompleted ? "line-through text-neutral-500" : "text-green-200",
            )}
          >
            {step.title}
          </h5>
          {step.description && (
            <p className="text-xs text-neutral-400 mt-1">{step.description}</p>
          )}
          {fileSections}
          <CommandSection commands={step.commands} />
        </div>
      </div>
    </motion.div>
  );
}

// Section components
function EngineerFileStructureSection({
  fileStructure,
  animated,
  onInteraction,
}: {
  fileStructure: FileNode[];
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
        <FolderOpen className="w-4 h-4" />
        {t(I18nKey.ORCHESTRATION$FILE_STRUCTURE)}
      </h4>
      <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-3">
        {fileStructure.map((node, index) => (
          <FileTreeNode
            key={index}
            node={node}
            depth={0}
            animated={animated}
            index={index}
            onInteraction={onInteraction}
          />
        ))}
      </div>
    </div>
  );
}

function EngineerImplementationPlanSection({
  implementationPlan,
  animated,
  onInteraction,
}: {
  implementationPlan: ImplementationStep[];
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
        <Play className="w-4 h-4" />
        {t(I18nKey.ORCHESTRATION$IMPLEMENTATION_STEPS, {
          count: implementationPlan.length,
        })}
      </h4>
      {implementationPlan.map((step, index) => (
        <ImplementationStepCard
          key={index}
          step={step}
          index={index}
          animated={animated}
          onInteraction={onInteraction}
        />
      ))}
    </div>
  );
}

function EngineerDependenciesSection({
  dependencies,
  animated,
}: {
  dependencies: NonNullable<EngineerSpecArtifact["dependencies"]>;
  animated: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
        <Package className="w-4 h-4" />
        {t(I18nKey.ORCHESTRATION$DEPENDENCIES, { count: dependencies.length })}
      </h4>
      <div className="grid grid-cols-2 gap-2">
        {dependencies.map((dep, index) => (
          <motion.div
            key={index}
            initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
            animate={animated ? { opacity: 1, scale: 1 } : undefined}
            transition={{ delay: index * 0.02 }}
            className={cn(
              "bg-green-500/5 border rounded px-3 py-2",
              dep.dev ? "border-green-500/10" : "border-green-500/20",
            )}
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-mono text-green-300">{dep.name}</p>
              {dep.dev && (
                <span className="text-xs text-neutral-500">
                  {t(I18nKey.ORCHESTRATION$DEV)}
                </span>
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
  );
}

function EngineerCommandsSection({
  setup,
  run,
  test,
}: {
  setup?: string[];
  run?: string[];
  test?: string[];
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-green-300 uppercase tracking-wide flex items-center gap-2">
        <Terminal className="w-4 h-4" />
        {t(I18nKey.ORCHESTRATION$COMMANDS_TITLE)}
      </h4>
      {setup?.length ? <CommandList title="Setup" commands={setup} /> : null}
      {run?.length ? <CommandList title="Run" commands={run} /> : null}
      {test?.length ? <CommandList title="Test" commands={test} /> : null}
    </div>
  );
}

function EngineerEffortSection({
  estimatedEffort,
}: {
  estimatedEffort: string;
}) {
  const { t } = useTranslation();
  return (
    <div className="bg-green-500/5 border border-green-500/20 rounded p-3">
      <p className="text-xs text-green-400 mb-1">
        {t(I18nKey.ORCHESTRATION$ESTIMATED_EFFORT)}
      </p>
      <p className="text-sm text-green-300">{estimatedEffort}</p>
    </div>
  );
}

// Builder function
function buildSections({
  artifact,
  animated,
  onInteraction,
}: {
  artifact: EngineerSpecArtifact;
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}): React.ReactNode[] {
  const sections: React.ReactNode[] = [];

  if (artifact.file_structure?.length) {
    sections.push(
      <EngineerFileStructureSection
        key="file-structure"
        fileStructure={artifact.file_structure}
        animated={animated}
        onInteraction={onInteraction}
      />,
    );
  }

  if (artifact.implementation_plan?.length) {
    sections.push(
      <EngineerImplementationPlanSection
        key="implementation-plan"
        implementationPlan={artifact.implementation_plan}
        animated={animated}
        onInteraction={onInteraction}
      />,
    );
  }

  if (artifact.dependencies?.length) {
    sections.push(
      <EngineerDependenciesSection
        key="dependencies"
        dependencies={artifact.dependencies}
        animated={animated}
      />,
    );
  }

  if (
    artifact.setup_commands?.length ||
    artifact.run_commands?.length ||
    artifact.test_commands?.length
  ) {
    sections.push(
      <EngineerCommandsSection
        key="commands"
        setup={artifact.setup_commands}
        run={artifact.run_commands}
        test={artifact.test_commands}
      />,
    );
  }

  if (artifact.estimated_effort) {
    sections.push(
      <EngineerEffortSection
        key="effort"
        estimatedEffort={artifact.estimated_effort}
      />,
    );
  }

  return sections;
}

// Main component
export function EngineerVisualization({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: EngineerVisualizationProps) {
  const { t } = useTranslation();
  const sections = buildSections({ artifact, animated, onInteraction });

  if (sections.length === 0) {
    return (
      <div className={cn("metasop-viz-empty", className)}>
        <Code className="w-12 h-12 text-green-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">
          No implementation details yet...
        </p>
      </div>
    );
  }

  return (
    <div className={cn("metasop-viz-engineer", className)}>
      <div className="metasop-viz-header bg-green-500/10 border-green-500/20">
        <Code className="w-5 h-5 text-green-400" />
        <h3 className="text-sm font-semibold text-green-300">
          {t(I18nKey.ORCHESTRATION$ENGINEER)}
        </h3>
        <span className="text-xs text-green-400/60">
          {t(I18nKey.ORCHESTRATION$IMPLEMENTATION_PLAN)}
        </span>
      </div>

      <div className="p-4 space-y-6">{sections}</div>
    </div>
  );
}
