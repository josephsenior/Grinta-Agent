import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  useFileActions,
  useLatestStreamingContent,
  useStreamingChunks,
  useWsEvents,
} from "#/hooks/use-ws-events";

const useWsClientMock = vi.fn();

vi.mock("#/context/ws-client-provider", () => ({
  useWsClient: () => useWsClientMock(),
}));

describe("useWsEvents family", () => {
  const baseClient = {
    parsedEvents: [],
    webSocketStatus: "CONNECTED" as const,
    isLoadingMessages: false,
  };

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("returns default values when websocket client is unavailable", () => {
    useWsClientMock.mockReturnValue(undefined);

    const { result } = renderHook(() => useWsEvents());

    expect(result.current).toEqual({
      parsedEvents: [],
      webSocketStatus: "DISCONNECTED",
      isLoadingMessages: false,
    });
  });

  it("exposes websocket client values when available", () => {
    const client = {
      ...baseClient,
      parsedEvents: [{ action: "message" }],
      webSocketStatus: "CONNECTED" as const,
      isLoadingMessages: true,
    };
    useWsClientMock.mockReturnValue(client);

    const { result } = renderHook(() => useWsEvents());

    expect(result.current).toEqual({
      parsedEvents: client.parsedEvents,
      webSocketStatus: "CONNECTED",
      isLoadingMessages: true,
    });
  });

  it("filters streaming chunk actions via useStreamingChunks", () => {
    const events = [
      { action: "streaming_chunk", args: { accumulated: "first" } },
      { action: "message" },
      { action: "streaming_chunk", args: { accumulated: "second" } },
    ];
    useWsClientMock.mockReturnValue({ ...baseClient, parsedEvents: events });

    const { result } = renderHook(() => useStreamingChunks());

    expect(result.current).toEqual([
      events[0],
      events[2],
    ]);
  });

  it("returns file write and edit actions via useFileActions", () => {
    const writeAction = { action: "write", args: { path: "file-A" } };
    const editAction = { action: "edit", args: { path: "file-B" } };
    const events = [
      writeAction,
      { action: "streaming_chunk" },
      editAction,
      { action: "message" },
    ];
    useWsClientMock.mockReturnValue({ ...baseClient, parsedEvents: events });

    const { result } = renderHook(() => useFileActions());

    expect(result.current).toEqual({
      fileWriteActions: [writeAction],
      fileEditActions: [editAction],
      allFileActions: [writeAction, editAction],
    });
  });

  describe("useLatestStreamingContent", () => {
    it("returns the most recent accumulated streaming content", () => {
      const events = [
        { action: "streaming_chunk", args: { accumulated: "partial" } },
        { action: "streaming_chunk", args: { accumulated: "final" } },
      ];
      useWsClientMock.mockReturnValue({ ...baseClient, parsedEvents: events });

      const { result } = renderHook(() => useLatestStreamingContent());

      expect(result.current).toBe("final");
    });

    it("returns empty string when no streaming chunks exist", () => {
      useWsClientMock.mockReturnValue({
        ...baseClient,
        parsedEvents: [{ action: "message" }],
      });

      const { result } = renderHook(() => useLatestStreamingContent());

      expect(result.current).toBe("");
    });

    it("returns accumulated content scoped by filePath when available", () => {
      const events = [
        { action: "streaming_chunk", args: { accumulated: "" } },
        { action: "streaming_chunk", args: { accumulated: "scoped content" } },
      ];
      useWsClientMock.mockReturnValue({ ...baseClient, parsedEvents: events });

      const { result } = renderHook(() =>
        useLatestStreamingContent("some/file.ts"),
      );

      expect(result.current).toBe("scoped content");
    });
  });
});

