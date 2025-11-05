import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Store, ShoppingBag } from "lucide-react";
import { useSettings } from "#/hooks/query/use-settings";
import { useDeleteMcpServer } from "#/hooks/mutation/use-delete-mcp-server";
import { useAddMcpServer } from "#/hooks/mutation/use-add-mcp-server";
import { useUpdateMcpServer } from "#/hooks/mutation/use-update-mcp-server";
import { I18nKey } from "#/i18n/declaration";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";

import { MCPServerList } from "#/components/features/settings/mcp-settings/mcp-server-list";
import { MCPServerForm } from "#/components/features/settings/mcp-settings/mcp-server-form";
import { MCPMarketplace } from "#/components/features/settings/mcp-settings/mcp-marketplace";
import { ConfirmationModal } from "#/components/shared/modals/confirmation-modal";
import { BrandButton } from "#/components/features/settings/brand-button";
import { MCPConfig } from "#/types/settings";

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

type TabType = "my-servers" | "marketplace";

function MCPSettingsScreen() {
  const { t } = useTranslation();
  const { data: settings, isLoading } = useSettings();
  const { mutate: deleteMcpServer } = useDeleteMcpServer();
  const { mutate: addMcpServer } = useAddMcpServer();
  const { mutate: updateMcpServer } = useUpdateMcpServer();

  const [activeTab, setActiveTab] = useState<TabType>("my-servers");
  const [view, setView] = useState<"list" | "add" | "edit">("list");
  const [editingServer, setEditingServer] = useState<MCPServerConfig | null>(
    null,
  );
  const [confirmationModalIsVisible, setConfirmationModalIsVisible] =
    useState(false);
  const [serverToDelete, setServerToDelete] = useState<string | null>(null);

  const mcpConfig: MCPConfig = settings?.MCP_CONFIG || {
    sse_servers: [],
    stdio_servers: [],
    shttp_servers: [],
  };

  // Convert servers to a unified format for display
  const allServers: MCPServerConfig[] = [
    ...mcpConfig.sse_servers.map((server, index) => ({
      id: `sse-${index}`,
      type: "sse" as const,
      url: typeof server === "string" ? server : server.url,
      api_key: typeof server === "object" ? server.api_key : undefined,
    })),
    ...mcpConfig.stdio_servers.map((server, index) => ({
      id: `stdio-${index}`,
      type: "stdio" as const,
      name: server.name,
      command: server.command,
      args: server.args,
      env: server.env,
    })),
    ...mcpConfig.shttp_servers.map((server, index) => ({
      id: `shttp-${index}`,
      type: "shttp" as const,
      url: typeof server === "string" ? server : server.url,
      api_key: typeof server === "object" ? server.api_key : undefined,
    })),
  ];

  const handleAddServer = (serverConfig: MCPServerConfig) => {
    addMcpServer(serverConfig, {
      onSuccess: () => {
        setView("list");
      },
    });
  };

  const handleEditServer = (serverConfig: MCPServerConfig) => {
    updateMcpServer(
      {
        serverId: serverConfig.id,
        server: serverConfig,
      },
      {
        onSuccess: () => {
          setView("list");
        },
      },
    );
  };

  const handleDeleteServer = (serverId: string) => {
    deleteMcpServer(serverId, {
      onSuccess: () => {
        setConfirmationModalIsVisible(false);
      },
    });
  };

  const handleEditClick = (server: MCPServerConfig) => {
    setEditingServer(server);
    setView("edit");
  };

  const handleDeleteClick = (serverId: string) => {
    setServerToDelete(serverId);
    setConfirmationModalIsVisible(true);
  };

  const handleConfirmDelete = () => {
    if (serverToDelete) {
      handleDeleteServer(serverToDelete);
      setServerToDelete(null);
    }
  };

  const handleCancelDelete = () => {
    setConfirmationModalIsVisible(false);
    setServerToDelete(null);
  };

  const handleInstallFromMarketplace = (mcp: MCPMarketplaceItem) => {
    const serverConfig: MCPServerConfig = {
      id: `${mcp.type}-${Date.now()}`,
      type: mcp.type,
      name: mcp.config.command ? mcp.name : undefined,
      command: mcp.config.command,
      args: mcp.config.args,
      env: mcp.config.env,
      url: mcp.config.url,
    };

    addMcpServer(serverConfig, {
      onSuccess: () => {
        // Switch to My Servers tab after successful install
        setActiveTab("my-servers");
      },
    });
  };

  // Get installed server names for marketplace
  const installedServerNames = allServers.map((server) => server.name || "");

  if (isLoading) {
    return (
      <div className="px-11 py-9 flex flex-col gap-5">
        <div className="animate-pulse">
          <div className="h-6 bg-black rounded w-1/4 mb-4" />
          <div className="h-4 bg-black rounded w-1/2 mb-8" />
          <div className="h-10 bg-black rounded w-32" />
        </div>
      </div>
    );
  }

  return (
    <div className="px-11 py-9 flex flex-col gap-5">
      {/* Tab Navigation */}
      <div className="flex items-center gap-1 p-1 bg-black border border-violet-500/20 rounded-lg w-fit">
        <button
          type="button"
          onClick={() => {
            setActiveTab("my-servers");
            setView("list");
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
            activeTab === "my-servers"
              ? "bg-brand-500 text-white shadow-sm"
              : "text-foreground-secondary hover:text-foreground hover:bg-black"
          }`}
        >
          <Store className="w-4 h-4" />
          My Servers
          {allServers.length > 0 && (
            <span
              className={`px-1.5 py-0.5 text-xs rounded-full ${
                activeTab === "my-servers"
                  ? "bg-white/20 text-white"
                  : "bg-black text-foreground-secondary"
              }`}
            >
              {allServers.length}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("marketplace")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
            activeTab === "marketplace"
              ? "bg-brand-500 text-white shadow-sm"
              : "text-foreground-secondary hover:text-foreground hover:bg-black"
          }`}
        >
          <ShoppingBag className="w-4 h-4" />
          Marketplace
        </button>
      </div>

      {/* Content */}
      {activeTab === "my-servers" && view === "list" && (
        <>
          <BrandButton
            testId="add-mcp-server-button"
            type="button"
            variant="primary"
            onClick={() => setView("add")}
            isDisabled={isLoading}
          >
            {t(I18nKey.SETTINGS$MCP_ADD_SERVER)}
          </BrandButton>

          <MCPServerList
            servers={allServers}
            onEdit={handleEditClick}
            onDelete={handleDeleteClick}
          />
        </>
      )}

      {activeTab === "my-servers" && view === "add" && (
        <MCPServerForm
          mode="add"
          existingServers={allServers}
          onSubmit={handleAddServer}
          onCancel={() => setView("list")}
        />
      )}

      {activeTab === "my-servers" && view === "edit" && editingServer && (
        <MCPServerForm
          mode="edit"
          server={editingServer}
          existingServers={allServers}
          onSubmit={handleEditServer}
          onCancel={() => {
            setView("list");
            setEditingServer(null);
          }}
        />
      )}

      {activeTab === "marketplace" && (
        <MCPMarketplace
          installedServers={installedServerNames}
          onInstall={handleInstallFromMarketplace}
        />
      )}

      {confirmationModalIsVisible && (
        <ConfirmationModal
          text={t(I18nKey.SETTINGS$MCP_CONFIRM_DELETE)}
          onConfirm={handleConfirmDelete}
          onCancel={handleCancelDelete}
        />
      )}
    </div>
  );
}

export default MCPSettingsScreen;
