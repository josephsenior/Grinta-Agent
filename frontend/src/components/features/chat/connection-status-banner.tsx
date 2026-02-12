import { useWsClient } from "#/context/ws-client-provider";

/**
 * Thin banner shown at the top of the chat area when the WebSocket is
 * disconnected or reconnecting.  Dismisses automatically once the
 * connection is re-established.
 */
export function ConnectionStatusBanner() {
  const { webSocketStatus } = useWsClient();

  if (webSocketStatus === "CONNECTED") return null;

  const isConnecting = webSocketStatus === "CONNECTING";

  return (
    <div
      className={`flex items-center justify-center gap-2 px-3 py-1.5 text-xs font-medium ${
        isConnecting
          ? "bg-yellow-500/15 text-yellow-300"
          : "bg-red-500/15 text-red-400"
      }`}
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          isConnecting ? "bg-yellow-400 animate-pulse" : "bg-red-500"
        }`}
      />
      {isConnecting
        ? "Reconnecting to server..."
        : "Connection lost — waiting to reconnect"}
    </div>
  );
}
