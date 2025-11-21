import React from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
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
}) => React.JSX.Element;

const ROLE_VISUALIZATIONS: Record<
  ParsedArtifact["role"],
  VisualizationRenderer
> = {
  product_manager: ({ artifact, animated, className, onInteraction }) => (
    <PMVisualization
      artifact={artifact as PMSpecArtifact}
      animated={animated}
      className={className}
      onInteraction={onInteraction}
    />
  ),
  architect: ({ artifact, animated, className, onInteraction }) => (
    <ArchitectVisualization
      artifact={artifact as ArchitectSpecArtifact}
      animated={animated}
      className={className}
      onInteraction={onInteraction}
    />
  ),
  engineer: ({ artifact, animated, className, onInteraction }) => (
    <EngineerVisualization
      artifact={artifact as EngineerSpecArtifact}
      animated={animated}
      className={className}
      onInteraction={onInteraction}
    />
  ),
  qa: ({ artifact, animated, className, onInteraction }) => (
    <QAVisualization
      artifact={artifact as QASpecArtifact}
      animated={animated}
      className={className}
      onInteraction={onInteraction}
    />
  ),
};

export function CleanVisualAdapter({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: VisualizationProps) {
  const { t } = useTranslation();
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
        <p>{t(I18nKey.ORCHESTRATION$UNKNOWN_ROLE, { role: artifact.role })}</p>
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
