import { AgentState } from "../agent-state";
import { ForgeObservationEvent } from "./base";

export interface AgentStateChangeObservation
  extends ForgeObservationEvent<"agent_state_changed"> {
  source: "agent";
  extras: {
    agent_state: AgentState;
    reason?: string;
  };
}

export interface CommandObservation extends ForgeObservationEvent<"run"> {
  source: "agent" | "user";
  extras: {
    command: string;
    hidden?: boolean;
    metadata: Record<string, unknown>;
  };
}

export interface BrowseObservation extends ForgeObservationEvent<"browse"> {
  source: "agent";
  extras: {
    url: string;
    screenshot: string;
    error: boolean;
    open_page_urls: string[];
    active_page_index: number;
    dom_object: Record<string, unknown>;
    axtree_object: Record<string, unknown>;
    extra_element_properties: Record<string, unknown>;
    last_browser_action: string;
    last_browser_action_error: unknown;
    focused_element_bid: string;
  };
}

export interface BrowseInteractiveObservation
  extends ForgeObservationEvent<"browse_interactive"> {
  source: "agent";
  extras: {
    url: string;
    screenshot: string;
    error: boolean;
    open_page_urls: string[];
    active_page_index: number;
    dom_object: Record<string, unknown>;
    axtree_object: Record<string, unknown>;
    extra_element_properties: Record<string, unknown>;
    last_browser_action: string;
    last_browser_action_error: unknown;
    focused_element_bid: string;
  };
}

export interface WriteObservation extends ForgeObservationEvent<"write"> {
  source: "agent";
  extras: {
    path: string;
    content: string;
  };
}

export interface ReadObservation extends ForgeObservationEvent<"read"> {
  source: "agent";
  extras: {
    path: string;
    impl_source: string;
  };
}

export interface EditObservation extends ForgeObservationEvent<"edit"> {
  source: "agent";
  extras: {
    path: string;
    diff: string;
    impl_source: string;
    old_content?: string | null;
    new_content?: string | null;
    preview?: boolean;
  };
}

export interface ErrorObservation extends ForgeObservationEvent<"error"> {
  source: "user";
  extras: {
    error_id?: string;
  };
}

export interface AgentThinkObservation extends ForgeObservationEvent<"think"> {
  source: "agent";
  extras: {
    thought: string;
  };
}

export interface PlaybookKnowledge {
  name: string;
  trigger: string;
  content: string;
}

export interface RecallObservation extends ForgeObservationEvent<"recall"> {
  source: "agent";
  extras: {
    recall_type?: "workspace_context" | "knowledge";
    repo_name?: string;
    repo_directory?: string;
    repo_instructions?: string;
    runtime_hosts?: Record<string, number>;
    custom_secrets_descriptions?: Record<string, string>;
    additional_agent_instructions?: string;
    conversation_instructions?: string;
    date?: string;
    playbook_knowledge?: PlaybookKnowledge[];
  };
}

export interface MCPObservation extends ForgeObservationEvent<"mcp"> {
  source: "agent";
  extras: {
    name: string;
    arguments: Record<string, unknown>;
  };
}

export interface UserRejectedObservation
  extends ForgeObservationEvent<"user_rejected"> {
  source: "agent";
  extras: Record<string, unknown>;
}

export type ForgeObservation =
  | AgentStateChangeObservation
  | AgentThinkObservation
  | CommandObservation
  | BrowseObservation
  | BrowseInteractiveObservation
  | WriteObservation
  | ReadObservation
  | EditObservation
  | ErrorObservation
  | RecallObservation
  | MCPObservation
  | UserRejectedObservation;
