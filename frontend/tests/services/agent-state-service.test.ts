import { describe, expect, it } from "vitest";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import ActionType from "#/types/action-type";
import { AgentState } from "#/types/agent-state";

describe("generateAgentStateChangeEvent", () => {
  it("returns action payload for provided state", () => {
    const event = generateAgentStateChangeEvent(AgentState.ERROR);
    expect(event).toEqual({
      action: ActionType.CHANGE_AGENT_STATE,
      args: { agent_state: AgentState.ERROR },
    });
  });

  it("handles different agent states", () => {
    const initEvent = generateAgentStateChangeEvent(AgentState.INIT);
    const runningEvent = generateAgentStateChangeEvent(AgentState.RUNNING);

    expect(initEvent.args.agent_state).toBe(AgentState.INIT);
    expect(runningEvent.args.agent_state).toBe(AgentState.RUNNING);
  });
});
