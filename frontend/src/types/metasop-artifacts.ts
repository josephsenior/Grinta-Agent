/**
 * MetaSOP Artifact Type Definitions
 * 
 * Type-safe interfaces for all MetaSOP agent artifacts
 */

// ============================================================================
// BASE TYPES
// ============================================================================

export type AgentRole = "product_manager" | "architect" | "engineer" | "qa";
export type Priority = "high" | "medium" | "low" | "critical";
export type Status = "pending" | "in_progress" | "complete" | "blocked";
export type TestStatus = "passed" | "failed" | "skipped" | "pending";

// ============================================================================
// PRODUCT MANAGER ARTIFACTS
// ============================================================================

export interface UserStory {
  id?: string;
  title: string;
  story?: string;
  description?: string;
  as_a?: string;
  i_want?: string;
  so_that?: string;
  priority?: Priority;
  estimate?: string;
  status?: Status;
  tags?: string[];
}

export interface AcceptanceCriteria {
  id?: string;
  criteria?: string;
  description?: string;
  scenario?: string;
  given?: string;
  when?: string;
  then?: string;
  completed?: boolean;
}

export interface PMSpecArtifact {
  user_stories?: UserStory[];
  acceptance_criteria?: AcceptanceCriteria[];
  priority?: Priority;
  epics?: Array<{
    id?: string;
    title: string;
    description?: string;
    stories?: string[];
  }>;
  success_metrics?: Array<{
    metric: string;
    target?: string;
    description?: string;
  }>;
}

// ============================================================================
// ARCHITECT ARTIFACTS
// ============================================================================

export interface APIEndpoint {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  description?: string;
  request_body?: string;
  response?: string;
  auth_required?: boolean;
  rate_limit?: string;
}

export interface DatabaseSchema {
  table_name: string;
  columns?: Array<{
    name: string;
    type: string;
    constraints?: string[];
  }>;
  indexes?: string[];
  relationships?: string[];
}

export interface TechnicalDecision {
  decision: string;
  rationale?: string;
  alternatives?: string[];
  trade_offs?: string;
  context?: string;
  confidence?: "high" | "medium" | "low";
}

export interface SystemComponent {
  id: string;
  name: string;
  type: "service" | "database" | "cache" | "queue" | "api" | "client";
  description?: string;
  dependencies?: string[];
  technologies?: string[];
}

export interface ArchitectSpecArtifact {
  system_architecture?: {
    components?: SystemComponent[];
    connections?: Array<{
      from: string;
      to: string;
      protocol?: string;
      description?: string;
    }>;
    diagram?: string; // Mermaid diagram string
  };
  api_endpoints?: APIEndpoint[];
  database_schema?: DatabaseSchema[];
  technical_decisions?: TechnicalDecision[];
  technology_stack?: Record<string, string>;
  scalability_plan?: string;
  security_considerations?: string[];
}

// ============================================================================
// ENGINEER ARTIFACTS
// ============================================================================

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "folder" | "directory";
  description?: string;
  purpose?: string;
  children?: FileNode[];
  language?: string;
  lines_of_code?: number;
}

export interface ImplementationStep {
  step_number?: number;
  title: string;
  description?: string;
  files_to_create?: string[];
  files_to_modify?: string[];
  commands?: string[];
  estimated_time?: string;
  dependencies?: string[];
  completed?: boolean;
}

export interface Dependency {
  name: string;
  version?: string;
  purpose?: string;
  dev?: boolean;
}

export interface EngineerSpecArtifact {
  file_structure?: FileNode[];
  implementation_plan?: ImplementationStep[];
  dependencies?: Dependency[];
  setup_commands?: string[];
  run_commands?: string[];
  test_commands?: string[];
  code_snippets?: Array<{
    file: string;
    language: string;
    code: string;
    description?: string;
  }>;
  estimated_effort?: string;
}

// ============================================================================
// QA ARTIFACTS
// ============================================================================

export interface TestScenario {
  id?: string;
  title: string;
  description?: string;
  scenario?: string;
  priority?: Priority;
  type?: "unit" | "integration" | "e2e" | "performance" | "security";
  tags?: string[];
  steps?: string[];
  expected_result?: string;
  status?: TestStatus;
}

export interface CodeCoverageMetrics {
  lines?: number;
  statements?: number;
  functions?: number;
  branches?: number;
}

export interface SecurityFinding {
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  description?: string;
  file?: string;
  line?: number;
  recommendation?: string;
}

export interface PerformanceMetrics {
  api_response_time?: string;
  page_load_time?: string;
  db_query_time?: string;
  memory_usage?: string;
  cpu_usage?: string;
}

export interface QASpecArtifact {
  test_scenarios?: TestScenario[];
  test_results?: {
    passed?: number;
    failed?: number;
    skipped?: number;
    total?: number;
  };
  code_coverage?: CodeCoverageMetrics;
  security_findings?: SecurityFinding[];
  performance_metrics?: PerformanceMetrics;
  lint_status?: "clean" | "warnings" | "errors";
  lint_details?: Array<{
    file: string;
    issues: number;
    severity: string;
  }>;
  quality_score?: number;
}

// ============================================================================
// UNIFIED ARTIFACT TYPE
// ============================================================================

export type ArtifactData = 
  | PMSpecArtifact 
  | ArchitectSpecArtifact 
  | EngineerSpecArtifact 
  | QASpecArtifact;

export interface ParsedArtifact {
  role: AgentRole;
  data: ArtifactData;
  error?: string;
  timestamp?: string;
}

// ============================================================================
// ORCHESTRATION STEP
// ============================================================================

export interface OrchestrationStep {
  id: string;
  role: AgentRole;
  title: string;
  description?: string;
  status: Status;
  artifact?: ParsedArtifact;
  started_at?: string;
  completed_at?: string;
  error?: string;
  progress?: number; // 0-100
}

// ============================================================================
// METASOP EVENT
// ============================================================================

export interface MetaSOPEvent {
  type: "metasop_step_start" | "metasop_step_update" | "metasop_step_complete" | "metasop_orchestration_complete";
  event_type?: string;
  step_id: string;
  role: AgentRole;
  artifact?: any;
  status?: string;
  timestamp?: string;
  progress?: number;
  error?: string;
}

// ============================================================================
// VISUALIZATION PROPS
// ============================================================================

export interface VisualizationProps {
  artifact: ParsedArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: any) => void;
}

