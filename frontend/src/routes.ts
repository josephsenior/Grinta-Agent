import {
  type RouteConfig,
  layout,
  index,
  route,
} from "@react-router/dev/routes";

export default [
  layout("routes/root-layout.tsx", [
    index("routes/index-redirect.tsx"),
    route("search", "routes/search.tsx"),
    route("settings", "routes/settings.tsx", [
      index("routes/llm-settings.tsx"),
      route("app", "routes/app-settings.tsx"),
      route("mcp", "routes/mcp-settings.tsx"),
    ]),
    route("conversation", "routes/conversation-redirect.tsx"),
    route("conversations/:conversationId", "routes/conversation.tsx", [
      index("routes/workspace-tab.tsx"),
      route("terminal", "routes/terminal-tab.tsx"),
      route("browser", "routes/browser-tab.tsx"),
    ]),
    route("*", "routes/404.tsx"), // Catch-all 404 route
  ]),
] satisfies RouteConfig;
