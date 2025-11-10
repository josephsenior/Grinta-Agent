import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader2,
  Code,
  Settings,
  TestTube,
  User,
} from "lucide-react";
import type { ComponentType } from "react";

export type FlowStatus =
  | "pending"
  | "in_progress"
  | "complete"
  | "blocked"
  | "unknown";

interface StatusMeta {
  id: FlowStatus;
  label: string;
  nodeClass: string;
  bannerClass: string;
  icon: ComponentType<{ className?: string }>;
  isPending: boolean;
  isInProgress: boolean;
  isComplete: boolean;
  isBlocked: boolean;
}

const STATUS_LOOKUP: Record<FlowStatus, Omit<StatusMeta, "id">> = {
  pending: {
    label: "Pending",
    nodeClass: "bg-neutral-500/10 border-neutral-500/30 text-neutral-400",
    bannerClass:
      "bg-neutral-500/10 border border-neutral-500/30 text-neutral-300",
    icon: Clock,
    isPending: true,
    isInProgress: false,
    isComplete: false,
    isBlocked: false,
  },
  in_progress: {
    label: "In Progress",
    nodeClass: "bg-brand-500/20 border-brand-500/50 text-brand-300",
    bannerClass: "bg-brand-500/20 border border-brand-500/30 text-brand-200",
    icon: Loader2,
    isPending: false,
    isInProgress: true,
    isComplete: false,
    isBlocked: false,
  },
  complete: {
    label: "Complete",
    nodeClass: "bg-green-500/20 border-green-500/50 text-green-300",
    bannerClass: "bg-green-500/20 border border-green-500/30 text-green-200",
    icon: CheckCircle,
    isPending: false,
    isInProgress: false,
    isComplete: true,
    isBlocked: false,
  },
  blocked: {
    label: "Blocked",
    nodeClass: "bg-red-500/20 border-red-500/50 text-red-300",
    bannerClass: "bg-red-500/20 border border-red-500/30 text-red-200",
    icon: AlertTriangle,
    isPending: false,
    isInProgress: false,
    isComplete: false,
    isBlocked: true,
  },
  unknown: {
    label: "Unknown",
    nodeClass: "bg-neutral-500/10 border-neutral-500/30 text-neutral-400",
    bannerClass:
      "bg-neutral-500/10 border border-neutral-500/30 text-neutral-300",
    icon: Clock,
    isPending: false,
    isInProgress: false,
    isComplete: false,
    isBlocked: false,
  },
};

export function getStatusMeta(status: unknown): StatusMeta {
  const normalized = normalizeStatus(status);
  const definition = STATUS_LOOKUP[normalized];
  return { id: normalized, ...definition };
}

export type FlowRole =
  | "product_manager"
  | "architect"
  | "engineer"
  | "qa"
  | "other";

interface RoleMeta {
  id: FlowRole;
  label: string;
  badgeClass: string;
  panelClass: string;
  icon: ComponentType<{ className?: string }>;
}

const ROLE_LOOKUP: Record<FlowRole, Omit<RoleMeta, "id">> = {
  product_manager: {
    label: "Product Manager",
    badgeClass: "text-purple-400 bg-purple-500/20",
    panelClass: "bg-purple-500/10 border-purple-500/20",
    icon: User,
  },
  architect: {
    label: "Architect",
    badgeClass: "text-blue-400 bg-blue-500/20",
    panelClass: "bg-blue-500/10 border-blue-500/20",
    icon: Settings,
  },
  engineer: {
    label: "Engineer",
    badgeClass: "text-green-400 bg-green-500/20",
    panelClass: "bg-green-500/10 border-green-500/20",
    icon: Code,
  },
  qa: {
    label: "QA",
    badgeClass: "text-orange-400 bg-orange-500/20",
    panelClass: "bg-orange-500/10 border-orange-500/20",
    icon: TestTube,
  },
  other: {
    label: "Agent",
    badgeClass: "text-neutral-300 bg-neutral-500/20",
    panelClass: "bg-neutral-500/10 border-neutral-500/20",
    icon: User,
  },
};

export function getRoleMeta(role: unknown): RoleMeta {
  const normalized = normalizeRole(role);
  const definition = ROLE_LOOKUP[normalized];
  return { id: normalized, ...definition };
}

export function normalizeProgress(progress: unknown): number | undefined {
  if (typeof progress === "number" && Number.isFinite(progress)) {
    const clamped = Math.min(100, Math.max(0, progress));
    return Math.round(clamped);
  }
  return undefined;
}

export function formatStepTimestamp(
  value?: string | number | Date,
): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }
  return date.toLocaleTimeString();
}

export function formatStepDateTime(
  value?: string | number | Date,
): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }
  return date.toLocaleString();
}

export function normalizeStatus(status: unknown): FlowStatus {
  if (typeof status !== "string") {
    return "unknown";
  }
  const normalized = status.toLowerCase().replace(/[-\s]/g, "_");
  if (normalized in STATUS_LOOKUP) {
    return normalized as FlowStatus;
  }
  // Map common aliases
  if (["running", "active"].includes(normalized)) {
    return "in_progress";
  }
  if (["success", "completed", "done"].includes(normalized)) {
    return "complete";
  }
  if (["failed", "error"].includes(normalized)) {
    return "blocked";
  }
  if (["waiting", "queued"].includes(normalized)) {
    return "pending";
  }
  return "unknown";
}

export function normalizeRole(role: unknown): FlowRole {
  if (typeof role !== "string") {
    return "other";
  }
  const normalized = role.toLowerCase().replace(/[-\s]/g, "_");
  if (normalized in ROLE_LOOKUP) {
    return normalized as FlowRole;
  }
  for (const { patterns, role: mappedRole } of ROLE_PATTERNS) {
    if (patterns.some((pattern) => normalized.includes(pattern))) {
      return mappedRole;
    }
  }
  return "other";
}

const ROLE_PATTERNS: Array<{ patterns: string[]; role: FlowRole }> = [
  { patterns: ["product", "pm"], role: "product_manager" },
  { patterns: ["architect", "arch"], role: "architect" },
  { patterns: ["engineer", "eng"], role: "engineer" },
  { patterns: ["qa", "test"], role: "qa" },
];
