declare module "#/types/metasop-artifacts" {
  // Top-level parsed artifact used by visualizations.
  export interface ParsedArtifact {
    role: string;
    data?: ArtifactData;
    error?: string | null;
    // allow parser to attach additional metadata like timestamp/score
    timestamp?: string;
    [k: string]: unknown;
  }

  export type ArtifactData = PMSpecArtifact | ArchitectSpecArtifact | EngineerSpecArtifact | QASpecArtifact | Record<string, unknown>;

  export type AgentRole = "product_manager" | "architect" | "engineer" | "qa" | string;

  // Orchestration step used by flow visualizations
  export interface OrchestrationStep {
    id: string;
    role: AgentRole;
    title?: string;
    description?: string;
    status?: "pending" | "in_progress" | "complete" | "blocked" | string;
    progress?: number;
    started_at?: string;
    completed_at?: string;
    error?: string;
    artifact?: unknown;
    [k: string]: unknown;
  }

  export interface VisualizationProps {
    artifact: ParsedArtifact;
    animated?: boolean;
    className?: string;
    onInteraction?: (action: string, data?: unknown) => void;
  }

  // ------------------------- Product Manager -------------------------
  export interface Epic {
    id?: string | number;
    title?: string;
    description?: string;
    stories?: Array<UserStory | string>;
  }

  export interface SuccessMetric {
    metric: string;
    target?: string | number;
    description?: string;
  }

  export interface PMSpecArtifact {
    epics?: Epic[];
    user_stories?: UserStory[];
    acceptance_criteria?: AcceptanceCriteria[];
    success_metrics?: SuccessMetric[];
    // optional document-level priority (parser sometimes attaches this)
    priority?: "high" | "medium" | "low" | "critical" | string;
  }

  export interface UserStory {
    id?: string | number;
    title?: string;
    description?: string;
    story?: string;
    as_a?: string;
    i_want?: string;
    so_that?: string;
    priority?: "critical" | "high" | "medium" | "low" | string;
    estimate?: string | number;
    status?: string;
    tags?: string[];
  }

  export interface AcceptanceCriteria {
    id?: string | number;
    criteria?: string;
    description?: string;
    completed?: boolean;
    given?: string;
    when?: string;
    then?: string;
    scenario?: string;
  }

  // ------------------------- Architect -------------------------
  export interface APIEndpoint {
    method?: string;
    path?: string;
    description?: string;
    auth_required?: boolean;
  }

  export interface ColumnSchema { name?: string; type?: string; }

  export interface DatabaseSchema {
    table_name?: string;
    columns?: ColumnSchema[];
  }

  export interface ConnectionDescriptor {
    from?: string;
    to?: string;
    type?: string;
  }

  export interface SystemComponent {
    id?: string | number;
    name?: string;
    type?: string;
    description?: string;
    technologies?: string[];
  }

  export interface SystemArchitecture {
    components?: SystemComponent[];
    connections?: ConnectionDescriptor[];
    diagram?: string | object;
  }

  export interface ArchitectSpecArtifact {
    system_architecture?: SystemArchitecture;
    api_endpoints?: APIEndpoint[];
    database_schema?: DatabaseSchema[];
    technical_decisions?: Array<{ decision?: string; rationale?: string; alternatives?: string[]; confidence?: string }>;
    technology_stack?: Record<string, string>;
    // parser may attach these
    scalability_plan?: string;
    security_considerations?: unknown[];
  }

  // ------------------------- Engineer -------------------------
  export interface FileNode {
    name?: string;
    type?: string; // file | folder | directory
    children?: FileNode[];
    purpose?: string;
    path?: string;
    description?: string;
    language?: string;
    lines_of_code?: number;
  }

  export interface ImplementationStep {
    step_number?: number;
    title?: string;
    description?: string;
    files_to_create?: string[];
    files_to_modify?: string[];
    commands?: string[];
    estimated_time?: string;
    completed?: boolean;
  }

  export interface DependencyDescriptor {
    name?: string;
    version?: string;
    dev?: boolean;
    purpose?: string;
  }

  export interface EngineerSpecArtifact {
    file_structure?: FileNode[];
    implementation_plan?: ImplementationStep[];
    dependencies?: DependencyDescriptor[];
    code_snippets?: Array<{ language?: string; code?: string }>;
    setup_commands?: string[];
    run_commands?: string[];
    test_commands?: string[];
    estimated_effort?: string;
  }

  // ------------------------- QA -------------------------
  export interface TestResults {
    passed?: number;
    failed?: number;
    skipped?: number;
    total?: number;
  }

  export interface TestScenario {
    id?: string | number;
    title?: string;
    description?: string;
    status?: string; // passed|failed|skipped|pending
    priority?: string;
    type?: string;
    tags?: string[];
  }

  export interface SecurityFinding {
    title?: string;
    severity?: string;
    description?: string;
    file?: string;
    line?: number;
    recommendation?: string;
  }

  export interface QASpecArtifact {
    test_scenarios?: TestScenario[];
    test_results?: TestResults;
    code_coverage?: Record<string, number>;
    security_findings?: SecurityFinding[];
    performance_metrics?: Record<string, string | number | React.ReactNode>;
    lint_status?: string;
    lint_details?: unknown[];
    quality_score?: number;
  }

  // Re-export common utility types (for parsers/validators)
  export type AgentRoleKey = AgentRole;
  export type APIEndpointType = APIEndpoint;
  export type SystemComponentType = SystemComponent;
  export type DatabaseSchemaType = DatabaseSchema;
  export type SecurityFindingType = SecurityFinding;
}
