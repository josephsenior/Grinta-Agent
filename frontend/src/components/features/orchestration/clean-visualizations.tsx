import React from "react";
import { AlertCircle } from "lucide-react";
import type {
  ParsedArtifact,
  PMSpecArtifact,
  ArchitectSpecArtifact,
  EngineerSpecArtifact,
  QASpecArtifact,
  VisualizationProps,
} from "#/types/metasop-artifacts";
import { PMVisualization } from "./clean-visualizations/pm-visualization";
import { ArchitectVisualization } from "./clean-visualizations/architect-visualization";
import { EngineerVisualization } from "./clean-visualizations/engineer-visualization";
import { QAVisualization } from "./clean-visualizations/qa-visualization";

export { getPriorityBadgeClass } from "./clean-visualizations/shared";

type VisualizationRenderer = (params: {
  artifact: ParsedArtifact["data"];
  animated?: boolean;
  className?: string;
  onInteraction?: VisualizationProps["onInteraction"];
}) => JSX.Element;

const ROLE_VISUALIZATIONS: Record<ParsedArtifact["role"], VisualizationRenderer> = {
  product_manager: ({ artifact, ...rest }) => (
    <PMVisualization artifact={artifact as PMSpecArtifact} {...rest} />
  ),
  architect: ({ artifact, ...rest }) => (
    <ArchitectVisualization artifact={artifact as ArchitectSpecArtifact} {...rest} />
  ),
  engineer: ({ artifact, ...rest }) => (
    <EngineerVisualization artifact={artifact as EngineerSpecArtifact} {...rest} />
  ),
  qa: ({ artifact, ...rest }) => (
    <QAVisualization artifact={artifact as QASpecArtifact} {...rest} />
  ),
};

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

  const renderer = ROLE_VISUALIZATIONS[artifact.role];

  if (!renderer) {
      return (
        <div className={`metasop-viz-unknown ${className}`}>
          <p>Unknown role: {artifact.role}</p>
        </div>
      );
  }

  return renderer({
    artifact: artifact.data,
  animated,
    className,
  onInteraction,
  });
}


