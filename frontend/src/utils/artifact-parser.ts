/**
 * MetaSOP Artifact Parser
 *
 * Robust, type-safe parser for MetaSOP agent artifacts
 * Handles __raw__ field unwrapping and validation
 */

import type {
  AgentRole,
  ArtifactData,
  ParsedArtifact,
  PMSpecArtifact,
  ArchitectSpecArtifact,
  EngineerSpecArtifact,
  QASpecArtifact,
  UserStory,
  AcceptanceCriteria,
  FileNode,
} from "#/types/metasop-artifacts";
import {
  isAPIEndpoint,
  isSystemComponent,
  isDatabaseColumn,
  isTestScenario,
  isSecurityFinding,
} from "./artifact-validators";

// ============================================================================
// MAIN PARSER
// ============================================================================

function unwrapRawData(rawData: unknown) {
  if (
    rawData &&
    typeof rawData === "object" &&
    "__raw__" in (rawData as Record<string, unknown>)
  ) {
    const rawValue = (rawData as Record<string, unknown>).__raw__;
    if (typeof rawValue === "string") {
      try {
        return JSON.parse(rawValue);
      } catch {
        // fall back to original raw data
      }
    }
  }

  return rawData;
}

function buildParseErrorResult(
  role: AgentRole,
  timestamp: string,
  error: unknown,
): ParsedArtifact {
  return {
    role,
    data: {} as ArtifactData,
    error: error instanceof Error ? error.message : "Failed to parse artifact",
    timestamp,
  };
}

// ============================================================================
// NORMALIZATION UTILITIES
// ============================================================================

let idCounter = 0;

function generateId(): string {
  idCounter += 1;
  return `artifact_${Date.now()}_${idCounter}`;
}

function normalizePriority(
  priority: unknown,
): "high" | "medium" | "low" | "critical" {
  if (typeof priority !== "string") {
    return "medium";
  }

  const p = priority.toLowerCase();
  if (p === "critical" || p === "p0") return "critical";
  if (p === "high" || p === "p1") return "high";
  if (p === "low" || p === "p3") return "low";
  return "medium";
}

function normalizeStatus(
  status: unknown,
): "pending" | "in_progress" | "complete" | "blocked" {
  if (typeof status !== "string") {
    return "pending";
  }

  const normalized = status.toLowerCase().replace(/[_-]/g, "");
  if (
    normalized === "complete" ||
    normalized === "done" ||
    normalized === "completed"
  ) {
    return "complete";
  }
  if (
    normalized === "inprogress" ||
    normalized === "active" ||
    normalized === "working"
  ) {
    return "in_progress";
  }
  if (normalized === "blocked" || normalized === "stuck") {
    return "blocked";
  }
  return "pending";
}

function normalizeTestStatus(
  status: unknown,
): "passed" | "failed" | "skipped" | "pending" {
  if (typeof status !== "string") {
    return "pending";
  }

  const normalized = status.toLowerCase();
  if (
    normalized === "passed" ||
    normalized === "pass" ||
    normalized === "success"
  ) {
    return "passed";
  }
  if (
    normalized === "failed" ||
    normalized === "fail" ||
    normalized === "error"
  ) {
    return "failed";
  }
  if (normalized === "skipped" || normalized === "skip") {
    return "skipped";
  }
  return "pending";
}

function normalizeEstimate(value: unknown): string | undefined {
  if (value == null) return undefined;
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  return undefined;
}

function normalizeToStringOrUndefined(value: unknown): string | undefined {
  if (value == null) return undefined;
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function normalizeToNumberOrUndefined(value: unknown): number | undefined {
  if (value == null) return undefined;
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function normalizeComponentType(
  value: unknown,
): "service" | "database" | "cache" | "queue" | "api" | "client" {
  if (typeof value !== "string") return "service";
  const normalized = value.toLowerCase();
  if (normalized.includes("db") || normalized.includes("database"))
    return "database";
  if (normalized.includes("cache")) return "cache";
  if (normalized.includes("queue")) return "queue";
  if (normalized.includes("api")) return "api";
  if (normalized.includes("client")) return "client";
  return "service";
}

function normalizeHttpMethod(
  value: unknown,
): "GET" | "POST" | "PUT" | "PATCH" | "DELETE" {
  if (typeof value !== "string") return "GET";
  const method = value.toUpperCase();
  if (method === "POST") return "POST";
  if (method === "PUT") return "PUT";
  if (method === "PATCH") return "PATCH";
  if (method === "DELETE") return "DELETE";
  return "GET";
}

function normalizeFileNodeType(
  value: unknown,
): "file" | "folder" | "directory" {
  if (typeof value !== "string") {
    return "file";
  }
  const normalized = value.toLowerCase();
  if (
    normalized === "folder" ||
    normalized === "directory" ||
    normalized === "dir"
  ) {
    return "folder";
  }
  if (normalized === "file") {
    return "file";
  }
  return "file";
}

function normalizeTestType(
  value: unknown,
): "unit" | "integration" | "e2e" | "performance" | "security" {
  if (typeof value !== "string") return "unit";
  const normalized = value.toLowerCase();
  if (normalized === "integration") return "integration";
  if (normalized === "e2e") return "e2e";
  if (normalized === "performance") return "performance";
  if (normalized === "security") return "security";
  return "unit";
}

function normalizeSeverity(
  value: unknown,
): "critical" | "high" | "medium" | "low" | "info" {
  if (typeof value !== "string") return "info";
  const normalized = value.toLowerCase();
  if (normalized === "critical") return "critical";
  if (normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  if (normalized === "low") return "low";
  return "info";
}

function normalizeConfidence(value: unknown): "high" | "medium" | "low" {
  if (typeof value !== "string") {
    return "medium";
  }
  const normalized = value.toLowerCase();
  if (normalized === "high") return "high";
  if (normalized === "low") return "low";
  return "medium";
}

function normalizeNumberMetric(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return 0;
}

// ============================================================================
// PRODUCT MANAGER PARSER
// ============================================================================

function resolveFirstString(
  source: Record<string, unknown>,
  keys: string[],
  fallback?: string,
) {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }
  }
  return fallback;
}

function createUserStory(story: unknown): UserStory {
  const s = story as Record<string, unknown>;
  const title = resolveFirstString(s, ["title", "name"], "Untitled Story");
  const description = resolveFirstString(s, ["description", "desc"]);
  const asA = resolveFirstString(s, ["as_a", "user_type"]);
  const iWant = resolveFirstString(s, ["i_want", "want"]);
  const soThat = resolveFirstString(s, ["so_that", "benefit"]);
  const estimate = resolveFirstString(s, ["estimate", "story_points"]);

  return {
    id: (s.id as string) || (s.story_id as string) || generateId(),
    title,
    story: s.story as string,
    description,
    as_a: asA,
    i_want: iWant,
    so_that: soThat,
    priority: normalizePriority(s.priority),
    estimate: normalizeEstimate(estimate),
    status: normalizeStatus(s.status),
    tags: Array.isArray(s.tags) ? (s.tags as unknown[]).map(String) : [],
  } as UserStory;
}

function parsePMSpec(data: unknown): PMSpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const artifact: PMSpecArtifact = {};
  const obj = data as Record<string, unknown>;

  // Parse user stories
  if (Array.isArray(obj.user_stories)) {
    artifact.user_stories = obj.user_stories
      .filter((story: unknown) => story && typeof story === "object")
      .map((story: unknown): UserStory => createUserStory(story));
  }

  // Parse acceptance criteria
  if (Array.isArray(obj.acceptance_criteria)) {
    artifact.acceptance_criteria = obj.acceptance_criteria
      .filter((criteria: unknown) => criteria && typeof criteria === "object")
      .map((criteria: unknown): AcceptanceCriteria => {
        const c = criteria as Record<string, unknown>;
        return {
          id: (c.id as string) || generateId(),
          criteria: (c.criteria as string) || (c.description as string),
          description: (c.description as string) || (c.detail as string),
          scenario: c.scenario as string | undefined,
          given: c.given as string | undefined,
          when: c.when as string | undefined,
          then: c.then as string | undefined,
          completed: Boolean(c.completed),
        } as AcceptanceCriteria;
      });
  }

  // Parse epics
  if (Array.isArray(obj.epics)) {
    artifact.epics = obj.epics.map((epic: unknown) => {
      const e = epic as Record<string, unknown>;
      return {
        id: (e.id as string) || generateId(),
        title: (e.title as string) || (e.name as string) || "Untitled Epic",
        description: e.description as string | undefined,
        stories: Array.isArray(e.stories)
          ? (e.stories as unknown[]).map(String)
          : [],
      };
    });
  }

  // Parse success metrics
  if (Array.isArray(obj.success_metrics)) {
    artifact.success_metrics = obj.success_metrics.map((metric: unknown) => {
      const m = metric as Record<string, unknown>;
      return {
        metric: (m.metric as string) || (m.name as string) || "Untitled Metric",
        target: m.target != null ? String(m.target) : undefined,
        description: m.description as string | undefined,
      };
    });
  }

  artifact.priority = normalizePriority(obj.priority);

  return artifact;
}
// ============================================================================
// ARCHITECT PARSER
// ============================================================================

const parseSystemArchitecture = (
  value: unknown,
): ArchitectSpecArtifact["system_architecture"] => {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const arch = value as Record<string, unknown>;
  const components = Array.isArray(arch.components)
    ? (arch.components as unknown[])
        .filter((component) => isSystemComponent(component))
        .map((component) => {
          const comp = component as Record<string, unknown>;
          return {
            id:
              typeof comp.id === "string" || typeof comp.id === "number"
                ? comp.id
                : generateId(),
            name:
              typeof comp.name === "string" ? comp.name : "Unnamed Component",
            type: normalizeComponentType(comp.type),
            description:
              typeof comp.description === "string"
                ? comp.description
                : undefined,
            dependencies: Array.isArray(comp.dependencies)
              ? (comp.dependencies as unknown[]).map(String)
              : [],
            technologies: Array.isArray(comp.technologies)
              ? (comp.technologies as unknown[]).map(String)
              : [],
          };
        })
    : [];

  const connections = Array.isArray(arch.connections)
    ? (arch.connections as unknown[]).map((connection) => {
        const conn = connection as Record<string, unknown>;
        return {
          from: (conn.from as string) || (conn.source as string) || "",
          to: (conn.to as string) || (conn.target as string) || "",
          protocol: conn.protocol as string | undefined,
          description: conn.description as string | undefined,
        };
      })
    : [];

  return {
    components,
    connections,
    diagram: arch.diagram as string | undefined,
  };
};

const parseApiEndpoints = (
  value: unknown,
): ArchitectSpecArtifact["api_endpoints"] => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[])
    .filter((endpoint) => isAPIEndpoint(endpoint))
    .map((endpoint) => {
      const ep = endpoint as Record<string, unknown>;
      return {
        method: normalizeHttpMethod(ep.method),
        path: (ep.path as string) || (ep.url as string) || "/",
        description:
          typeof ep.description === "string" ? ep.description : undefined,
        request_body: normalizeToStringOrUndefined(ep.request_body ?? ep.body),
        response: normalizeToStringOrUndefined(ep.response),
        auth_required: Boolean(ep.auth_required),
        rate_limit: normalizeToStringOrUndefined(ep.rate_limit),
      };
    });
};

const parseDatabaseSchema = (
  value: unknown,
): ArchitectSpecArtifact["database_schema"] => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[]).map((schema) => {
    const s = schema as Record<string, unknown>;
    const columns = Array.isArray(s.columns)
      ? (s.columns as unknown[])
          .filter((column) => isDatabaseColumn(column))
          .map((column) => {
            const col = column as Record<string, unknown>;
            return {
              name:
                (col.name as string) || (col.column_name as string) || "col",
              type:
                (col.type as string) || (col.datatype as string) || "string",
              constraints: Array.isArray(col.constraints)
                ? (col.constraints as unknown[]).map(String)
                : [],
            };
          })
      : [];

    return {
      table_name:
        (s.table_name as string) || (s.name as string) || "unnamed_table",
      columns,
      indexes: Array.isArray(s.indexes)
        ? (s.indexes as unknown[]).map(String)
        : [],
      relationships: Array.isArray(s.relationships)
        ? (s.relationships as unknown[]).map(String)
        : [],
    };
  });
};

const parseTechnicalDecisions = (
  value: unknown,
): ArchitectSpecArtifact["technical_decisions"] => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[]).map((decision) => {
    const d = decision as Record<string, unknown>;
    return {
      decision:
        (d.decision as string) || (d.title as string) || "Untitled Decision",
      rationale: (d.rationale as string) || (d.reason as string) || undefined,
      alternatives: Array.isArray(d.alternatives)
        ? (d.alternatives as unknown[]).map(String)
        : [],
      trade_offs:
        (d.trade_offs as string | undefined) ||
        (d.tradeoffs as string | undefined),
      context: d.context as string | undefined,
      confidence: normalizeConfidence(d.confidence),
    };
  });
};

const parseTechnologyStack = (
  value: unknown,
): ArchitectSpecArtifact["technology_stack"] => {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const stack = value as Record<string, unknown>;
  return Object.fromEntries(
    Object.entries(stack).map(([key, val]) => [
      key,
      val == null ? "" : String(val),
    ]),
  );
};

function parseArchitectSpec(data: unknown): ArchitectSpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const obj = data as Record<string, unknown>;
  const systemArchitecture = parseSystemArchitecture(obj.system_architecture);
  const apiEndpoints = parseApiEndpoints(obj.api_endpoints);
  const databaseSchema = parseDatabaseSchema(obj.database_schema);
  const technicalDecisions = parseTechnicalDecisions(obj.technical_decisions);
  const technologyStack = parseTechnologyStack(obj.technology_stack);

  return {
    ...(systemArchitecture ? { system_architecture: systemArchitecture } : {}),
    ...(apiEndpoints ? { api_endpoints: apiEndpoints } : {}),
    ...(databaseSchema ? { database_schema: databaseSchema } : {}),
    ...(technicalDecisions ? { technical_decisions: technicalDecisions } : {}),
    ...(technologyStack ? { technology_stack: technologyStack } : {}),
    scalability_plan:
      obj.scalability_plan != null ? String(obj.scalability_plan) : undefined,
    security_considerations: Array.isArray(obj.security_considerations)
      ? obj.security_considerations
      : [],
  };
}

// ============================================================================
// ENGINEER PARSER
// ============================================================================

function parseFileNode(node: unknown): FileNode {
  if (!node || typeof node !== "object") {
    return {
      name: "unknown",
      path: "/",
      type: "file",
    };
  }

  const record = node as Record<string, unknown>;
  const children = Array.isArray(record.children)
    ? (record.children as unknown[]).map((child: unknown) =>
        parseFileNode(child),
      )
    : undefined;
  let linesOfCode: number | undefined;

  if (typeof record.lines_of_code === "number") {
    linesOfCode = record.lines_of_code;
  } else if (typeof record.loc === "number") {
    linesOfCode = record.loc;
  }

  return {
    name: (record.name as string) || "unknown",
    path: (record.path as string) || "/",
    type: normalizeFileNodeType(record.type),
    description: record.description as string | undefined,
    purpose: record.purpose as string | undefined,
    children,
    language: record.language as string | undefined,
    lines_of_code: linesOfCode,
  };
}

function parseEngineerSpec(data: unknown): EngineerSpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const artifact: EngineerSpecArtifact = {};
  const obj = data as Record<string, unknown>;

  // Parse file structure
  if (Array.isArray(obj.file_structure)) {
    artifact.file_structure = (obj.file_structure as unknown[]).map(
      (node: unknown) => parseFileNode(node),
    );
  }

  // Parse implementation plan
  if (Array.isArray(obj.implementation_plan)) {
    artifact.implementation_plan = (obj.implementation_plan as unknown[]).map(
      (step: unknown, index: number) => {
        const st = step as Record<string, unknown>;
        let estimatedTime: string | undefined;

        if (st.estimated_time != null) {
          estimatedTime = String(st.estimated_time);
        } else if (st.time != null) {
          estimatedTime = String(st.time);
        }

        return {
          step_number: (st.step_number as number) || index + 1,
          title:
            (st.title as string) || (st.name as string) || `Step ${index + 1}`,
          description: st.description as string | undefined,
          files_to_create: Array.isArray(st.files_to_create)
            ? (st.files_to_create as unknown[]).map(String)
            : [],
          files_to_modify: Array.isArray(st.files_to_modify)
            ? (st.files_to_modify as unknown[]).map(String)
            : [],
          commands: Array.isArray(st.commands)
            ? (st.commands as unknown[]).map(String)
            : [],
          estimated_time: estimatedTime,
          dependencies: Array.isArray(st.dependencies)
            ? (st.dependencies as unknown[]).map(String)
            : [],
          completed: Boolean(st.completed),
        };
      },
    );
  }

  // Parse dependencies
  if (Array.isArray(obj.dependencies)) {
    artifact.dependencies = (obj.dependencies as unknown[]).map(
      (dep: unknown) => {
        const d = dep as Record<string, unknown>;
        return {
          name: (d.name as string) || (d.package as string) || "unknown",
          version: d.version as string | undefined,
          purpose:
            (d.purpose as string) || (d.description as string | undefined),
          dev: Boolean(d.dev || d.devDependency),
        };
      },
    );
  }

  // Parse commands
  artifact.setup_commands = Array.isArray(obj.setup_commands)
    ? obj.setup_commands
    : [];
  artifact.run_commands = Array.isArray(obj.run_commands)
    ? obj.run_commands
    : [];
  artifact.test_commands = Array.isArray(obj.test_commands)
    ? obj.test_commands
    : [];

  // Parse code snippets
  if (Array.isArray(obj.code_snippets)) {
    artifact.code_snippets = (obj.code_snippets as unknown[]).map(
      (snippet: unknown) => {
        const sn = snippet as Record<string, unknown>;
        return {
          file: (sn.file as string) || (sn.filename as string) || "untitled",
          language: (sn.language as string) || (sn.lang as string) || "text",
          code: (sn.code as string) || (sn.content as string) || "",
          description: sn.description as string | undefined,
        };
      },
    );
  }

  artifact.estimated_effort = normalizeToStringOrUndefined(
    obj.estimated_effort,
  );

  return artifact;
}

// ============================================================================
// QA PARSER
// ============================================================================

function parseTestScenarios(value: unknown): QASpecArtifact["test_scenarios"] {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[])
    .filter((scenario) => isTestScenario(scenario))
    .map((scenario) => {
      const record = scenario as Record<string, unknown>;
      const title = resolveFirstString(
        record,
        ["title", "name"],
        "Untitled Test",
      );

      return {
        id: typeof record.id === "string" ? record.id : generateId(),
        title,
        description:
          typeof record.description === "string"
            ? record.description
            : undefined,
        scenario:
          typeof record.scenario === "string" ? record.scenario : undefined,
        priority: normalizePriority(record.priority),
        type: normalizeTestType(record.type),
        tags: Array.isArray(record.tags)
          ? (record.tags as unknown[]).map(String)
          : [],
        steps: Array.isArray(record.steps)
          ? (record.steps as unknown[]).map(String)
          : [],
        expected_result: normalizeToStringOrUndefined(
          record.expected_result ?? record.expected,
        ),
        status: normalizeTestStatus(record.status),
      };
    });
}

function parseTestResults(value: unknown): QASpecArtifact["test_results"] {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const results = value as Record<string, unknown>;
  return {
    passed: typeof results.passed === "number" ? results.passed : 0,
    failed: typeof results.failed === "number" ? results.failed : 0,
    skipped: typeof results.skipped === "number" ? results.skipped : 0,
    total: typeof results.total === "number" ? results.total : 0,
  };
}

function parseCodeCoverage(value: unknown): QASpecArtifact["code_coverage"] {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const coverage = value as Record<string, unknown>;
  return {
    lines: normalizeNumberMetric(coverage.lines),
    statements: normalizeNumberMetric(coverage.statements),
    functions: normalizeNumberMetric(coverage.functions),
    branches: normalizeNumberMetric(coverage.branches),
  };
}

function parseSecurityFindings(
  value: unknown,
): QASpecArtifact["security_findings"] {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[])
    .filter((finding) => isSecurityFinding(finding))
    .map((finding) => {
      const record = finding as Record<string, unknown>;
      const title = resolveFirstString(
        record,
        ["title", "name"],
        "Security Issue",
      );
      const recommendation = resolveFirstString(record, [
        "recommendation",
        "fix",
      ]);

      return {
        severity: normalizeSeverity(record.severity),
        title,
        description:
          typeof record.description === "string"
            ? record.description
            : undefined,
        file: typeof record.file === "string" ? record.file : undefined,
        line: typeof record.line === "number" ? record.line : undefined,
        recommendation,
      };
    });
}

function parsePerformanceMetrics(
  value: unknown,
): QASpecArtifact["performance_metrics"] {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const metrics = value as Record<string, unknown>;
  return {
    api_response_time: normalizeNumberMetric(metrics.api_response_time),
    page_load_time: normalizeNumberMetric(metrics.page_load_time),
    db_query_time: normalizeNumberMetric(metrics.db_query_time),
    memory_usage: normalizeNumberMetric(metrics.memory_usage),
    cpu_usage: normalizeNumberMetric(metrics.cpu_usage),
  };
}

function parseLintStatus(value: unknown): QASpecArtifact["lint_status"] {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return "clean";
}

function parseLintDetails(value: unknown): QASpecArtifact["lint_details"] {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[]).map((detail) =>
    typeof detail === "string" ? detail : String(detail),
  );
}

function parseQASpec(data: unknown): QASpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const artifact: QASpecArtifact = {};
  const obj = data as Record<string, unknown>;

  artifact.test_scenarios = parseTestScenarios(obj.test_scenarios);
  artifact.test_results = parseTestResults(obj.test_results);
  artifact.code_coverage = parseCodeCoverage(obj.code_coverage);
  artifact.security_findings = parseSecurityFindings(obj.security_findings);
  artifact.performance_metrics = parsePerformanceMetrics(
    obj.performance_metrics,
  );
  artifact.lint_status = parseLintStatus(obj.lint_status);
  artifact.lint_details = parseLintDetails(obj.lint_details);
  artifact.quality_score = normalizeToNumberOrUndefined(obj.quality_score);

  return artifact;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// ============================================================================
// VALIDATION
// ============================================================================

type ArtifactValidator = (data: unknown) => boolean;

const hasArrayEntries = (value: unknown): boolean =>
  Array.isArray(value) && value.length > 0;

const anyTrue = (...checks: Array<boolean | undefined>): boolean =>
  checks.some(Boolean);

const ARTIFACT_VALIDATORS: Partial<
  Record<ParsedArtifact["role"], ArtifactValidator>
> = {
  product_manager: (data) => {
    const pmData = data as PMSpecArtifact;
    return anyTrue(
      hasArrayEntries(pmData.user_stories),
      hasArrayEntries(pmData.acceptance_criteria),
    );
  },
  architect: (data) => {
    const archData = data as ArchitectSpecArtifact;
    return anyTrue(
      Boolean(archData.system_architecture),
      hasArrayEntries(archData.api_endpoints),
      hasArrayEntries(archData.technical_decisions),
    );
  },
  engineer: (data) => {
    const engineerData = data as EngineerSpecArtifact;
    return anyTrue(
      hasArrayEntries(engineerData.file_structure),
      hasArrayEntries(engineerData.implementation_plan),
    );
  },
  qa: (data) => {
    const qaData = data as QASpecArtifact;
    return anyTrue(
      hasArrayEntries(qaData.test_scenarios),
      Boolean(qaData.test_results),
    );
  },
};

export function validateArtifact(artifact: ParsedArtifact): boolean {
  if (!artifact?.role || artifact.error) {
    return false;
  }

  const validator = ARTIFACT_VALIDATORS[artifact.role];
  return validator ? validator(artifact.data) : false;
}

const ROLE_PARSERS: Record<AgentRole, (data: unknown) => ArtifactData> = {
  product_manager: (data) => parsePMSpec(data) as ArtifactData,
  architect: (data) => parseArchitectSpec(data) as ArtifactData,
  engineer: (data) => parseEngineerSpec(data) as ArtifactData,
  qa: (data) => parseQASpec(data) as ArtifactData,
};

export function parseArtifact(
  rawData: unknown,
  role: AgentRole,
): ParsedArtifact {
  const timestamp = new Date().toISOString();
  const parser = ROLE_PARSERS[role];

  if (!parser) {
    return buildParseErrorResult(
      role,
      timestamp,
      new Error(`Unknown role: ${role}`),
    );
  }

  try {
    const data = parser(unwrapRawData(rawData));
    return {
      role,
      data,
      timestamp,
    };
  } catch (error) {
    return buildParseErrorResult(role, timestamp, error);
  }
}
