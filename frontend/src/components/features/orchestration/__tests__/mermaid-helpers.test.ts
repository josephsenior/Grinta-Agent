import { beforeEach, describe, expect, it, vi } from "vitest";
import { ensureMermaid, resetMermaidCache } from "../mermaid-helpers";

vi.mock("mermaid", () => {
  const initialize = vi.fn();
  return {
    default: {
      initialize,
    },
  };
});

describe("mermaid-helpers", () => {
  beforeEach(() => {
    resetMermaidCache();
  });

  it("initializes mermaid only once", async () => {
    const mermaidModule = await import("mermaid");
    const initializeSpy = mermaidModule.default.initialize as ReturnType<
      typeof vi.fn
    >;

    const first = await ensureMermaid();
    const second = await ensureMermaid();

    expect(first).toBe(second);
    expect(initializeSpy).toHaveBeenCalledTimes(1);
  });
});
