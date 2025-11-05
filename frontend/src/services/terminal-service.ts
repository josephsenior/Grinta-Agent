import ActionType from "#/types/action-type";

export function getTerminalCommand(command: string, hidden: boolean = false) {
  return { action: ActionType.RUN, args: { command, hidden } };
}
