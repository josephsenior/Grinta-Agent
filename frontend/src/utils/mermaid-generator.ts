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

  let mermaid = "graph LR\n";
  mermaid += "  start((Start))\n";

  pmJson.user_stories.forEach((story, index) => {
    const nodeId = `story${index}`;
    const label = story.substring(0, 50).replace(/"/g, "'");
    mermaid += `  ${nodeId}["${label}"]\n`;

    if (index === 0) {
      mermaid += `  start --> ${nodeId}\n`;
    } else {
      mermaid += `  story${index - 1} --> ${nodeId}\n`;
    }
  });

  mermaid += `  story${pmJson.user_stories.length - 1} --> done((Done))\n`;

  return mermaid;
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

  let mermaid = "gantt\n";
  mermaid += "  title Project Timeline\n";
  mermaid += "  dateFormat YYYY-MM-DD\n\n";

  // Group by status
  const sections = {
    Planning: timelineJson.tasks.filter((t) => t.status === "pending"),
    "In Progress": timelineJson.tasks.filter((t) => t.status === "active"),
    Completed: timelineJson.tasks.filter((t) => t.status === "done"),
    Critical: timelineJson.tasks.filter((t) => t.status === "crit"),
  };

  Object.entries(sections).forEach(([sectionName, tasks]) => {
    if (tasks.length > 0) {
      mermaid += `  section ${sectionName}\n`;
      tasks.forEach((task) => {
        const name = task.name.substring(0, 40);
        const status =
          task.status === "done"
            ? "done"
            : task.status === "active"
              ? "active"
              : task.status === "crit"
                ? "crit"
                : "";
        const depends =
          task.depends_on && task.depends_on.length > 0
            ? `, after ${task.depends_on[0]}`
            : "";

        if (task.start_date && task.end_date) {
          mermaid += `  ${name} :${status ? `${status}, ` : ""}${task.id}, ${task.start_date}, ${task.end_date}\n`;
        } else if (task.duration) {
          mermaid += `  ${name} :${status ? `${status}, ` : ""}${task.id}${depends}, ${task.duration}d\n`;
        } else {
          mermaid += `  ${name} :${status ? `${status}, ` : ""}${task.id}${depends}, 1d\n`;
        }
      });
    }
  });

  return mermaid;
}

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
export function autoGenerateDiagram(
  stepId: string,
  role: string,
  artifactContent: any,
): { type: string; mermaid: string } | null {
  if (!artifactContent) return null;

  const roleNormalized = role.toLowerCase().trim();

  // Architect → Architecture + API diagrams
  if (roleNormalized.includes("architect")) {
    return {
      type: "architecture",
      mermaid: generateArchitectureDiagram(artifactContent),
    };
  }

  // UI Designer → Component tree
  if (roleNormalized.includes("designer") || roleNormalized.includes("ui")) {
    return {
      type: "ui-components",
      mermaid: generateUiComponentDiagram(artifactContent),
    };
  }

  // Product Manager → User story flow
  if (roleNormalized.includes("product") || roleNormalized.includes("pm")) {
    return {
      type: "user-stories",
      mermaid: generateUserStoryFlow(artifactContent),
    };
  }

  // Database Designer / DBA → ER Diagram
  if (roleNormalized.includes("database") || roleNormalized.includes("dba")) {
    return {
      type: "er-diagram",
      mermaid: generateERDiagram(artifactContent),
    };
  }

  // Project Manager / Timeline → Gantt Chart
  if (artifactContent.tasks && Array.isArray(artifactContent.tasks)) {
    return {
      type: "gantt-chart",
      mermaid: generateGanttChart(artifactContent),
    };
  }

  // Engineer / Code Structure → Class Diagram
  if (artifactContent.classes && Array.isArray(artifactContent.classes)) {
    return {
      type: "class-diagram",
      mermaid: generateClassDiagram(artifactContent),
    };
  }

  return null;
}
