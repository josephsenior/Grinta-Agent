import { describe, expect, it } from "vitest";
import { getTerminalCommand } from "#/services/terminal-service";
import ActionType from "#/types/action-type";

describe("getTerminalCommand", () => {
  it("creates run action with explicit hidden state", () => {
    const payload = getTerminalCommand("ls", true);
    expect(payload).toEqual({
      action: ActionType.RUN,
      args: { command: "ls", hidden: true },
    });
  });

  it("defaults hidden to false", () => {
    const payload = getTerminalCommand("pwd");
    expect(payload.args).toEqual({ command: "pwd", hidden: false });
  });
});
