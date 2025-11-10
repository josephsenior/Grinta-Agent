import React, { useMemo } from "react";
import { motion } from "framer-motion";
import { Settings, Database, Globe, Lock, Zap, Package } from "lucide-react";
import type { ArchitectSpecArtifact } from "#/types/metasop-artifacts";

export interface ArchitectVisualizationProps {
  artifact: ArchitectSpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: unknown) => void;
}

export function ArchitectVisualization({
  artifact,
  animated = true,
  className = "",
}: ArchitectVisualizationProps) {
  const sections = useMemo(
    () => buildArchitectSections(artifact, animated),
    [artifact, animated],
  );

  if (sections.length === 0) {
    return (
      <div className={`metasop-viz-empty ${className}`}>
        <Settings className="w-12 h-12 text-blue-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">
          No architecture details yet...
        </p>
      </div>
    );
  }

  return (
    <div className={`metasop-viz-architect ${className}`}>
      <div className="metasop-viz-header bg-blue-500/10 border-blue-500/20">
        <Settings className="w-5 h-5 text-blue-400" />
        <h3 className="text-sm font-semibold text-blue-300">Architect</h3>
        <span className="text-xs text-blue-400/60">
          System Design & Architecture
        </span>
      </div>

      <div className="p-4 space-y-6">
        {sections.map((section) => (
          <React.Fragment key={section.key}>{section.node}</React.Fragment>
        ))}
      </div>
    </div>
  );
}

type ArchitectSection = {
  key: string;
  node: React.ReactNode;
};

function buildArchitectSections(
  artifact: ArchitectSpecArtifact,
  animated: boolean,
): ArchitectSection[] {
  const sections: ArchitectSection[] = [];

  if (artifact.system_architecture?.components?.length) {
    sections.push({
      key: "system-components",
      node: (
        <SystemComponentsSection
          components={artifact.system_architecture.components}
          animated={animated}
        />
      ),
    });
  }

  if (artifact.api_endpoints?.length) {
    sections.push({
      key: "api-endpoints",
      node: (
        <ApiEndpointsSection
          endpoints={artifact.api_endpoints}
          animated={animated}
        />
      ),
    });
  }

  if (artifact.database_schema?.length) {
    sections.push({
      key: "database-schema",
      node: (
        <DatabaseSchemaSection
          schemas={artifact.database_schema}
          animated={animated}
        />
      ),
    });
  }

  if (artifact.technical_decisions?.length) {
    sections.push({
      key: "technical-decisions",
      node: (
        <TechnicalDecisionsSection
          decisions={artifact.technical_decisions}
          animated={animated}
        />
      ),
    });
  }

  if (
    artifact.technology_stack &&
    Object.keys(artifact.technology_stack).length
  ) {
    sections.push({
      key: "technology-stack",
      node: (
        <TechnologyStackSection
          stack={artifact.technology_stack}
          animated={animated}
        />
      ),
    });
  }

  return sections;
}

function SectionTitle({
  icon,
  title,
}: {
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <h4 className="text-xs font-medium text-blue-300 uppercase tracking-wide flex items-center gap-2">
      {icon}
      {title}
    </h4>
  );
}

function SystemComponentsSection({
  components,
  animated,
}: {
  components: NonNullable<
    ArchitectSpecArtifact["system_architecture"]
  >["components"];
  animated: boolean;
}) {
  if (!components || components.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <SectionTitle
        icon={<Database className="w-4 h-4" />}
        title={`System Components (${components.length})`}
      />
      <div className="grid grid-cols-1 gap-3">
        {components.map((component, index) => (
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
                  <h5 className="text-sm font-medium text-blue-200">
                    {component.name}
                  </h5>
                  {component.type && (
                    <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded border border-blue-500/30">
                      {component.type}
                    </span>
                  )}
                </div>
                {component.description && (
                  <p className="text-xs text-neutral-400 mt-1">
                    {component.description}
                  </p>
                )}
                {component.technologies?.length ? (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {component.technologies.map((tech, technologyIndex) => (
                      <span
                        key={technologyIndex}
                        className="text-xs px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded"
                      >
                        {String(tech)}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function ApiEndpointsSection({
  endpoints,
  animated,
}: {
  endpoints: NonNullable<ArchitectSpecArtifact["api_endpoints"]>;
  animated: boolean;
}) {
  return (
    <div className="space-y-3">
      <SectionTitle
        icon={<Globe className="w-4 h-4" />}
        title={`API Endpoints (${endpoints.length})`}
      />
      {endpoints.map((endpoint, index) => (
        <motion.div
          key={`${endpoint.path}-${index}`}
          initial={animated ? { opacity: 0, x: -20 } : undefined}
          animate={animated ? { opacity: 1, x: 0 } : undefined}
          transition={{ delay: index * 0.05 }}
          className="bg-blue-500/5 border border-blue-500/20 rounded p-3"
        >
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`text-xs font-mono px-2 py-1 rounded ${getMethodColor(endpoint.method ?? "")}`}
            >
              {endpoint.method}
            </span>
            <code className="text-xs text-blue-300 font-mono">
              {endpoint.path}
            </code>
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
  );
}

function DatabaseSchemaSection({
  schemas,
  animated,
}: {
  schemas: NonNullable<ArchitectSpecArtifact["database_schema"]>;
  animated: boolean;
}) {
  return (
    <div className="space-y-3">
      <SectionTitle
        icon={<Database className="w-4 h-4" />}
        title={`Database Schema (${schemas.length} tables)`}
      />
      {schemas.map((schema, index) => (
        <motion.div
          key={`${schema.table_name}-${index}`}
          initial={animated ? { opacity: 0, y: 20 } : undefined}
          animate={animated ? { opacity: 1, y: 0 } : undefined}
          transition={{ delay: index * 0.05 }}
          className="bg-blue-500/5 border border-blue-500/20 rounded p-3"
        >
          <h5 className="text-sm font-mono text-blue-300 mb-2">
            {schema.table_name}
          </h5>
          {schema.columns?.length ? (
            <div className="text-xs text-neutral-400 space-y-1">
              {schema.columns.slice(0, 5).map((col, columnIndex) => (
                <div key={columnIndex} className="flex items-center gap-2">
                  <span className="text-blue-400">{col.name}</span>
                  <span className="text-neutral-500">{col.type}</span>
                </div>
              ))}
              {schema.columns.length > 5 && (
                <p className="text-neutral-500">
                  + {schema.columns.length - 5} more columns
                </p>
              )}
            </div>
          ) : null}
        </motion.div>
      ))}
    </div>
  );
}

function TechnicalDecisionsSection({
  decisions,
  animated,
}: {
  decisions: NonNullable<ArchitectSpecArtifact["technical_decisions"]>;
  animated: boolean;
}) {
  return (
    <div className="space-y-3">
      <SectionTitle
        icon={<Zap className="w-4 h-4" />}
        title={`Key Decisions (${decisions.length})`}
      />
      {decisions.map((decision, index) => (
        <motion.div
          key={`${decision.decision}-${index}`}
          initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
          animate={animated ? { opacity: 1, scale: 1 } : undefined}
          transition={{ delay: index * 0.05 }}
          className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3"
        >
          <div className="flex items-start justify-between mb-2">
            <h5 className="text-sm font-medium text-blue-200">
              {decision.decision}
            </h5>
            {decision.confidence && (
              <span
                className={`text-xs px-2 py-1 rounded ${getConfidenceColor(decision.confidence)}`}
              >
                {decision.confidence}
              </span>
            )}
          </div>
          {decision.rationale && (
            <p className="text-xs text-neutral-400 mt-2">
              {decision.rationale}
            </p>
          )}
          {decision.alternatives?.length ? (
            <div className="mt-2">
              <p className="text-xs text-blue-400 mb-1">
                Alternatives considered:
              </p>
              <ul className="text-xs text-neutral-500 space-y-0.5 pl-4">
                {decision.alternatives.map((alt, alternativeIndex) => (
                  <li key={alternativeIndex}>• {String(alt)}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </motion.div>
      ))}
    </div>
  );
}

function TechnologyStackSection({
  stack,
  animated,
}: {
  stack: NonNullable<ArchitectSpecArtifact["technology_stack"]>;
  animated: boolean;
}) {
  const entries = Object.entries(stack);

  return (
    <div className="space-y-2">
      <SectionTitle
        icon={<Package className="w-4 h-4" />}
        title="Technology Stack"
      />
      <div className="grid grid-cols-2 gap-2">
        {entries.map(([key, value], index) => (
          <motion.div
            key={key}
            initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
            animate={animated ? { opacity: 1, scale: 1 } : undefined}
            transition={{ delay: index * 0.03 }}
            className="bg-blue-500/5 border border-blue-500/20 rounded px-3 py-2"
          >
            <p className="text-xs text-blue-400">{key}</p>
            <p className="text-xs text-neutral-300 font-mono">
              {String(value)}
            </p>
          </motion.div>
        ))}
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
  return (
    colors[method] ||
    "bg-neutral-500/20 text-neutral-300 border border-neutral-500/30"
  );
}

function getConfidenceColor(confidence: string): string {
  const colors: Record<string, string> = {
    high: "bg-green-500/20 text-green-300 border border-green-500/30",
    medium: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
    low: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
  };
  return (
    colors[confidence] ||
    "bg-neutral-500/20 text-neutral-300 border border-neutral-500/30"
  );
}
