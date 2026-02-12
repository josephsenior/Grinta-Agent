import { useSelector } from "react-redux";
import type { RootState } from "#/store";

/**
 * Access the current agent state from Redux.
 *
 * Replaces the repeated `useSelector((state: RootState) => state.agent)` pattern
 * and provides a stable reference for derived state in the future.
 */
export function useAgentState() {
  return useSelector((state: RootState) => state.agent.curAgentState);
}
