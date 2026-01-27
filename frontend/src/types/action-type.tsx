enum ActionType {
  // Initializes the agent. Only sent by client.
  INIT = "initialize",

  // Represents a message from the user or agent.
  MESSAGE = "message",

  // Represents a system message for an agent, including the system prompt and available tools.
  SYSTEM = "system",

  // Reads the contents of a file.
  READ = "read",

  // Writes the contents to a file.
  WRITE = "write",

  // Runs a command.
  RUN = "run",

  // Opens a web page.
  BROWSE = "browse",

  // Interact with the browser instance.
  BROWSE_INTERACTIVE = "browse_interactive",

  // Logs a thought.
  THINK = "think",

  // If you're absolutely certain that you've completed your task and have tested your work,
  // use the finish action to stop working.
  FINISH = "finish",

  // Reject a request from user or another agent.
  REJECT = "reject",

  // Changes the state of the agent, e.g. to paused or running
  CHANGE_AGENT_STATE = "change_agent_state",

  // Interact with the MCP server.
  MCP = "call_tool_mcp",

  // Views or updates the task list for task management.
  TASK_TRACKING = "task_tracking",
}

export default ActionType;
