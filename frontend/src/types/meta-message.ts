// MetaGPT-inspired message envelope and document types for structured messaging

export type Role = "user" | "agent" | "system" | "tool";

export interface MetaMessageEnvelope {
  id: string; // unique id for this message
  role: Role;
  content: string;
  timestamp: string; // ISO
  parentId?: string | null;
  route?: {
    from?: string;
    to?: string | "*";
    causeBy?: string; // message id or reason
  };
  attachments?: {
    image_urls?: string[];
    file_urls?: string[];
  };
  // Extra metadata for orchestration or planning
  meta?: Record<string, unknown>;
}

export interface MetaDocument {
  root_path?: string;
  filename?: string;
  content: string;
}

export interface ToolCall {
  tool: string; // e.g. "runTests", "gitCommit"
  args?: Record<string, unknown>;
  callId?: string; // correlate to result
}

export interface ToolResult<T = unknown> {
  tool: string;
  callId?: string;
  ok: boolean;
  data?: T;
  error?: string;
}
