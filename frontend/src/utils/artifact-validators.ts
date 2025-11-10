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

export function isAPIEndpoint(v: unknown): v is APIEndpoint {
  if (!isRecord(v)) return false;
  const method =
    typeof (v as any).method === "string"
      ? (v as any).method.toUpperCase()
      : "GET";
  const path =
    typeof (v as any).path === "string" || typeof (v as any).url === "string";
  return path && ["GET", "POST", "PUT", "PATCH", "DELETE"].includes(method);
}

export function isSystemComponent(v: unknown): v is SystemComponent {
  if (!isRecord(v)) return false;
  if (typeof (v as any).id !== "string") return false;
  if (typeof (v as any).name !== "string") return false;
  return true;
}

export function isDatabaseColumn(
  v: unknown,
): v is { name: string; type: string } {
  if (!isRecord(v)) return false;
  return (
    typeof (v as any).name === "string" && typeof (v as any).type === "string"
  );
}

export function isFileNode(v: unknown): v is FileNode {
  if (!isRecord(v)) return false;
  return (
    typeof (v as any).name === "string" && typeof (v as any).path === "string"
  );
}

export function isTestScenario(v: unknown): v is TestScenario {
  if (!isRecord(v)) return false;
  return typeof (v as any).title === "string";
}

export function isSecurityFinding(v: unknown): v is SecurityFinding {
  if (!isRecord(v)) return false;
  return (
    typeof (v as any).title === "string" &&
    typeof (v as any).severity === "string"
  );
}

export default {
  isAPIEndpoint,
  isSystemComponent,
  isDatabaseColumn,
  isFileNode,
  isTestScenario,
  isSecurityFinding,
};
