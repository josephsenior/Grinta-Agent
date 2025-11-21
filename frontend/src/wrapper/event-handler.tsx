import React from "react";
import { useHandleWSEvents } from "../hooks/use-handle-ws-events";
import { useHandleRuntimeActive } from "../hooks/use-handle-runtime-active";

export function EventHandler({ children }: React.PropsWithChildren) {
  useHandleWSEvents();
  // This hook requires a conversationId and will throw if not in a conversation route
  useHandleRuntimeActive();

  return children;
}
