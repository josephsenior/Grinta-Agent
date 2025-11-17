import { describe, expect, it, beforeEach, vi } from "vitest";
import { SuggestionsService } from "#/api/suggestions-service/suggestions-service.api";

const forgeGetMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge-axios", () => ({
  Forge: {
    get: forgeGetMock,
  },
}));

describe("SuggestionsService", () => {
  beforeEach(() => {
    forgeGetMock.mockReset();
  });

  it("fetches suggested tasks", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: [{ id: "1" }] });

    await expect(SuggestionsService.getSuggestedTasks()).resolves.toEqual([{ id: "1" }]);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/user/suggested-tasks");
  });
});
