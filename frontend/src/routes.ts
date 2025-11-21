import {
  type RouteConfig,
  layout,
  index,
  route,
} from "@react-router/dev/routes";

export default [
  layout("routes/root-layout.tsx", [
    index("routes/home.tsx"),
    // Auth routes (public, no auth required)
    route("auth/login", "routes/auth/login.tsx"),
    route("auth/register", "routes/auth/register.tsx"),
    route("auth/forgot-password", "routes/auth/forgot-password.tsx"),
    route("auth/reset-password", "routes/auth/reset-password.tsx"),
    route("dashboard", "routes/dashboard.tsx"),
    route("profile", "routes/profile.tsx"), // Profile page
    route("help", "routes/help.tsx"),
    route("notifications", "routes/notifications.tsx"),
    route("search", "routes/search.tsx"),
    route("accept-tos", "routes/accept-tos.tsx"),
    route("about", "routes/about.tsx"),
    route("pricing", "routes/pricing.tsx"),
    route("contact", "routes/contact.tsx"),
    route("terms", "routes/terms.tsx"),
    route("privacy", "routes/privacy.tsx"),
    route("settings", "routes/settings.tsx", [
      index("routes/llm-settings.tsx"),
      route("mcp", "routes/mcp-settings.tsx"),
      route("user", "routes/user-settings.tsx"),
      route("integrations", "routes/git-settings.tsx"),
      route("databases", "routes/database-settings.tsx"),
      route("knowledge-base", "routes/knowledge-base-settings.tsx"),
      route("memory", "routes/memory-settings.tsx"),
      route("analytics", "routes/analytics-settings.tsx"),
      route("prompts", "routes/prompts-settings.tsx"),
      route("snippets", "routes/snippets-settings.tsx"),
      route("slack", "routes/slack-settings.tsx"),
      route("backup", "routes/backup-settings.tsx"),
      route("app", "routes/app-settings.tsx"),
      route("billing", "routes/billing.tsx"),
      route("secrets", "routes/secrets-settings.tsx"),
      route("api-keys", "routes/api-keys.tsx"),
    ]),
    route("database-browser", "routes/database-browser.tsx"),
    route("conversation", "routes/conversation-redirect.tsx"),
    route("conversations", "routes/conversations-list.tsx"),
    route("conversations/:conversationId", "routes/conversation.tsx", [
      index("routes/workspace-tab.tsx"),
      route("browser", "routes/browser-tab.tsx"),
      route("jupyter", "routes/jupyter-tab.tsx"),
      route("served", "routes/served-tab.tsx"),
      route("terminal", "routes/terminal-tab.tsx"),
      route("vscode", "routes/vscode-tab.tsx"),
    ]),
    // Admin routes (requires admin role)
    route("admin/users", "routes/admin/users.tsx"),
    route("admin/users/:userId", "routes/admin/users/[userId].tsx"),
    route("*", "routes/404.tsx"), // Catch-all 404 route
  ]),
] satisfies RouteConfig;
