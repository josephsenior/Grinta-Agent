import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSettings } from "#/hooks/query/use-settings";
import { useAddMcpServer } from "#/hooks/mutation/use-add-mcp-server";
import { useUpdateMcpServer } from "#/hooks/mutation/use-update-mcp-server";
import { useDeleteMcpServer } from "#/hooks/mutation/use-delete-mcp-server";
import { MCPServerList } from "#/components/features/settings/mcp-settings/mcp-server-list";
import { MCPServerForm } from "#/components/features/settings/mcp-settings/mcp-server-form";
import { MCPMarketplace } from "#/components/features/settings/mcp-settings/mcp-marketplace";
import { ConfirmationModal } from "#/components/shared/modals/confirmation-modal";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { cn } from "#/utils/utils";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";
import type { MCPSSEServer, MCPStdioServer, MCPSHTTPServer } from "#/types/settings";

type MCPServerType = "sse" | "stdio" | "shttp";

interface MCPServerConfig {
  id: string;
  type: MCPServerType;
  name?: string;
  url?: string;
  api_key?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
}

type ExtendedMCPServer = 
  | (MCPSSEServer & { id: string; type: "sse" })
  | (MCPStdioServer & { id: string; type: "stdio" })
  | (MCPSHTTPServer & { id: string; type: "shttp" });

interface MCPSettingsScreenProps {
  initialTab?: "my-servers" | "marketplace";
}

export function confirmServerDeletion({
  serverToDelete,
  handleDeleteServer,
  setServerToDelete,
}: {
  serverToDelete: string | null;
  handleDeleteServer: (id: string) => void;
  setServerToDelete: (id: string | null) => void;
}) {
  if (!serverToDelete) {
    displayErrorToast("No server selected for deletion.");
    return;
  }
  if (!handleDeleteServer) {
    displayErrorToast("Unable to delete server right now.");
    return;
  }
  handleDeleteServer(serverToDelete);
  setServerToDelete(null);
}

export function createTemplateInstaller({
  addMcpServer,
  setActiveTab,
}: {
  addMcpServer: ReturnType<typeof useAddMcpServer>["mutate"];
  setActiveTab: (tab: "my-servers" | "marketplace") => void;
}) {
  return (template: MCPMarketplaceItem) => {
    const payload = {
      ...template.config,
      name: template.name,
      type: template.type,
    };

    addMcpServer(payload as MCPServerConfig, {
      onSuccess: () => {
        displaySuccessToast("Template installed");
        setActiveTab("my-servers");
      },
      onError: (error: Error) => {
        displayErrorToast(error?.message || "Failed to install template");
      },
    });
  };
}

export default function MCPSettingsScreen({
  initialTab = "my-servers",
}: MCPSettingsScreenProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"my-servers" | "marketplace">(
    initialTab,
  );
  const [isAdding, setIsAdding] = useState(false);
  const [editingServer, setEditingServer] = useState<MCPServerConfig | null>(null);
  const [serverToDelete, setServerToDelete] = useState<string | null>(null);

  const { data: settings, isLoading } = useSettings();
  const { mutate: addMcpServer } = useAddMcpServer();
  const { mutate: updateMcpServer } = useUpdateMcpServer();
  const { mutate: deleteMcpServer } = useDeleteMcpServer();

  const handleAddServer = (payload: MCPServerConfig) => {
    addMcpServer(payload, {
      onSuccess: () => {
        displaySuccessToast("Server added successfully");
        setIsAdding(false);
      },
      onError: (error: Error) => {
        displayErrorToast(error?.message || "Failed to add MCP server");
      },
    });
  };

  const handleUpdateServer = (payload: { serverId: string; server: MCPServerConfig }) => {
    updateMcpServer(payload, {
      onSuccess: () => {
        displaySuccessToast("Server updated successfully");
        setEditingServer(null);
      },
      onError: (error: Error) => {
        displayErrorToast(error?.message || "Failed to update MCP server");
      },
    });
  };

  const handleDeleteServer = (id: string) => {
    deleteMcpServer(id, {
      onSuccess: () => {
        displaySuccessToast("Server deleted successfully");
      },
      onError: () => {
        displayErrorToast("Failed to delete MCP server");
      },
    });
  };

  const installTemplate = createTemplateInstaller({
    addMcpServer,
    setActiveTab,
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-background-tertiary rounded" />
        <div className="h-64 bg-background-tertiary rounded" />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <p className="text-foreground-secondary">
          {t("settings.mcp.error", "Failed to load MCP settings")}
        </p>
        <button
          type="button"
          data-testid="reload-mcp-settings"
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
        >
          {t("common.reload", "Reload")}
        </button>
      </div>
    );
  }

  const mcpConfig = settings.MCP_CONFIG || {
    sse_servers: [],
    stdio_servers: [],
    shttp_servers: [],
  };

  const allServers: ExtendedMCPServer[] = [
    ...mcpConfig.sse_servers.map((s: MCPSSEServer, i: number) => ({
      ...s,
      id: `sse-${i}`,
      type: "sse" as const,
    })),
    ...mcpConfig.stdio_servers.map((s: MCPStdioServer, i: number) => ({
      ...s,
      id: `stdio-${i}`,
      type: "stdio" as const,
    })),
    ...mcpConfig.shttp_servers.map((s: MCPSHTTPServer, i: number) => ({
      ...s,
      id: `shttp-${i}`,
      type: "shttp" as const,
    })),
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex space-x-1 p-1 bg-background-secondary rounded-xl border border-border/50">
          <button
            type="button"
            onClick={() => setActiveTab("my-servers")}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200",
              activeTab === "my-servers"
                ? "bg-background-primary text-foreground shadow-sm"
                : "text-foreground-tertiary hover:text-foreground hover:bg-background-primary/50",
            )}
          >
            {t("settings.mcp.tabs.myServers", "My Servers")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("marketplace")}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200",
              activeTab === "marketplace"
                ? "bg-background-primary text-foreground shadow-sm"
                : "text-foreground-tertiary hover:text-foreground hover:bg-background-primary/50",
            )}
          >
            {t("settings.mcp.tabs.marketplace", "Marketplace")}
          </button>
        </div>

        {activeTab === "my-servers" && (
          <button
            type="button"
            data-testid="add-mcp-server-button"
            onClick={() => setIsAdding(true)}
            className="px-4 py-2 bg-brand-500 text-white text-sm font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-sm shadow-brand-500/20"
          >
            {t("settings.mcp.addServer", "Add MCP Server")}
          </button>
        )}
      </div>

      <div className="bg-background-elevated border border-border/50 rounded-xl overflow-hidden">
        {activeTab === "my-servers" ? (
          <MCPServerList
            servers={allServers}
            onEdit={(server) => setEditingServer(server)}
            onDelete={setServerToDelete}
          />
        ) : (
          <MCPMarketplace
            onInstall={installTemplate}
            installedServers={allServers.map((s) => (s as MCPStdioServer & { id: string }).name ?? (s as { url?: string }).url ?? s.id)}
          />
        )}
      </div>

      {(isAdding || editingServer) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl bg-background-elevated border border-border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6">
              <MCPServerForm
                mode={isAdding ? "add" : "edit"}
                server={editingServer ?? undefined}
                onSubmit={isAdding ? handleAddServer : (server) => handleUpdateServer({ serverId: editingServer?.id ?? "", server })}
                onCancel={() => {
                  setIsAdding(false);
                  setEditingServer(null);
                }}
              />
            </div>
          </div>
        </div>
      )}

      {serverToDelete && (
        <ConfirmationModal
          text={t(
            "settings.mcp.delete.text",
            "Are you sure you want to delete this MCP server? This action cannot be undone.",
          )}
          onConfirm={() =>
            confirmServerDeletion({
              serverToDelete,
              handleDeleteServer,
              setServerToDelete,
            })
          }
          onCancel={() => setServerToDelete(null)}
        />
      )}
    </div>
  );
}
