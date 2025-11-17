import type {
  APIEndpoint,
  SystemComponent,
  FileNode,
  TestScenario,
  SecurityFinding,
} from "#/types/metasop-artifacts";

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

const HTTP_METHODS = new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]);

export function isAPIEndpoint(v: unknown): v is APIEndpoint {
  if (!isRecord(v)) return false;

  const record = v as Record<string, unknown>;
  const method =
    typeof record.method === "string" ? record.method.toUpperCase() : "GET";

  let path: string | undefined;
  if (typeof record.path === "string") {
    path = record.path;
  } else if (typeof record.url === "string") {
    path = record.url;
  }

  if (!path) {
    return false;
  }

  return HTTP_METHODS.has(method);
}

export function isSystemComponent(v: unknown): v is SystemComponent {
  if (!isRecord(v)) return false;
  if (typeof v.id !== "string") return false;
  if (typeof v.name !== "string") return false;
  return true;
}

export function isDatabaseColumn(
  v: unknown,
): v is { name: string; type: string } {
  if (!isRecord(v)) return false;
  return typeof v.name === "string" && typeof v.type === "string";
}

export function isFileNode(v: unknown): v is FileNode {
  if (!isRecord(v)) return false;
  return typeof v.name === "string" && typeof v.path === "string";
}

export function isTestScenario(v: unknown): v is TestScenario {
  if (!isRecord(v)) return false;
  return typeof v.title === "string";
}

export function isSecurityFinding(v: unknown): v is SecurityFinding {
  if (!isRecord(v)) return false;
  return typeof v.title === "string" && typeof v.severity === "string";
}

export default {
  isAPIEndpoint,
  isSystemComponent,
  isDatabaseColumn,
  isFileNode,
  isTestScenario,
  isSecurityFinding,
};
