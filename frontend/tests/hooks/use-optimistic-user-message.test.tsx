import { describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => queryClientMock,
}));

const setQueryDataMock = vi.fn();
const getQueryDataMock = vi.fn();
const removeQueriesMock = vi.fn();
const queryClientMock = {
  setQueryData: setQueryDataMock,
  getQueryData: getQueryDataMock,
  removeQueries: removeQueriesMock,
};

import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";

describe("useOptimisticUserMessage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sets and retrieves optimistic user message", () => {
    const hook = useOptimisticUserMessage();
    getQueryDataMock.mockReturnValueOnce("hello");

    hook.setOptimisticUserMessage("hello");
    const value = hook.getOptimisticUserMessage();

    expect(setQueryDataMock).toHaveBeenCalledWith(["optimistic_user_message"], "hello");
    expect(getQueryDataMock).toHaveBeenCalledWith(["optimistic_user_message"]);
    expect(value).toBe("hello");
  });

  it("removes optimistic user message", () => {
    const hook = useOptimisticUserMessage();

    hook.removeOptimisticUserMessage();

    expect(removeQueriesMock).toHaveBeenCalledWith({ queryKey: ["optimistic_user_message"] });
  });
});
