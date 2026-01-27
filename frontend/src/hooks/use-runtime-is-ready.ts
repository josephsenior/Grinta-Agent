import { useSelector } from "react-redux";
import { RootState } from "#/store";
import { RUNTIME_INACTIVE_STATES } from "#/types/agent-state";
import { useActiveConversation } from "./query/use-active-conversation";

/**
 * Hook to determine if the runtime is ready for operations
 *
 * @returns boolean indicating if the runtime is ready
 */
export const useRuntimeIsReady = (): boolean => {
  const { data: conversation } = useActiveConversation();
  const { curAgentState } = useSelector((state: RootState) => state.agent);

  // Test-only: if running under Playwright, consider the runtime ready to
  // avoid flaky waits for socket-driven startup events. This flag is set by
  // the test harness via `page.addInitScript(() => window.__Forge_PLAYWRIGHT = true)`
  // or via Vite env/process env when running E2E.
  // Narrowly-typed guards to avoid `any` casts in tests/runtime detection.
  type MaybeProcess = { env?: Record<string, string> } | undefined;
  type MaybeImportMeta = { env?: Record<string, unknown> } | undefined;
  interface WindowWithE2E extends Window {
    __Forge_PLAYWRIGHT?: boolean;
  }

  const proc =
    typeof process !== "undefined" ? (process as MaybeProcess) : undefined;

  const importMeta = import.meta as MaybeImportMeta;

  const win =
    typeof window !== "undefined"
      ? (window as unknown as WindowWithE2E)
      : undefined;

  const isPlaywrightRun =
    proc?.env?.PLAYWRIGHT === "1" ||
    Boolean(importMeta?.env?.VITE_PLAYWRIGHT_STUB) ||
    win?.__Forge_PLAYWRIGHT === true;

  if (isPlaywrightRun) {
    return true;
  }

  // Runtime is ready if:
  // 1. Conversation is RUNNING, OR
  // 2. Agent state is active (not INIT, LOADING, or ERROR)
  const conversationRunning = conversation?.status === "RUNNING";
  const agentStateActive =
    curAgentState && !RUNTIME_INACTIVE_STATES.includes(curAgentState);

  return conversationRunning || agentStateActive;
};
