export type ForgeEventType =
  | "message"
  | "system"
  | "agent_state_changed"
  | "change_agent_state"
  | "run"
  | "read"
  | "write"
  | "edit"
  | "delegate"
  | "browse"
  | "browse_interactive"
  | "reject"
  | "think"
  | "finish"
  | "error"
  | "recall"
  | "mcp"
  | "call_tool_mcp"
  | "task_tracking"
  | "user_rejected"
  | "streaming_chunk";

export type ForgeSourceType = "agent" | "user" | "environment";

interface ForgeBaseEvent {
  id: number;
  source: ForgeSourceType;
  message: string;
  timestamp: string; // ISO 8601
}

export interface ForgeActionEvent<T extends ForgeEventType>
  extends ForgeBaseEvent {
  action: T;
  args: Record<string, unknown>;
}

export interface ForgeObservationEvent<T extends ForgeEventType>
  extends ForgeBaseEvent {
  cause: number;
  observation: T;
  content: string;
  extras: Record<string, unknown>;
}

// Union type for all Forge events (actions and observations)
export type ForgeEvent<T extends ForgeEventType = ForgeEventType> =
  | ForgeActionEvent<T>
  | ForgeObservationEvent<T>;
