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

// ============================================================================
// MAIN PARSER
// ============================================================================

export function parseArtifact(
  rawData: unknown,
  role: AgentRole
): ParsedArtifact {
  try {
    // Handle __raw__ field unwrapping
    let data = rawData;
    if (data && typeof data === "object" && "__raw__" in data) {
      try {
        data = JSON.parse((data as any).__raw__);
      } catch (parseError) {
        console.warn("Failed to parse __raw__ field, using original data");
      }
    }

    // Role-specific parsing
    switch (role) {
      case "product_manager":
        return {
          role,
          data: parsePMSpec(data),
          timestamp: new Date().toISOString(),
        };
      case "architect":
        return {
          role,
          data: parseArchitectSpec(data),
          timestamp: new Date().toISOString(),
        };
      case "engineer":
        return {
          role,
          data: parseEngineerSpec(data),
          timestamp: new Date().toISOString(),
        };
      case "qa":
        return {
          role,
          data: parseQASpec(data),
          timestamp: new Date().toISOString(),
        };
      default:
        throw new Error(`Unknown role: ${role}`);
    }
  } catch (error) {
    console.error("Artifact parse error:", error);
    return {
      role,
      data: {} as ArtifactData,
      error: error instanceof Error ? error.message : "Failed to parse artifact",
      timestamp: new Date().toISOString(),
    };
  }
}

// ============================================================================
// PRODUCT MANAGER PARSER
// ============================================================================

function parsePMSpec(data: unknown): PMSpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const artifact: PMSpecArtifact = {};
  const obj = data as Record<string, any>;

  // Parse user stories
  if (Array.isArray(obj.user_stories)) {
    artifact.user_stories = obj.user_stories
      .filter((story: any) => story && typeof story === "object")
      .map((story: any): UserStory => ({
        id: story.id || story.story_id || generateId(),
        title: story.title || story.name || "Untitled Story",
        story: story.story,
        description: story.description || story.desc,
        as_a: story.as_a || story.user_type,
        i_want: story.i_want || story.want,
        so_that: story.so_that || story.benefit,
        priority: normalizePriority(story.priority),
        estimate: story.estimate || story.story_points,
        status: normalizeStatus(story.status),
        tags: Array.isArray(story.tags) ? story.tags : [],
      }));
  }

  // Parse acceptance criteria
  if (Array.isArray(obj.acceptance_criteria)) {
    artifact.acceptance_criteria = obj.acceptance_criteria
      .filter((criteria: any) => criteria && typeof criteria === "object")
      .map((criteria: any): AcceptanceCriteria => ({
        id: criteria.id || generateId(),
        criteria: criteria.criteria || criteria.description,
        description: criteria.description || criteria.detail,
        scenario: criteria.scenario,
        given: criteria.given,
        when: criteria.when,
        then: criteria.then,
        completed: Boolean(criteria.completed),
      }));
  }

  // Parse epics
  if (Array.isArray(obj.epics)) {
    artifact.epics = obj.epics.map((epic: any) => ({
      id: epic.id || generateId(),
      title: epic.title || epic.name || "Untitled Epic",
      description: epic.description,
      stories: Array.isArray(epic.stories) ? epic.stories : [],
    }));
  }

  // Parse success metrics
  if (Array.isArray(obj.success_metrics)) {
    artifact.success_metrics = obj.success_metrics.map((metric: any) => ({
      metric: metric.metric || metric.name || "Untitled Metric",
      target: metric.target,
      description: metric.description,
    }));
  }

  artifact.priority = normalizePriority(obj.priority);

  return artifact;
}

// ============================================================================
// ARCHITECT PARSER
// ============================================================================

function parseArchitectSpec(data: unknown): ArchitectSpecArtifact {
  if (!data || typeof data !== "object") {
    return {};
  }

  const artifact: ArchitectSpecArtifact = {};
  const obj = data as Record<string, any>;

  // Parse system architecture
  if (obj.system_architecture && typeof obj.system_architecture === "object") {
    const arch = obj.system_architecture;
    artifact.system_architecture = {
      components: Array.isArray(arch.components)
        ? arch.components.map((comp: any) => ({
            id: comp.id || generateId(),
            name: comp.name || "Unnamed Component",
            type: comp.type || "service",
            description: comp.description,
            dependencies: Array.isArray(comp.dependencies)
              ? comp.dependencies
              : [],
            technologies: Array.isArray(comp.technologies)
              ? comp.technologies
              : [],
          }))
        : [],
      connections: Array.isArray(arch.connections)
        ? arch.connections.map((conn: any) => ({
            from: conn.from || conn.source,
            to: conn.to || conn.target,
            protocol: conn.protocol,
            description: conn.description,
          }))
        : [],
      diagram: arch.diagram,
    };
  }

  // Parse API endpoints
  if (Array.isArray(obj.api_endpoints)) {
    artifact.api_endpoints = obj.api_endpoints.map((endpoint: any) => ({
      method: endpoint.method || "GET",
      path: endpoint.path || endpoint.url || "/",
      description: endpoint.description,
      request_body: endpoint.request_body || endpoint.body,
      response: endpoint.response,
      auth_required: Boolean(endpoint.auth_required),
      rate_limit: endpoint.rate_limit,
    }));
  }

  // Parse database schema
  if (Array.isArray(obj.database_schema)) {
    artifact.database_schema = obj.database_schema.map((schema: any) => ({
      table_name: schema.table_name || schema.name || "unnamed_table",
      columns: Array.isArray(schema.columns) ? schema.columns : [],
      indexes: Array.isArray(schema.indexes) ? schema.indexes : [],
      relationships: Array.isArray(schema.relationships)
        ? schema.relationships
        : [],
    }));
  }

  // Parse technical decisions
  if (Array.isArray(obj.technical_decisions)) {
    artifact.technical_decisions = obj.technical_decisions.map(
      (decision: any) => ({
        decision: decision.decision || decision.title || "Untitled Decision",
        rationale: decision.rationale || decision.reason,
        alternatives: Array.isArray(decision.alternatives)
          ? decision.alternatives
          : [],
        trade_offs: decision.trade_offs || decision.tradeoffs,
        context: decision.context,
        confidence: decision.confidence || "medium",
      })
    );
  }

  // Parse technology stack
  if (obj.technology_stack && typeof obj.technology_stack === "object") {
    artifact.technology_stack = obj.technology_stack;
  }

  artifact.scalability_plan = obj.scalability_plan;
  artifact.security_considerations = Array.isArray(obj.security_considerations)
    ? obj.security_considerations
    : [];

  return artifact;
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
    artifact.implementation_plan = obj.implementation_plan.map(
      (step: any, index: number) => ({
        step_number: step.step_number || index + 1,
        title: step.title || step.name || `Step ${index + 1}`,
        description: step.description,
        files_to_create: Array.isArray(step.files_to_create)
          ? step.files_to_create
          : [],
        files_to_modify: Array.isArray(step.files_to_modify)
          ? step.files_to_modify
          : [],
        commands: Array.isArray(step.commands) ? step.commands : [],
        estimated_time: step.estimated_time || step.time,
        dependencies: Array.isArray(step.dependencies) ? step.dependencies : [],
        completed: Boolean(step.completed),
      })
    );
  }

  // Parse dependencies
  if (Array.isArray(obj.dependencies)) {
    artifact.dependencies = obj.dependencies.map((dep: any) => ({
      name: dep.name || dep.package || "unknown",
      version: dep.version,
      purpose: dep.purpose || dep.description,
      dev: Boolean(dep.dev || dep.devDependency),
    }));
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
    artifact.code_snippets = obj.code_snippets.map((snippet: any) => ({
      file: snippet.file || snippet.filename || "untitled",
      language: snippet.language || snippet.lang || "text",
      code: snippet.code || snippet.content || "",
      description: snippet.description,
    }));
  }

  artifact.estimated_effort = obj.estimated_effort;

  return artifact;
}

function parseFileNode(node: any): FileNode {
  if (!node || typeof node !== "object") {
    return {
      name: "unknown",
      path: "/",
      type: "file",
    };
  }

  return {
    name: node.name || "unknown",
    path: node.path || "/",
    type: node.type || (node.children ? "folder" : "file"),
    description: node.description,
    purpose: node.purpose,
    children: Array.isArray(node.children)
      ? node.children.map((child: any) => parseFileNode(child))
      : undefined,
    language: node.language,
    lines_of_code: node.lines_of_code || node.loc,
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

  // Parse test scenarios
  if (Array.isArray(obj.test_scenarios)) {
    artifact.test_scenarios = obj.test_scenarios.map((scenario: any) => ({
      id: scenario.id || generateId(),
      title: scenario.title || scenario.name || "Untitled Test",
      description: scenario.description,
      scenario: scenario.scenario,
      priority: normalizePriority(scenario.priority),
      type: scenario.type || "unit",
      tags: Array.isArray(scenario.tags) ? scenario.tags : [],
      steps: Array.isArray(scenario.steps) ? scenario.steps : [],
      expected_result: scenario.expected_result || scenario.expected,
      status: normalizeTestStatus(scenario.status),
    }));
  }

  // Parse test results
  if (obj.test_results && typeof obj.test_results === "object") {
    artifact.test_results = {
      passed: obj.test_results.passed || 0,
      failed: obj.test_results.failed || 0,
      skipped: obj.test_results.skipped || 0,
      total: obj.test_results.total || 0,
    };
  }

  // Parse code coverage
  if (obj.code_coverage && typeof obj.code_coverage === "object") {
    artifact.code_coverage = {
      lines: obj.code_coverage.lines,
      statements: obj.code_coverage.statements,
      functions: obj.code_coverage.functions,
      branches: obj.code_coverage.branches,
    };
  }

  // Parse security findings
  if (Array.isArray(obj.security_findings)) {
    artifact.security_findings = obj.security_findings.map((finding: any) => ({
      severity: finding.severity || "info",
      title: finding.title || finding.name || "Security Issue",
      description: finding.description,
      file: finding.file,
      line: finding.line,
      recommendation: finding.recommendation || finding.fix,
    }));
  }

  // Parse performance metrics
  if (obj.performance_metrics && typeof obj.performance_metrics === "object") {
    artifact.performance_metrics = {
      api_response_time: obj.performance_metrics.api_response_time,
      page_load_time: obj.performance_metrics.page_load_time,
      db_query_time: obj.performance_metrics.db_query_time,
      memory_usage: obj.performance_metrics.memory_usage,
      cpu_usage: obj.performance_metrics.cpu_usage,
    };
  }

  // Parse lint status
  artifact.lint_status = obj.lint_status || "clean";
  if (Array.isArray(obj.lint_details)) {
    artifact.lint_details = obj.lint_details;
  }

  artifact.quality_score = obj.quality_score;

  return artifact;
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

// ============================================================================
// VALIDATION
// ============================================================================

export function validateArtifact(artifact: ParsedArtifact): boolean {
  if (!artifact || !artifact.role) {
    return false;
  }

  if (artifact.error) {
    return false;
  }

  // Role-specific validation
  switch (artifact.role) {
    case "product_manager":
      const pmData = artifact.data as PMSpecArtifact;
      return Boolean(
        pmData.user_stories?.length || pmData.acceptance_criteria?.length
      );
    
    case "architect":
      const archData = artifact.data as ArchitectSpecArtifact;
      return Boolean(
        archData.system_architecture ||
        archData.api_endpoints?.length ||
        archData.technical_decisions?.length
      );
    
    case "engineer":
      const engData = artifact.data as EngineerSpecArtifact;
      return Boolean(
        engData.file_structure?.length || engData.implementation_plan?.length
      );
    
    case "qa":
      const qaData = artifact.data as QASpecArtifact;
      return Boolean(
        qaData.test_scenarios?.length || qaData.test_results
      );
    
    default:
      return false;
  }
}

