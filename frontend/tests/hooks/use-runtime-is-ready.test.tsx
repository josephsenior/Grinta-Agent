import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

const useActiveConversationMock = vi.fn();
const useSelectorMock = vi.fn();

vi.mock("react-redux", () => ({
  useSelector: (selector: (state: any) => any) => useSelectorMock(selector),
}));

vi.mock("#/hooks/query/use-active-conversation", () => ({
  useActiveConversation: () => useActiveConversationMock(),
}));

import { RUNTIME_INACTIVE_STATES } from "#/types/agent-state";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";

describe("useRuntimeIsReady", () => {
  const originalProcess = globalThis.process;
  const originalWindow = globalThis.window;
  let agentState: string | undefined;
  const originalImportMetaEnvFlag = import.meta.env?.VITE_PLAYWRIGHT_STUB;

  beforeEach(() => {
    vi.clearAllMocks();
    (globalThis as any).process = originalProcess;
    (globalThis as any).window = originalWindow;
    if (import.meta.env) {
      (import.meta.env as any).VITE_PLAYWRIGHT_STUB = originalImportMetaEnvFlag;
    }
    useSelectorMock.mockImplementation((selector: (state: any) => any) =>
      selector({ agent: { curAgentState: agentState } }),
    );
    useActiveConversationMock.mockReturnValue({ data: undefined });
    vi.spyOn(console, "log").mockImplementation(() => undefined);
    agentState = undefined;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).process = originalProcess;
    (globalThis as any).window = originalWindow;
    if (import.meta.env) {
      (import.meta.env as any).VITE_PLAYWRIGHT_STUB = originalImportMetaEnvFlag;
    }
  });

  it("returns true when Playwright env flag set via process", () => {
    (globalThis as any).process = { env: { PLAYWRIGHT: "1" } };

    const result = useRuntimeIsReady();

    expect(result).toBe(true);
  });

  it("returns true when conversation is running", () => {
    useActiveConversationMock.mockReturnValue({ data: { status: "RUNNING" } });
    agentState = RUNTIME_INACTIVE_STATES[0];

    const result = useRuntimeIsReady();

    expect(result).toBe(true);
  });

  it("returns true when agent state is active", () => {
    useActiveConversationMock.mockReturnValue({ data: { status: "IDLE" } });
    agentState = "ACTIVE";

    const result = useRuntimeIsReady();

    expect(result).toBe(true);
  });

  it("returns false when conversation inactive and agent state inactive", () => {
    useActiveConversationMock.mockReturnValue({ data: { status: "PENDING" } });
    agentState = RUNTIME_INACTIVE_STATES[0];
    (globalThis as any).process = { env: {} };
    (globalThis as any).window = undefined;
    if (import.meta.env) {
      (import.meta.env as any).VITE_PLAYWRIGHT_STUB = undefined;
    }

    const result = useRuntimeIsReady();

    expect(result).toBe(false);
  });

  it("honors window Playwright flag", () => {
    (globalThis as any).process = { env: {} };
    (globalThis as any).window = { __Forge_PLAYWRIGHT: true };

    const result = useRuntimeIsReady();

    expect(result).toBe(true);
  });

  it("honors import.meta env Playwright flag", () => {
    (globalThis as any).process = { env: {} };
    (import.meta.env as any).VITE_PLAYWRIGHT_STUB = true;

    const result = useRuntimeIsReady();

    expect(result).toBe(true);
  });
});
