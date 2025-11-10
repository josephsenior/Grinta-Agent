import React from "react";
import { motion } from "framer-motion";
import {
  User,
  FileText,
  CheckCircle,
  Circle,
  Clock,
  Activity,
  TrendingUp,
} from "lucide-react";
import type {
  PMSpecArtifact,
  UserStory,
  AcceptanceCriteria,
} from "#/types/metasop-artifacts";
import { getPriorityBadgeClass } from "./shared";

export interface PMVisualizationProps {
  artifact: PMSpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: unknown) => void;
}

export function PMVisualization({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: PMVisualizationProps) {
  const sections = buildPmSections({ artifact, animated, onInteraction });

  if (sections.length === 0) {
    return (
      <div className={`metasop-viz-empty ${className}`}>
        <User className="w-12 h-12 text-purple-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">
          No product specifications yet...
        </p>
      </div>
    );
  }

  return (
    <div className={`metasop-viz-pm ${className}`}>
      <div className="metasop-viz-header bg-purple-500/10 border-purple-500/20">
        <User className="w-5 h-5 text-purple-400" />
        <h3 className="text-sm font-semibold text-purple-300">
          Product Manager
        </h3>
        <span className="text-xs text-purple-400/60">
          Requirements & User Stories
        </span>
      </div>

      <div className="p-4 space-y-6">{sections}</div>
    </div>
  );
}

const buildPmSections = ({
  artifact,
  animated,
  onInteraction,
}: {
  artifact: PMSpecArtifact;
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) => {
  const sections: React.ReactNode[] = [];

  if (artifact.epics && artifact.epics.length > 0) {
    sections.push(renderEpicsSection({ epics: artifact.epics, animated }));
  }

  if (artifact.user_stories && artifact.user_stories.length > 0) {
    sections.push(
      renderUserStoriesSection({
        userStories: artifact.user_stories,
        animated,
        onInteraction,
      }),
    );
  }

  if (artifact.acceptance_criteria && artifact.acceptance_criteria.length > 0) {
    sections.push(
      renderAcceptanceCriteriaSection({
        acceptanceCriteria: artifact.acceptance_criteria,
        animated,
      }),
    );
  }

  if (artifact.success_metrics && artifact.success_metrics.length > 0) {
    sections.push(
      renderSuccessMetricsSection({
        successMetrics: artifact.success_metrics,
        animated,
      }),
    );
  }

  return sections;
};

const renderEpicsSection = ({
  epics,
  animated,
}: {
  epics: NonNullable<PMSpecArtifact["epics"]>;
  animated: boolean;
}) => (
  <div className="space-y-3" key="epics">
    <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
      <FileText className="w-4 h-4" />
      Epics
    </h4>
    {epics.map((epic, index) => (
      <motion.div
        key={epic.id || index}
        initial={animated ? { opacity: 0, x: -20 } : undefined}
        animate={animated ? { opacity: 1, x: 0 } : undefined}
        transition={{ delay: index * 0.1 }}
        className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h5 className="text-sm font-medium text-purple-200">
              {epic.title}
            </h5>
            {epic.description && (
              <p className="text-xs text-neutral-400 mt-1">
                {epic.description}
              </p>
            )}
            {epic.stories && epic.stories.length > 0 && (
              <div className="mt-2 text-xs text-purple-400">
                {epic.stories.length}{" "}
                {epic.stories.length === 1 ? "story" : "stories"}
              </div>
            )}
          </div>
        </div>
      </motion.div>
    ))}
  </div>
);

const renderUserStoriesSection = ({
  userStories,
  animated,
  onInteraction,
}: {
  userStories: NonNullable<PMSpecArtifact["user_stories"]>;
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) => (
  <div className="space-y-3" key="user-stories">
    <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
      <User className="w-4 h-4" />
      User Stories ({userStories.length})
    </h4>
    {userStories.map((story, index) => (
      <UserStoryCard
        key={story.id || index}
        story={story}
        index={index}
        animated={animated}
        onClick={() => onInteraction?.("story_click", story)}
      />
    ))}
  </div>
);

const renderAcceptanceCriteriaSection = ({
  acceptanceCriteria,
  animated,
}: {
  acceptanceCriteria: NonNullable<PMSpecArtifact["acceptance_criteria"]>;
  animated: boolean;
}) => (
  <div className="space-y-3" key="acceptance-criteria">
    <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
      <CheckCircle className="w-4 h-4" />
      Acceptance Criteria ({acceptanceCriteria.length})
    </h4>
    {acceptanceCriteria.map((criteria, index) => (
      <AcceptanceCriteriaCard
        key={criteria.id || index}
        criteria={criteria}
        index={index}
        animated={animated}
      />
    ))}
  </div>
);

const renderSuccessMetricsSection = ({
  successMetrics,
  animated,
}: {
  successMetrics: NonNullable<PMSpecArtifact["success_metrics"]>;
  animated: boolean;
}) => (
  <div className="space-y-3" key="success-metrics">
    <h4 className="text-xs font-medium text-purple-300 uppercase tracking-wide flex items-center gap-2">
      <TrendingUp className="w-4 h-4" />
      Success Metrics
    </h4>
    {successMetrics.map((metric, index) => (
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
            <span className="text-xs text-purple-400 ml-2">
              Target: {metric.target}
            </span>
          )}
        </div>
        {metric.description && (
          <p className="text-xs text-neutral-400 mt-1">{metric.description}</p>
        )}
      </motion.div>
    ))}
  </div>
);

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
  const priorityClass = getPriorityBadgeClass(story.priority);

  const personaSection = <UserStoryPersonaSection story={story} />;
  const descriptionSection = <UserStoryDescription story={story} />;
  const metadataItems = buildUserStoryMetadata(story);
  const metadataSection = metadataItems.length ? (
    <UserStoryMetadataRow items={metadataItems} />
  ) : null;
  const tagsSection = story.tags?.length ? (
    <UserStoryTags tags={story.tags} />
  ) : null;

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
          <span className={`text-xs px-2 py-1 rounded border ${priorityClass}`}>
            {story.priority.toUpperCase()}
          </span>
        )}
      </div>

      {personaSection}
      {descriptionSection}
      {metadataSection}
      {tagsSection}
    </motion.div>
  );
}

function UserStoryPersonaSection({ story }: { story: UserStory }) {
  if (!story.as_a && !story.i_want && !story.so_that) {
    return null;
  }

  const personaLines = [
    story.as_a && {
      label: "As a",
      value: story.as_a,
    },
    story.i_want && {
      label: "I want",
      value: story.i_want,
    },
    story.so_that && {
      label: "So that",
      value: story.so_that,
    },
  ].filter(Boolean) as Array<{ label: string; value: string }>;

  return (
    <div className="space-y-1 text-xs text-neutral-300 bg-black/20 rounded p-2 border border-purple-500/10">
      {personaLines.map((line, index) => (
        <p key={index}>
          <span className="text-purple-400">{line.label}</span> {line.value}
        </p>
      ))}
    </div>
  );
}

function UserStoryDescription({ story }: { story: UserStory }) {
  if ((story.description || story.story) && !story.as_a) {
    return (
      <p className="text-xs text-neutral-400 mt-2">
        {story.description || story.story}
      </p>
    );
  }
  return null;
}

function buildUserStoryMetadata(story: UserStory) {
  const metadata: Array<{ icon: React.ReactNode; text: string }> = [];

  if (story.estimate) {
    metadata.push({
      icon: <Clock className="w-3 h-3" />,
      text: String(story.estimate),
    });
  }

  if (story.status) {
    metadata.push({
      icon: <Activity className="w-3 h-3" />,
      text: story.status,
    });
  }

  return metadata;
}

function UserStoryMetadataRow({
  items,
}: {
  items: Array<{ icon: React.ReactNode; text: string }>;
}) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="flex items-center gap-3 mt-3 text-xs text-neutral-500">
      {items.map((item, index) => (
        <span key={index} className="flex items-center gap-1">
          {item.icon}
          {item.text}
        </span>
      ))}
    </div>
  );
}

function UserStoryTags({ tags }: { tags: string[] }) {
  if (!tags.length) {
    return null;
  }

  return (
    <div className="flex gap-1 mt-3">
      {tags.map((tag, index) => (
        <span
          key={index}
          className="px-1.5 py-0.5 bg-purple-500/20 rounded text-purple-300 text-xs"
        >
          {tag}
        </span>
      ))}
    </div>
  );
}

function AcceptanceCriteriaCard({
  criteria,
  index,
  animated,
}: {
  criteria: AcceptanceCriteria;
  index: number;
  animated?: boolean;
}) {
  const [isCompleted, setIsCompleted] = React.useState<boolean>(() =>
    Boolean(criteria.completed),
  );

  const bddSection = buildBddSection(criteria);
  const scenarioSection = buildScenarioSection(criteria);

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
          <p
            className={`text-sm ${
              isCompleted ? "line-through text-neutral-500" : "text-neutral-300"
            }`}
          >
            {criteria.criteria || criteria.description}
          </p>

          {bddSection}
          {scenarioSection}
        </div>
      </div>
    </motion.div>
  );
}

function buildBddSection(criteria: AcceptanceCriteria) {
  if (!criteria.given && !criteria.when && !criteria.then) {
    return null;
  }

  const entries = [
    criteria.given && { label: "Given", value: criteria.given },
    criteria.when && { label: "When", value: criteria.when },
    criteria.then && { label: "Then", value: criteria.then },
  ].filter(Boolean) as Array<{ label: string; value: string }>;

  return (
    <div className="mt-2 space-y-1 text-xs text-neutral-400 bg-black/20 rounded p-2 border border-purple-500/10">
      {entries.map((entry, index) => (
        <p key={index}>
          <span className="text-purple-400">{entry.label}</span> {entry.value}
        </p>
      ))}
    </div>
  );
}

function buildScenarioSection(criteria: AcceptanceCriteria) {
  if (!criteria.scenario || criteria.given) {
    return null;
  }

  return <p className="text-xs text-neutral-500 mt-1">{criteria.scenario}</p>;
}
