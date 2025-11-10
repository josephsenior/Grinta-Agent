import { ForgeActionEvent } from "./base";
import { ActionSecurityRisk } from "#/state/security-analyzer-slice";

export interface UserMessageAction extends ForgeActionEvent<"message"> {
  source: "user";
  args: {
    content: string;
    image_urls: string[];
    file_urls: string[];
  };
}

export interface SystemMessageAction extends ForgeActionEvent<"system"> {
  source: "agent" | "environment";
  args: {
    content: string;
    tools: Array<Record<string, unknown>> | null;
    Forge_version: string | null;
    agent_class: string | null;
  };
}

export interface CommandAction extends ForgeActionEvent<"run"> {
  source: "agent" | "user";
  args: {
    command: string;
    security_risk: ActionSecurityRisk;
    confirmation_state: "confirmed" | "rejected" | "awaiting_confirmation";
    thought: string;
    hidden?: boolean;
  };
}

export interface AssistantMessageAction extends ForgeActionEvent<"message"> {
  source: "agent";
  args: {
    thought: string;
    image_urls: string[] | null;
    file_urls: string[];
    wait_for_response: boolean;
  };
}

export interface IPythonAction extends ForgeActionEvent<"run_ipython"> {
  source: "agent";
  args: {
    code: string;
    security_risk: ActionSecurityRisk;
    confirmation_state: "confirmed" | "rejected" | "awaiting_confirmation";
    kernel_init_code: string;
    thought: string;
  };
}

export interface ThinkAction extends ForgeActionEvent<"think"> {
  source: "agent";
  args: {
    thought: string;
  };
}

export interface StreamingChunkAction
  extends ForgeActionEvent<"streaming_chunk"> {
  source: "agent";
  args: {
    chunk: string;
    accumulated: string;
    is_final: boolean;
  };
}

export interface FinishAction extends ForgeActionEvent<"finish"> {
  source: "agent";
  args: {
    final_thought: string;
    outputs: Record<string, unknown>;
    thought: string;
  };
}

export interface DelegateAction extends ForgeActionEvent<"delegate"> {
  source: "agent";
  timeout: number;
  args: {
    agent: "BrowsingAgent";
    inputs: Record<string, string>;
    thought: string;
  };
}

export interface BrowseAction extends ForgeActionEvent<"browse"> {
  source: "agent";
  args: {
    url: string;
    thought: string;
  };
}

export interface BrowseInteractiveAction
  extends ForgeActionEvent<"browse_interactive"> {
  source: "agent";
  timeout: number;
  args: {
    browser_actions: string;
    thought: string | null;
    browsergym_send_msg_to_user: string;
  };
}

export interface FileReadAction extends ForgeActionEvent<"read"> {
  source: "agent";
  args: {
    path: string;
    thought: string;
    security_risk: ActionSecurityRisk | null;
    impl_source?: string;
    view_range?: number[] | null;
  };
}

export interface FileWriteAction extends ForgeActionEvent<"write"> {
  source: "agent";
  args: {
    path: string;
    content: string;
    thought: string;
  };
}

export interface FileEditAction extends ForgeActionEvent<"edit"> {
  source: "agent";
  args: {
    path: string;
    command?: string;
    file_text?: string | null;
    view_range?: number[] | null;
    old_str?: string | null;
    new_str?: string | null;
    insert_line?: number | null;
    content?: string;
    start?: number;
    end?: number;
    thought: string;
    security_risk: ActionSecurityRisk | null;
    impl_source?: string;
  };
}

export interface RejectAction extends ForgeActionEvent<"reject"> {
  source: "agent";
  args: {
    thought: string;
  };
}

export interface RecallAction extends ForgeActionEvent<"recall"> {
  source: "agent";
  args: {
    recall_type: "workspace_context" | "knowledge";
    query: string;
    thought: string;
  };
}

export interface MCPAction extends ForgeActionEvent<"call_tool_mcp"> {
  source: "agent";
  args: {
    name: string;
    arguments: Record<string, unknown>;
    thought?: string;
  };
}

export interface TaskTrackingAction extends ForgeActionEvent<"task_tracking"> {
  source: "agent";
  args: {
    command: string;
    task_list: Array<{
      id: string;
      title: string;
      status: "todo" | "in_progress" | "done";
      notes?: string;
    }>;
    thought: string;
  };
}

export type ForgeAction =
  | UserMessageAction
  | AssistantMessageAction
  | SystemMessageAction
  | CommandAction
  | IPythonAction
  | ThinkAction
  | StreamingChunkAction
  | FinishAction
  | DelegateAction
  | BrowseAction
  | BrowseInteractiveAction
  | FileReadAction
  | FileEditAction
  | FileWriteAction
  | RejectAction
  | RecallAction
  | MCPAction
  | TaskTrackingAction;
