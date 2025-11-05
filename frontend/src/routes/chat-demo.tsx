import React from "react";
import { ChatInterfaceDemo } from "#/components/features/chat/chat-interface-demo";

export default function ChatDemoRoute() {
  return <ChatInterfaceDemo />;
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
