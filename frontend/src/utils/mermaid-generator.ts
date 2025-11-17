/**
 * Utility to convert MetaSOP JSON outputs to Mermaid diagram syntax
 */

type UnknownRecord = Record<string, unknown>;

const toRecord = (value: unknown): UnknownRecord | undefined =>
  typeof value === "object" && value !== null
    ? (value as UnknownRecord)
    : undefined;

const toArchitectJson = (value: unknown): ArchitectJson =>
  toRecord(value) as ArchitectJson;

const toDesignerJson = (value: unknown): DesignerJson =>
  toRecord(value) as DesignerJson;

const toNonEmptyString = (value: unknown): string | undefined => {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
};

const toStringArray = (value: unknown): string[] =>
  Array.isArray(value)
    ? (value as unknown[])
        .map((entry) => toNonEmptyString(entry))
        .filter((entry): entry is string => Boolean(entry))
    : [];

type ArchitectDecision = {
  decision: string;
  reason: string;
  tradeoffs: string;
};

type ArchitectApi = {
  path: string;
  method: string;
  request_schema?: UnknownRecord | null;
};

type ArchitectJson =
  | {
      design_doc?: string;
      apis?: ArchitectApi[];
      decisions?: ArchitectDecision[];
    }
  | null
  | undefined;

// Architect JSON to Mermaid Architecture Diagram
export function generateArchitectureDiagram(
  architectJson: ArchitectJson,
): string {
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
export function generateApiSequenceDiagram(
  architectJson: ArchitectJson,
): string {
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

type DesignerAccessibilityItem = {
  issue: string;
  severity: string;
  recommendation: string;
};

type DesignerJson =
  | {
      layout_plan?: string;
      accessibility?: DesignerAccessibilityItem[];
    }
  | null
  | undefined;

// UI Designer JSON to Component Tree
export function generateUiComponentDiagram(designerJson: DesignerJson): string {
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
export function generateUserStoryFlow(artifactContent: unknown): string {
  const pmJson = toRecord(artifactContent);
  const userStories = toStringArray(pmJson?.user_stories);

  if (userStories.length === 0) {
    return "";
  }

  const sanitizedStories = userStories.map((story, index) => ({
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
type SchemaColumn = {
  name: string;
  type: string;
  primary_key: boolean;
  foreign_key?: { table: string; column: string };
};

type SchemaTable = {
  name: string;
  columns: SchemaColumn[];
};

const toSchemaTables = (value: unknown): SchemaTable[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  const tables: SchemaTable[] = [];

  (value as unknown[]).forEach((table, tableIndex) => {
    const tableRecord = toRecord(table);
    if (!tableRecord) {
      return;
    }

    const name =
      toNonEmptyString(tableRecord.name) ?? `table_${tableIndex + 1}`;
    const columnsValue = Array.isArray(tableRecord.columns)
      ? (tableRecord.columns as unknown[])
      : [];

    const columns: SchemaColumn[] = [];
    columnsValue.forEach((column) => {
      const columnRecord = toRecord(column);
      if (!columnRecord) {
        return;
      }

      const columnName = toNonEmptyString(columnRecord.name);
      if (!columnName) {
        return;
      }

      const columnType = toNonEmptyString(columnRecord.type) ?? "string";
      const foreignKeyRecord = toRecord(columnRecord.foreign_key);
      const fkTable = toNonEmptyString(foreignKeyRecord?.table);
      const fkColumn = toNonEmptyString(foreignKeyRecord?.column);

      columns.push({
        name: columnName,
        type: columnType,
        primary_key: Boolean(columnRecord.primary_key),
        foreign_key:
          fkTable && fkColumn
            ? { table: fkTable, column: fkColumn }
            : undefined,
      });
    });

    tables.push({
      name,
      columns,
    });
  });

  return tables;
};

export function generateERDiagram(artifactContent: unknown): string {
  const schemaJson = toRecord(artifactContent);
  const tables = toSchemaTables(schemaJson?.tables);

  if (tables.length === 0) {
    return "";
  }

  let mermaid = "erDiagram\n";

  // Add tables and their columns
  tables.forEach((table) => {
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
  tables.forEach((table) => {
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

type TimelineTaskStatus = "pending" | "active" | "done" | "crit";

type TimelineTask = {
  id: string;
  name: string;
  start_date?: string;
  end_date?: string;
  duration?: number;
  status?: TimelineTaskStatus;
  depends_on?: string[];
};

const TIMELINE_STATUS_VALUES: TimelineTaskStatus[] = [
  "pending",
  "active",
  "done",
  "crit",
];

const toTimelineStatus = (value: unknown): TimelineTaskStatus | undefined => {
  if (typeof value !== "string") {
    return undefined;
  }
  return TIMELINE_STATUS_VALUES.find((status) => status === value);
};

const toDurationNumber = (value: unknown): number | undefined => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
};

const toTimelineTasks = (value: unknown): TimelineTask[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  const tasks: TimelineTask[] = [];

  (value as unknown[]).forEach((task, index) => {
    const taskRecord = toRecord(task);
    if (!taskRecord) {
      return;
    }

    const name = toNonEmptyString(taskRecord.name);
    if (!name) {
      return;
    }

    const id = toNonEmptyString(taskRecord.id) ?? `task_${index + 1}`;

    tasks.push({
      id,
      name,
      start_date: toNonEmptyString(taskRecord.start_date),
      end_date: toNonEmptyString(taskRecord.end_date),
      duration: toDurationNumber(taskRecord.duration),
      status: toTimelineStatus(taskRecord.status),
      depends_on: toStringArray(taskRecord.depends_on),
    });
  });

  return tasks;
};

type TimelineSection = {
  label: string;
  tasks: TimelineTask[];
};

const STATUS_TO_SECTION_LABEL: Array<{
  status: TimelineTaskStatus;
  label: string;
}> = [
  { status: "pending", label: "Planning" },
  { status: "active", label: "In Progress" },
  { status: "done", label: "Completed" },
  { status: "crit", label: "Critical" },
];

const buildGanttSections = (tasks: TimelineTask[]): TimelineSection[] =>
  STATUS_TO_SECTION_LABEL.map(({ status, label }) => ({
    label,
    tasks: tasks.filter((task) => task.status === status),
  })).filter((section) => section.tasks.length > 0);

const formatGanttTask = (task: TimelineTask): string => {
  const name = task.name.substring(0, 40).replace(/"/g, "'");

  let statusSegment = "";
  if (task.status && ["done", "active", "crit"].includes(task.status)) {
    statusSegment = `${task.status}, `;
  }

  let dependencySegment = "";
  if (Array.isArray(task.depends_on) && task.depends_on.length > 0) {
    dependencySegment = `, after ${task.depends_on[0]}`;
  }

  if (task.start_date && task.end_date) {
    return `  ${name} :${statusSegment}${task.id}, ${task.start_date}, ${task.end_date}`;
  }

  const duration =
    typeof task.duration === "number" ? `${task.duration}d` : "1d";
  return `  ${name} :${statusSegment}${task.id}${dependencySegment}, ${duration}`;
};

// Generate Gantt Chart from project timeline
export function generateGanttChart(artifactContent: unknown): string {
  const timelineJson = toRecord(artifactContent);
  const tasks = toTimelineTasks(timelineJson?.tasks);

  if (tasks.length === 0) {
    return "";
  }

  const lines = [
    "gantt",
    "  title Project Timeline",
    "  dateFormat YYYY-MM-DD",
    "",
  ];

  buildGanttSections(tasks).forEach(({ label, tasks: sectionTasks }) => {
    lines.push(`  section ${label}`);
    sectionTasks.forEach((task) => {
      lines.push(formatGanttTask(task));
    });
  });

  return `${lines.join("\n")}\n`;
}

const getVisibilitySymbol = (
  visibility?: "public" | "private" | "protected",
): string => {
  if (visibility === "private") {
    return "-";
  }
  if (visibility === "protected") {
    return "#";
  }
  return "+";
};

const toVisibility = (
  value: unknown,
): "public" | "private" | "protected" | undefined => {
  if (value === "public" || value === "private" || value === "protected") {
    return value;
  }
  return undefined;
};

type ClassProperty = {
  name: string;
  type: string;
  visibility?: "public" | "private" | "protected";
};

type ClassMethod = {
  name: string;
  return_type?: string;
  visibility?: "public" | "private" | "protected";
};

type ClassDefinition = {
  name: string;
  properties: ClassProperty[];
  methods: ClassMethod[];
  extends?: string;
  implements?: string[];
};

const toClassDefinitions = (value: unknown): ClassDefinition[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  const classes: ClassDefinition[] = [];

  (value as unknown[]).forEach((cls, index) => {
    const clsRecord = toRecord(cls);
    if (!clsRecord) {
      return;
    }

    const name = toNonEmptyString(clsRecord.name) ?? `Class${index + 1}`;

    const properties: ClassProperty[] = [];
    if (Array.isArray(clsRecord.properties)) {
      (clsRecord.properties as unknown[]).forEach((prop) => {
        const propRecord = toRecord(prop);
        if (!propRecord) {
          return;
        }

        const propName = toNonEmptyString(propRecord.name);
        if (!propName) {
          return;
        }

        properties.push({
          name: propName,
          type: toNonEmptyString(propRecord.type) ?? "any",
          visibility: toVisibility(propRecord.visibility),
        });
      });
    }

    const methods: ClassMethod[] = [];
    if (Array.isArray(clsRecord.methods)) {
      (clsRecord.methods as unknown[]).forEach((method) => {
        const methodRecord = toRecord(method);
        if (!methodRecord) {
          return;
        }

        const methodName = toNonEmptyString(methodRecord.name);
        if (!methodName) {
          return;
        }

        methods.push({
          name: methodName,
          return_type: toNonEmptyString(methodRecord.return_type),
          visibility: toVisibility(methodRecord.visibility),
        });
      });
    }

    const extendsValue = toNonEmptyString(clsRecord.extends);
    const implementsValue = toStringArray(clsRecord.implements);

    classes.push({
      name,
      properties,
      methods,
      extends: extendsValue,
      implements: implementsValue.length > 0 ? implementsValue : undefined,
    });
  });

  return classes;
};

// Generate Class Diagram from code structure
export function generateClassDiagram(artifactContent: unknown): string {
  const codeStructure = toRecord(artifactContent);
  const classes = toClassDefinitions(codeStructure?.classes);

  if (classes.length === 0) {
    return "";
  }

  let mermaid = "classDiagram\n";

  classes.forEach((cls) => {
    // Class definition
    mermaid += `  class ${cls.name} {\n`;

    // Properties
    if (cls.properties) {
      cls.properties.forEach((prop) => {
        const visibility = getVisibilitySymbol(prop.visibility);
        mermaid += `    ${visibility}${prop.type} ${prop.name}\n`;
      });
    }

    // Methods
    if (cls.methods) {
      cls.methods.forEach((method) => {
        const visibility = getVisibilitySymbol(method.visibility);
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
  matches: (context: DiagramContext) => boolean;
  generate: (artifactContent: unknown) => string;
};

type DiagramContext = {
  role: string;
  artifactContent: unknown;
};

const ROLE_STRATEGIES: DiagramStrategy[] = [
  {
    type: "architecture",
    matches: ({ role }) => role.includes("architect"),
    generate: (artifactContent) =>
      generateArchitectureDiagram(toArchitectJson(artifactContent)),
  },
  {
    type: "ui-components",
    matches: ({ role }) => role.includes("designer") || role.includes("ui"),
    generate: (artifactContent) =>
      generateUiComponentDiagram(toDesignerJson(artifactContent)),
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
    matches: ({ artifactContent }) => {
      const record = toRecord(artifactContent);
      return Array.isArray(record?.tasks);
    },
    generate: generateGanttChart,
  },
  {
    type: "class-diagram",
    matches: ({ artifactContent }) => {
      const record = toRecord(artifactContent);
      return Array.isArray(record?.classes);
    },
    generate: generateClassDiagram,
  },
];

const runStrategies = (
  strategies: DiagramStrategy[],
  context: DiagramContext,
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
  artifactContent: unknown,
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
