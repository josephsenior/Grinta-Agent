import { describe, expect, it, beforeEach, vi } from "vitest";
import { getTrajectory } from "#/services/trajectory-service";

const getConversationMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge", () => ({
  __esModule: true,
  default: {
    getConversation: getConversationMock,
  },
}));

describe("trajectory service", () => {
  beforeEach(() => {
    getConversationMock.mockReset();
  });

  it("fetches conversation trajectory", async () => {
    const data = { id: "conv" };
    getConversationMock.mockResolvedValueOnce(data);

    await expect(getTrajectory("conv")).resolves.toBe(data);
    expect(getConversationMock).toHaveBeenCalledWith("conv");
  });
});
