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
import { isAPIEndpoint, isSystemComponent, isDatabaseColumn, isTestScenario, isSecurityFinding } from "./artifact-validators";

// ============================================================================
// MAIN PARSER
// ============================================================================

export function parseArtifact(
  rawData: unknown,
  role: AgentRole
): ParsedArtifact {
  const timestamp = new Date().toISOString();

  try {
    const data = unwrapRawData(rawData);
    const parser = ROLE_PARSERS[role];

    if (!parser) {
      throw new Error(`Unknown role: ${role}`);
    }

    return {
      role,
      data: parser(data),
      timestamp,
    };
  } catch (error) {
    console.error("Artifact parse error:", error);
    return buildParseErrorResult(role, timestamp, error);
  }
}

const ROLE_PARSERS: Record<AgentRole, (data: unknown) => ArtifactData> = {
  product_manager: (data) => parsePMSpec(data) as ArtifactData,
  architect: (data) => parseArchitectSpec(data) as ArtifactData,
  engineer: (data) => parseEngineerSpec(data) as ArtifactData,
  qa: (data) => parseQASpec(data) as ArtifactData,
};

function unwrapRawData(rawData: unknown) {
  if (rawData && typeof rawData === "object" && "__raw__" in (rawData as Record<string, unknown>)) {
    const rawValue = (rawData as Record<string, unknown>).__raw__;
    if (typeof rawValue === "string") {
      try {
        return JSON.parse(rawValue);
      } catch (parseError) {
        console.warn("Failed to parse __raw__ field, using original data");
      }
    }
  }

  return rawData;
}

function buildParseErrorResult(role: AgentRole, timestamp: string, error: unknown): ParsedArtifact {
  return {
    role,
    data: {} as ArtifactData,
    error: error instanceof Error ? error.message : "Failed to parse artifact",
    timestamp,
  };
}

// ============================================================================
// PRODUCT MANAGER PARSER
// ============================================================================

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
        stories: Array.isArray(e.stories) ? (e.stories as unknown[]).map(String) : [],
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

// ============================================================================
// ARCHITECT PARSER
// ============================================================================

const parseSystemArchitecture = (value: unknown): ArchitectSpecArtifact["system_architecture"] => {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const arch = value as Record<string, unknown>;
  const components = Array.isArray(arch.components)
    ? (arch.components as unknown[])
        .filter(component => isSystemComponent(component))
        .map(component => {
          const comp = component as Record<string, unknown>;
          return {
            id:
              typeof comp.id === "string" || typeof comp.id === "number"
                ? comp.id
                : generateId(),
            name: typeof comp.name === "string" ? comp.name : "Unnamed Component",
            type: normalizeComponentType(comp.type),
            description: typeof comp.description === "string" ? comp.description : undefined,
            dependencies: Array.isArray(comp.dependencies) ? (comp.dependencies as unknown[]).map(String) : [],
            technologies: Array.isArray(comp.technologies) ? (comp.technologies as unknown[]).map(String) : [],
          };
        })
    : [];

  const connections = Array.isArray(arch.connections)
    ? (arch.connections as unknown[]).map(connection => {
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

const parseApiEndpoints = (value: unknown): ArchitectSpecArtifact["api_endpoints"] => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[])
    .filter(endpoint => isAPIEndpoint(endpoint))
    .map(endpoint => {
      const ep = endpoint as Record<string, unknown>;
      return {
        method: normalizeHttpMethod(ep.method),
        path: (ep.path as string) || (ep.url as string) || "/",
        description: typeof ep.description === "string" ? ep.description : undefined,
        request_body: normalizeToStringOrUndefined(ep.request_body ?? ep.body),
        response: normalizeToStringOrUndefined(ep.response),
        auth_required: Boolean(ep.auth_required),
        rate_limit: normalizeToStringOrUndefined(ep.rate_limit),
      };
    });
};

const parseDatabaseSchema = (value: unknown): ArchitectSpecArtifact["database_schema"] => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[]).map(schema => {
    const s = schema as Record<string, unknown>;
    const columns = Array.isArray(s.columns)
      ? (s.columns as unknown[])
          .filter(column => isDatabaseColumn(column))
          .map(column => {
            const col = column as Record<string, unknown>;
            return {
              name: (col.name as string) || (col.column_name as string) || "col",
              type: (col.type as string) || (col.datatype as string) || "string",
              constraints: Array.isArray(col.constraints) ? (col.constraints as unknown[]).map(String) : [],
            };
          })
      : [];

    return {
      table_name: (s.table_name as string) || (s.name as string) || "unnamed_table",
      columns,
      indexes: Array.isArray(s.indexes) ? (s.indexes as unknown[]).map(String) : [],
      relationships: Array.isArray(s.relationships) ? (s.relationships as unknown[]).map(String) : [],
    };
  });
};

const parseTechnicalDecisions = (value: unknown): ArchitectSpecArtifact["technical_decisions"] => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[]).map(decision => {
    const d = decision as Record<string, unknown>;
    return {
      decision: (d.decision as string) || (d.title as string) || "Untitled Decision",
      rationale: (d.rationale as string) || (d.reason as string) || undefined,
      alternatives: Array.isArray(d.alternatives) ? (d.alternatives as unknown[]).map(String) : [],
      trade_offs: (d.trade_offs as string | undefined) || (d.tradeoffs as string | undefined),
      context: d.context as string | undefined,
      confidence: normalizeConfidence(d.confidence),
    };
  });
};

const parseTechnologyStack = (value: unknown): ArchitectSpecArtifact["technology_stack"] => {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const stack = value as Record<string, unknown>;
  return Object.fromEntries(Object.entries(stack).map(([key, val]) => [key, val == null ? "" : String(val)]));
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
    scalability_plan: obj.scalability_plan != null ? String(obj.scalability_plan) : undefined,
    security_considerations: Array.isArray(obj.security_considerations) ? obj.security_considerations : [],
  };
}

// ============================================================================
// ENGINEER PARSER
// ============================================================================

function parseEngineerSpec(data: unknown): EngineerSpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const artifact: EngineerSpecArtifact = {};
  const obj = data as Record<string, any>;

  // Parse file structure
  if (Array.isArray(obj.file_structure)) {
    artifact.file_structure = obj.file_structure.map((node: any) =>
      parseFileNode(node)
    );
  }

  // Parse implementation plan
  if (Array.isArray(obj.implementation_plan)) {
    artifact.implementation_plan = (obj.implementation_plan as unknown[]).map(
      (step: unknown, index: number) => {
        const st = step as Record<string, unknown>;
        return {
          step_number: (st.step_number as number) || index + 1,
          title: (st.title as string) || (st.name as string) || `Step ${index + 1}`,
          description: st.description as string | undefined,
          files_to_create: Array.isArray(st.files_to_create) ? (st.files_to_create as unknown[]).map(String) : [],
          files_to_modify: Array.isArray(st.files_to_modify) ? (st.files_to_modify as unknown[]).map(String) : [],
          commands: Array.isArray(st.commands) ? (st.commands as unknown[]).map(String) : [],
          estimated_time: st.estimated_time != null ? String(st.estimated_time) : (st.time != null ? String(st.time) : undefined),
          dependencies: Array.isArray(st.dependencies) ? (st.dependencies as unknown[]).map(String) : [],
          completed: Boolean(st.completed),
        };
      }
    );
  }

  // Parse dependencies
  if (Array.isArray(obj.dependencies)) {
    artifact.dependencies = (obj.dependencies as unknown[]).map((dep: unknown) => {
      const d = dep as Record<string, unknown>;
      return {
        name: (d.name as string) || (d.package as string) || "unknown",
        version: d.version as string | undefined,
        purpose: (d.purpose as string) || (d.description as string | undefined),
        dev: Boolean(d.dev || d.devDependency),
      };
    });
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
    artifact.code_snippets = (obj.code_snippets as unknown[]).map((snippet: unknown) => {
      const sn = snippet as Record<string, unknown>;
      return {
        file: (sn.file as string) || (sn.filename as string) || "untitled",
        language: (sn.language as string) || (sn.lang as string) || "text",
        code: (sn.code as string) || (sn.content as string) || "",
        description: sn.description as string | undefined,
      };
    });
  }

  artifact.estimated_effort = obj.estimated_effort;

  return artifact;
}

function parseFileNode(node: unknown): FileNode {
  if (!node || typeof node !== "object") {
    return {
      name: "unknown",
      path: "/",
      type: "file",
    };
  }

  const n = node as Record<string, unknown>;

  return {
    name: (n.name as string) || "unknown",
    path: (n.path as string) || "/",
    type: normalizeFileNodeType(n.type),
    description: n.description as string | undefined,
    purpose: n.purpose as string | undefined,
    children: Array.isArray(n.children)
      ? (n.children as unknown[]).map((child: unknown) => parseFileNode(child))
      : undefined,
    language: n.language as string | undefined,
    lines_of_code: typeof n.lines_of_code === "number" ? (n.lines_of_code as number) : typeof n.loc === "number" ? (n.loc as number) : undefined,
  };
}

// ============================================================================
// QA PARSER
// ============================================================================

function parseQASpec(data: unknown): QASpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const artifact: QASpecArtifact = {};
  const obj = data as Record<string, any>;

  artifact.test_scenarios = parseTestScenarios(obj.test_scenarios);
  artifact.test_results = parseTestResults(obj.test_results);
  artifact.code_coverage = parseCodeCoverage(obj.code_coverage);
  artifact.security_findings = parseSecurityFindings(obj.security_findings);
  artifact.performance_metrics = parsePerformanceMetrics(
    obj.performance_metrics,
  );
  artifact.lint_status = parseLintStatus(obj.lint_status);
  artifact.lint_details = parseLintDetails(obj.lint_details);
  artifact.quality_score = obj.quality_score;

  return artifact;
}

function parseTestScenarios(value: unknown): QASpecArtifact["test_scenarios"] {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[])
    .filter((scenario) => isTestScenario(scenario))
    .map((scenario: any) => ({
      id: scenario.id || generateId(),
      title: scenario.title || scenario.name || "Untitled Test",
      description:
        typeof scenario.description === "string" ? scenario.description : undefined,
      scenario:
        typeof scenario.scenario === "string" ? scenario.scenario : undefined,
      priority: normalizePriority(scenario.priority),
      type: normalizeTestType(scenario.type),
      tags: Array.isArray(scenario.tags) ? scenario.tags.map(String) : [],
      steps: Array.isArray(scenario.steps) ? scenario.steps.map(String) : [],
      expected_result: normalizeToStringOrUndefined(
        scenario.expected_result ?? scenario.expected,
      ),
      status: normalizeTestStatus(scenario.status),
    }));
}

function parseTestResults(value: unknown): QASpecArtifact["test_results"] {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const results = value as Record<string, unknown>;
  return {
    passed: (results.passed as number) || 0,
    failed: (results.failed as number) || 0,
    skipped: (results.skipped as number) || 0,
    total: (results.total as number) || 0,
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

function parseSecurityFindings(value: unknown): QASpecArtifact["security_findings"] {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return (value as unknown[])
    .filter((finding) => isSecurityFinding(finding))
    .map((finding: any) => ({
      severity: normalizeSeverity(finding.severity),
      title: finding.title || finding.name || "Security Issue",
      description:
        typeof finding.description === "string" ? finding.description : undefined,
      file: typeof finding.file === "string" ? finding.file : undefined,
      line: typeof finding.line === "number" ? finding.line : undefined,
      recommendation: finding.recommendation || finding.fix,
    }));
}

function parsePerformanceMetrics(value: unknown): QASpecArtifact["performance_metrics"] {
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

  return value.map((detail) => (typeof detail === "string" ? detail : String(detail)));
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
// UTILITY FUNCTIONS
// ============================================================================

function normalizePriority(priority: any): "high" | "medium" | "low" | "critical" {
  if (typeof priority !== "string") return "medium";
  
  const p = priority.toLowerCase();
  if (p === "critical" || p === "p0") return "critical";
  if (p === "high" || p === "p1") return "high";
  if (p === "low" || p === "p3") return "low";
  return "medium";
}

function normalizeStatus(status: any): "pending" | "in_progress" | "complete" | "blocked" {
  if (typeof status !== "string") return "pending";
  
  const s = status.toLowerCase().replace(/[_-]/g, "");
  if (s === "complete" || s === "done" || s === "completed") return "complete";
  if (s === "inprogress" || s === "active" || s === "working") return "in_progress";
  if (s === "blocked" || s === "stuck") return "blocked";
  return "pending";
}

function normalizeTestStatus(status: any): "passed" | "failed" | "skipped" | "pending" {
  if (typeof status !== "string") return "pending";
  
  const s = status.toLowerCase();
  if (s === "passed" || s === "pass" || s === "success") return "passed";
  if (s === "failed" || s === "fail" || s === "error") return "failed";
  if (s === "skipped" || s === "skip") return "skipped";
  return "pending";
}

let idCounter = 0;
function generateId(): string {
  return `artifact_${Date.now()}_${++idCounter}`;
}

// -----------------
// Normalizers
// -----------------
function normalizeEstimate(v: unknown): string | undefined {
  if (v == null) return undefined;
  if (typeof v === "number") return String(v);
  if (typeof v === "string") return v;
  return undefined;
}

function normalizeToStringOrUndefined(v: unknown): string | undefined {
  if (v == null) return undefined;
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function normalizeComponentType(v: unknown): "service" | "database" | "cache" | "queue" | "api" | "client" {
  if (typeof v !== "string") return "service";
  const s = v.toLowerCase();
  if (s.includes("db") || s.includes("database")) return "database";
  if (s.includes("cache")) return "cache";
  if (s.includes("queue")) return "queue";
  if (s.includes("api")) return "api";
  if (s.includes("client")) return "client";
  return "service";
}

function normalizeHttpMethod(v: unknown): "GET" | "POST" | "PUT" | "PATCH" | "DELETE" {
  if (typeof v !== "string") return "GET";
  const m = v.toUpperCase();
  if (m === "POST") return "POST";
  if (m === "PUT") return "PUT";
  if (m === "PATCH") return "PATCH";
  if (m === "DELETE") return "DELETE";
  return "GET";
}

function normalizeFileNodeType(v: unknown): "file" | "folder" | "directory" {
  if (typeof v !== "string") return "file";
  const s = v.toLowerCase();
  if (s === "folder" || s === "directory" || s === "dir") return "folder";
  if (s === "file") return "file";
  return "file";
}

function normalizeTestType(v: unknown): "unit" | "integration" | "e2e" | "performance" | "security" {
  if (typeof v !== "string") return "unit";
  const s = v.toLowerCase();
  if (s === "integration") return "integration";
  if (s === "e2e") return "e2e";
  if (s === "performance") return "performance";
  if (s === "security") return "security";
  return "unit";
}

function normalizeSeverity(v: unknown): "critical" | "high" | "medium" | "low" | "info" {
  if (typeof v !== "string") return "info";
  const s = v.toLowerCase();
  if (s === "critical") return "critical";
  if (s === "high") return "high";
  if (s === "medium") return "medium";
  if (s === "low") return "low";
  return "info";
}

function normalizeConfidence(v: unknown): "high" | "medium" | "low" {
  if (typeof v !== "string") return "medium";
  const s = v.toLowerCase();
  if (s === "high") return "high";
  if (s === "low") return "low";
  return "medium";
}

// ============================================================================
// VALIDATION
// ============================================================================

export function validateArtifact(artifact: ParsedArtifact): boolean {
  if (!artifact?.role || artifact.error) {
    return false;
  }

  const validator = ARTIFACT_VALIDATORS[artifact.role];
  return validator ? validator(artifact.data) : false;
}

type ArtifactValidator = (data: unknown) => boolean;

const hasArrayEntries = (value: unknown): boolean =>
  Array.isArray(value) && value.length > 0;

const anyTrue = (...checks: Array<boolean | undefined>): boolean =>
  checks.some(Boolean);

const ARTIFACT_VALIDATORS: Partial<Record<ParsedArtifact["role"], ArtifactValidator>> = {
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

