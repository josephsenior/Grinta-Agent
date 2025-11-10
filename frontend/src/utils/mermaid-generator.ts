/**
 * Utility to convert MetaSOP JSON outputs to Mermaid diagram syntax
 */

// Architect JSON to Mermaid Architecture Diagram
export function generateArchitectureDiagram(architectJson: {
  design_doc?: string;
  apis?: Array<{
    path: string;
    method: string;
    request_schema?: any;
  }>;
  decisions?: Array<{
    decision: string;
    reason: string;
    tradeoffs: string;
  }>;
}): string {
  if (!architectJson) return "";

  let mermaid = "graph TB\n";

  // Add API endpoints as nodes
  if (architectJson.apis && architectJson.apis.length > 0) {
    mermaid += "  subgraph APIs\n";
    architectJson.apis.forEach((api, index) => {
      const nodeId = `api${index}`;
      const label = `${api.method} ${api.path}`;
      mermaid += `    ${nodeId}["${label}"]\n`;
    });
    mermaid += "  end\n\n";
  }

  // Add decisions as notes
  if (architectJson.decisions && architectJson.decisions.length > 0) {
    mermaid += "  subgraph Decisions\n";
    architectJson.decisions.forEach((decision, index) => {
      const nodeId = `dec${index}`;
      const label = decision.decision.replace(/"/g, "'");
      mermaid += `    ${nodeId}["${label}"]\n`;
    });
    mermaid += "  end\n";
  }

  return mermaid;
}

// API Sequence Diagram
export function generateApiSequenceDiagram(architectJson: {
  apis?: Array<{
    path: string;
    method: string;
    request_schema?: any;
  }>;
}): string {
  if (!architectJson?.apis || architectJson.apis.length === 0) {
    return "";
  }

  let mermaid = "sequenceDiagram\n";
  mermaid += "  participant Client\n";
  mermaid += "  participant API\n";
  mermaid += "  participant Backend\n\n";

  architectJson.apis.forEach((api) => {
    const { method } = api;
    const { path } = api;
    mermaid += `  Client->>API: ${method} ${path}\n`;
    mermaid += `  API->>Backend: Process Request\n`;
    mermaid += `  Backend-->>API: Response\n`;
    mermaid += `  API-->>Client: Result\n\n`;
  });

  return mermaid;
}

// UI Designer JSON to Component Tree
export function generateUiComponentDiagram(designerJson: {
  layout_plan?: string;
  accessibility?: Array<{
    issue: string;
    severity: string;
    recommendation: string;
  }>;
}): string {
  if (!designerJson?.layout_plan) return "";

  let mermaid = "graph TD\n";

  // Parse layout_plan to extract sections
  const layoutPlan = designerJson.layout_plan;
  const sections = layoutPlan.split(/Section:/i).filter((s) => s.trim());

  sections.forEach((section, index) => {
    const sectionName = section.split("\n")[0].trim();
    if (sectionName) {
      const nodeId = `section${index}`;
      const label = sectionName.substring(0, 50).replace(/"/g, "'");
      mermaid += `  ${nodeId}["${label}"]\n`;

      // Connect sections in sequence
      if (index > 0) {
        mermaid += `  section${index - 1} --> ${nodeId}\n`;
      }
    }
  });

  // Add accessibility warnings
  if (designerJson.accessibility && designerJson.accessibility.length > 0) {
    mermaid += "\n  subgraph Accessibility Issues\n";
    designerJson.accessibility.forEach((item, index) => {
      if (item.severity === "high") {
        const nodeId = `a11y${index}`;
        const label = item.issue.substring(0, 40).replace(/"/g, "'");
        mermaid += `    ${nodeId}["⚠️ ${label}"]\n`;
      }
    });
    mermaid += "  end\n";
  }

  return mermaid;
}

// PM Spec to User Story Flow
export function generateUserStoryFlow(pmJson: {
  user_stories?: string[];
  acceptance_criteria?: string[];
}): string {
  if (!pmJson?.user_stories || pmJson.user_stories.length === 0) {
    return "";
  }

  const sanitizedStories = pmJson.user_stories.map((story, index) => ({
    nodeId: `story${index}`,
    label: story.substring(0, 50).replace(/"/g, "'"),
  }));

  const lines: string[] = ["graph LR", "  start((Start))"];

  sanitizedStories.forEach(({ nodeId, label }) => {
    lines.push(`  ${nodeId}["${label}"]`);
  });

  sanitizedStories.forEach(({ nodeId }, index) => {
    const previousNodeId =
      index === 0 ? "start" : sanitizedStories[index - 1].nodeId;
    lines.push(`  ${previousNodeId} --> ${nodeId}`);
  });

  const lastNodeId = sanitizedStories[sanitizedStories.length - 1].nodeId;
  lines.push(`  ${lastNodeId} --> done((Done))`);

  return `${lines.join("\n")}\n`;
}

// Full Orchestration Flow Diagram
export function generateOrchestrationFlow(
  steps: Array<{
    step_id: string;
    role: string;
    status: string;
    artifact_hash?: string;
  }>,
): string {
  if (!steps || steps.length === 0) return "";

  let mermaid = "graph LR\n";

  steps.forEach((step, index) => {
    const nodeId = step.step_id.replace(/[^a-zA-Z0-9]/g, "_");
    const label = `${step.role}`;

    // Color based on status
    let style = "";
    if (step.status === "success") {
      style = ":::success";
    } else if (step.status === "failed") {
      style = ":::failed";
    } else if (step.status === "running") {
      style = ":::running";
    }

    mermaid += `  ${nodeId}["${label}"]${style}\n`;

    // Connect to previous step
    if (index > 0) {
      const prevNodeId = steps[index - 1].step_id.replace(/[^a-zA-Z0-9]/g, "_");
      mermaid += `  ${prevNodeId} --> ${nodeId}\n`;
    }
  });

  // Add styles
  mermaid +=
    "\n  classDef success fill:#90EE90,stroke:#006400,stroke-width:2px\n";
  mermaid += "  classDef failed fill:#FFB6C1,stroke:#8B0000,stroke-width:2px\n";
  mermaid +=
    "  classDef running fill:#87CEEB,stroke:#00008B,stroke-width:2px\n";

  return mermaid;
}

// Generate ER Diagram from database schema
export function generateERDiagram(schemaJson: {
  tables?: Array<{
    name: string;
    columns?: Array<{
      name: string;
      type: string;
      primary_key?: boolean;
      foreign_key?: { table: string; column: string };
    }>;
  }>;
}): string {
  if (!schemaJson?.tables || schemaJson.tables.length === 0) {
    return "";
  }

  let mermaid = "erDiagram\n";

  // Add tables and their columns
  schemaJson.tables.forEach((table) => {
    mermaid += `  ${table.name} {\n`;

    if (table.columns) {
      table.columns.forEach((col) => {
        const type = col.type || "string";
        const pk = col.primary_key ? " PK" : "";
        const fk = col.foreign_key ? " FK" : "";
        mermaid += `    ${type} ${col.name}${pk}${fk}\n`;
      });
    }

    mermaid += `  }\n`;
  });

  // Add relationships
  schemaJson.tables.forEach((table) => {
    if (table.columns) {
      table.columns.forEach((col) => {
        if (col.foreign_key) {
          mermaid += `  ${table.name} ||--o{ ${col.foreign_key.table} : has\n`;
        }
      });
    }
  });

  return mermaid;
}

// Generate Gantt Chart from project timeline
export function generateGanttChart(timelineJson: {
  tasks?: Array<{
    id: string;
    name: string;
    start_date?: string;
    end_date?: string;
    duration?: number;
    status?: "pending" | "active" | "done" | "crit";
    depends_on?: string[];
  }>;
}): string {
  if (!timelineJson?.tasks || timelineJson.tasks.length === 0) {
    return "";
  }

  const lines = [
    "gantt",
    "  title Project Timeline",
    "  dateFormat YYYY-MM-DD",
    "",
  ];

  buildGanttSections(timelineJson.tasks).forEach(({ label, tasks }) => {
    lines.push(`  section ${label}`);
    tasks.forEach((task) => {
      lines.push(formatGanttTask(task));
    });
  });

  return `${lines.join("\n")}\n`;
}

type TimelineTask = NonNullable<
  NonNullable<Parameters<typeof generateGanttChart>[0]["tasks"]>
>[number];

const GANTT_SECTION_DEFINITIONS: Array<{
  label: string;
  status: TimelineTask["status"];
}> = [
  { label: "Planning", status: "pending" },
  { label: "In Progress", status: "active" },
  { label: "Completed", status: "done" },
  { label: "Critical", status: "crit" },
];

const buildGanttSections = (tasks: TimelineTask[]) =>
  GANTT_SECTION_DEFINITIONS.map(({ label, status }) => ({
    label,
    tasks: tasks.filter((task) => task.status === status),
  })).filter((section) => section.tasks.length > 0);

const formatGanttTask = (task: TimelineTask): string => {
  const name = task.name.substring(0, 40).replace(/"/g, "'");
  const statusSegment =
    task.status && ["done", "active", "crit"].includes(task.status)
      ? `${task.status}, `
      : "";
  const depends =
    task.depends_on && task.depends_on.length > 0
      ? `, after ${task.depends_on[0]}`
      : "";

  if (task.start_date && task.end_date) {
    return `  ${name} :${statusSegment}${task.id}, ${task.start_date}, ${task.end_date}`;
  }

  const duration = task.duration ? `${task.duration}d` : "1d";
  return `  ${name} :${statusSegment}${task.id}${depends}, ${duration}`;
};

// Generate Class Diagram from code structure
export function generateClassDiagram(codeStructure: {
  classes?: Array<{
    name: string;
    properties?: Array<{
      name: string;
      type: string;
      visibility?: "public" | "private" | "protected";
    }>;
    methods?: Array<{
      name: string;
      return_type?: string;
      visibility?: "public" | "private" | "protected";
    }>;
    extends?: string;
    implements?: string[];
  }>;
}): string {
  if (!codeStructure?.classes || codeStructure.classes.length === 0) {
    return "";
  }

  let mermaid = "classDiagram\n";

  codeStructure.classes.forEach((cls) => {
    // Class definition
    mermaid += `  class ${cls.name} {\n`;

    // Properties
    if (cls.properties) {
      cls.properties.forEach((prop) => {
        const visibility =
          prop.visibility === "private"
            ? "-"
            : prop.visibility === "protected"
              ? "#"
              : "+";
        mermaid += `    ${visibility}${prop.type} ${prop.name}\n`;
      });
    }

    // Methods
    if (cls.methods) {
      cls.methods.forEach((method) => {
        const visibility =
          method.visibility === "private"
            ? "-"
            : method.visibility === "protected"
              ? "#"
              : "+";
        const returnType = method.return_type || "void";
        mermaid += `    ${visibility}${method.name}() ${returnType}\n`;
      });
    }

    mermaid += `  }\n`;

    // Relationships
    if (cls.extends) {
      mermaid += `  ${cls.extends} <|-- ${cls.name}\n`;
    }

    if (cls.implements) {
      cls.implements.forEach((iface) => {
        mermaid += `  ${iface} <|.. ${cls.name}\n`;
      });
    }
  });

  return mermaid;
}

// Auto-detect diagram type and generate appropriate diagram
type MermaidDiagram = { type: string; mermaid: string };

type DiagramStrategy = {
  type: string;
  matches: (context: { role: string; artifactContent: any }) => boolean;
  generate: (artifactContent: any) => string;
};

const ROLE_STRATEGIES: DiagramStrategy[] = [
  {
    type: "architecture",
    matches: ({ role }) => role.includes("architect"),
    generate: generateArchitectureDiagram,
  },
  {
    type: "ui-components",
    matches: ({ role }) => role.includes("designer") || role.includes("ui"),
    generate: generateUiComponentDiagram,
  },
  {
    type: "user-stories",
    matches: ({ role }) => role.includes("product") || role.includes("pm"),
    generate: generateUserStoryFlow,
  },
  {
    type: "er-diagram",
    matches: ({ role }) => role.includes("database") || role.includes("dba"),
    generate: generateERDiagram,
  },
];

const CONTENT_STRATEGIES: DiagramStrategy[] = [
  {
    type: "gantt-chart",
    matches: ({ artifactContent }) => Array.isArray(artifactContent?.tasks),
    generate: generateGanttChart,
  },
  {
    type: "class-diagram",
    matches: ({ artifactContent }) => Array.isArray(artifactContent?.classes),
    generate: generateClassDiagram,
  },
];

const runStrategies = (
  strategies: DiagramStrategy[],
  context: { role: string; artifactContent: any },
): MermaidDiagram | null => {
  for (const strategy of strategies) {
    if (strategy.matches(context)) {
      return {
        type: strategy.type,
        mermaid: strategy.generate(context.artifactContent),
      };
    }
  }

  return null;
};

export function autoGenerateDiagram(
  stepId: string,
  role: string,
  artifactContent: any,
): MermaidDiagram | null {
  if (!artifactContent) {
    return null;
  }

  const normalizedRole = role.toLowerCase().trim();
  const context = { role: normalizedRole, artifactContent };

  return (
    runStrategies(ROLE_STRATEGIES, context) ??
    runStrategies(CONTENT_STRATEGIES, context)
  );
}
