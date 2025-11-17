import React from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";

describe("useWSErrorMessage", () => {
  const queryClient = new QueryClient();

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  afterEach(() => {
    queryClient.clear();
    queryClient.removeQueries({ queryKey: ["error_message"] });
  });

  it("sets and retrieves the websocket error message", () => {
    const { result } = renderHook(() => useWSErrorMessage(), { wrapper });

    act(() => {
      result.current.setErrorMessage("connection error");
    });

    expect(result.current.getErrorMessage()).toBe("connection error");
    expect(queryClient.getQueryData(["error_message"])).toBe("connection error");
  });

  it("removes the websocket error message", () => {
    const { result } = renderHook(() => useWSErrorMessage(), { wrapper });

    act(() => {
      result.current.setErrorMessage("ephemeral error");
    });

    act(() => {
      result.current.removeErrorMessage();
    });

    expect(result.current.getErrorMessage()).toBeUndefined();
    expect(queryClient.getQueryData(["error_message"])).toBeUndefined();
  });
});

