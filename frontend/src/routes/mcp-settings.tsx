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
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";

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

interface MCPSettingsScreenProps {
  initialTab?: TabType;
}

function MCPSettingsScreen({
  initialTab = "my-servers",
}: MCPSettingsScreenProps = {}) {
  const { t } = useTranslation();
  const { data: settings, isLoading } = useSettings();
  const { mutate: deleteMcpServer } = useDeleteMcpServer();
  const { mutate: addMcpServer } = useAddMcpServer();
  const { mutate: updateMcpServer } = useUpdateMcpServer();

  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
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

  const allServers = React.useMemo(
    () => buildServerList(mcpConfig),
    [mcpConfig],
  );

  const handleAddServer = (serverConfig: MCPServerConfig) => {
    addMcpServer(serverConfig, {
      onSuccess: () => {
        displaySuccessToast("Server added successfully");
        setView("list");
      },
      onError: (error) => {
        displayErrorToast(
          error instanceof Error ? error.message : "Failed to add MCP server",
        );
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
          displaySuccessToast("Server updated successfully");
          setView("list");
        },
        onError: (error) => {
          displayErrorToast(
            error instanceof Error
              ? error.message
              : "Failed to update MCP server",
          );
        },
      },
    );
  };

  const handleDeleteServer = (serverId: string) => {
    deleteMcpServer(serverId, {
      onSuccess: () => {
        displaySuccessToast("Server deleted successfully");
        setConfirmationModalIsVisible(false);
      },
      onError: (error) => {
        displayErrorToast(
          error instanceof Error
            ? error.message
            : "Failed to delete MCP server",
        );
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
    confirmServerDeletion({
      serverToDelete,
      handleDeleteServer,
      setServerToDelete,
    });
  };

  const handleCancelDelete = () => {
    setConfirmationModalIsVisible(false);
    setServerToDelete(null);
  };

  const handleInstallFromMarketplace = React.useCallback(
    createTemplateInstaller({
      addMcpServer,
      setActiveTab,
    }),
    [addMcpServer, setActiveTab],
  );

  // Get installed server names for marketplace
  const installedServerNames = React.useMemo(
    () => allServers.map((server) => server.name || ""),
    [allServers],
  );

  if (isLoading) {
    return <McpSettingsSkeleton />;
  }

  if (!settings) {
    return (
      <div className="px-11 py-9">
        <div className="bg-black border border-violet-500/20 rounded-lg p-6 text-center space-y-3">
          <h2 className="text-lg font-semibold text-foreground">
            {t(I18nKey.SETTINGS$MCP_CONFIG_ERROR)}
          </h2>
          <p className="text-sm text-foreground-secondary">
            {t(I18nKey.SETTINGS$MCP_CONFIG_DESCRIPTION)}
          </p>
          <BrandButton
            variant="secondary"
            onClick={() => window.location.reload()}
            type="button"
            testId="reload-mcp-settings"
          >
            Refresh
          </BrandButton>
        </div>
      </div>
    );
  }

  const tabNavigation = (
    <TabNavigation
      activeTab={activeTab}
      totalServers={allServers.length}
      isLoading={isLoading}
      onChange={(tab) => handleTabChange({ tab, setActiveTab, setView })}
    />
  );

  const content = renderMcpContent({
    activeTab,
    view,
    allServers,
    isLoading,
    editingServer,
    t,
    handleEditClick,
    handleDeleteClick,
    handleAddServer,
    handleEditServer,
    setView,
    setEditingServer,
    installedServerNames,
    handleInstallFromMarketplace,
  });

  const confirmationModal = confirmationModalIsVisible ? (
    <ConfirmationModal
      text={t(I18nKey.SETTINGS$MCP_CONFIRM_DELETE)}
      onConfirm={handleConfirmDelete}
      onCancel={handleCancelDelete}
    />
  ) : null;

  return (
    <div className="px-11 py-9 flex flex-col gap-5">
      {tabNavigation}
      {content}
      {confirmationModal}
    </div>
  );
}

export default MCPSettingsScreen;

function buildServerList(mcpConfig: MCPConfig): MCPServerConfig[] {
  const sseServers = mcpConfig.sse_servers.map((server, index) => ({
    id: `sse-${index}`,
    type: "sse" as const,
    url: typeof server === "string" ? server : server.url,
    api_key: typeof server === "object" ? server.api_key : undefined,
  }));

  const stdioServers = mcpConfig.stdio_servers.map((server, index) => ({
    id: `stdio-${index}`,
    type: "stdio" as const,
    name: server.name,
    command: server.command,
    args: server.args,
    env: server.env,
  }));

  const shttpServers = mcpConfig.shttp_servers.map((server, index) => ({
    id: `shttp-${index}`,
    type: "shttp" as const,
    url: typeof server === "string" ? server : server.url,
    api_key: typeof server === "object" ? server.api_key : undefined,
  }));

  return [...sseServers, ...stdioServers, ...shttpServers];
}

export function confirmServerDeletion({
  serverToDelete,
  handleDeleteServer,
  setServerToDelete,
  onAfterDelete,
}: {
  serverToDelete: string | null;
  handleDeleteServer: (serverId: string) => void;
  setServerToDelete: React.Dispatch<React.SetStateAction<string | null>>;
  onAfterDelete?: () => void;
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
  onAfterDelete?.();
}

function handleTabChange({
  tab,
  setActiveTab,
  setView,
}: {
  tab: TabType;
  setActiveTab: React.Dispatch<React.SetStateAction<TabType>>;
  setView?: React.Dispatch<React.SetStateAction<"list" | "add" | "edit">>;
}) {
  setActiveTab(tab);
  if (tab === "my-servers" && setView) {
    setView("list");
  }
}

export function createTemplateInstaller({
  addMcpServer,
  setActiveTab,
}: {
  addMcpServer: ReturnType<typeof useAddMcpServer>["mutate"];
  setActiveTab: React.Dispatch<React.SetStateAction<TabType>>;
}) {
  return (mcp: MCPMarketplaceItem) => {
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
        displaySuccessToast("Template installed");
        setActiveTab("my-servers");
      },
      onError: (error) => {
        displayErrorToast(
          error instanceof Error ? error.message : "Failed to install template",
        );
      },
    });
  };
}

function McpSettingsSkeleton() {
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

function TabNavigation({
  activeTab,
  totalServers,
  isLoading,
  onChange,
}: {
  activeTab: TabType;
  totalServers: number;
  isLoading: boolean;
  onChange: (tab: TabType) => void;
}) {
  return (
    <div className="flex items-center gap-1 p-1 bg-black border border-violet-500/20 rounded-lg w-fit">
      <TabButton
        isActive={activeTab === "my-servers"}
        label="My Servers"
        icon={<Store className="w-4 h-4" />}
        badge={totalServers > 0 ? totalServers : undefined}
        onClick={() => {
          onChange("my-servers");
        }}
      />
      <TabButton
        isActive={activeTab === "marketplace"}
        label="Marketplace"
        icon={<ShoppingBag className="w-4 h-4" />}
        disabled={isLoading}
        onClick={() => onChange("marketplace")}
      />
    </div>
  );
}

function TabButton({
  isActive,
  label,
  icon,
  badge,
  onClick,
  disabled,
}: {
  isActive: boolean;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
        isActive
          ? "bg-brand-500 text-white shadow-sm"
          : "text-foreground-secondary hover:text-foreground hover:bg-black"
      } ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
    >
      {icon}
      {label}
      {typeof badge === "number" && (
        <span
          className={`px-1.5 py-0.5 text-xs rounded-full ${
            isActive
              ? "bg-white/20 text-white"
              : "bg-black text-foreground-secondary"
          }`}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

function renderMcpContent({
  activeTab,
  view,
  allServers,
  isLoading,
  editingServer,
  t,
  handleEditClick,
  handleDeleteClick,
  handleAddServer,
  handleEditServer,
  setView,
  setEditingServer,
  installedServerNames,
  handleInstallFromMarketplace,
}: {
  activeTab: TabType;
  view: "list" | "add" | "edit";
  allServers: MCPServerConfig[];
  isLoading: boolean;
  editingServer: MCPServerConfig | null;
  t: ReturnType<typeof useTranslation>["t"];
  handleEditClick: (server: MCPServerConfig) => void;
  handleDeleteClick: (serverId: string) => void;
  handleAddServer: (server: MCPServerConfig) => void;
  handleEditServer: (server: MCPServerConfig) => void;
  setView: React.Dispatch<React.SetStateAction<"list" | "add" | "edit">>;
  setEditingServer: React.Dispatch<
    React.SetStateAction<MCPServerConfig | null>
  >;
  installedServerNames: string[];
  handleInstallFromMarketplace: (mcp: MCPMarketplaceItem) => void;
}) {
  if (activeTab === "marketplace") {
    return (
      <MCPMarketplace
        installedServers={installedServerNames}
        onInstall={handleInstallFromMarketplace}
      />
    );
  }

  if (view === "add") {
    return (
      <MCPServerForm
        mode="add"
        existingServers={allServers}
        onSubmit={handleAddServer}
        onCancel={() => setView("list")}
      />
    );
  }

  if (view === "edit" && editingServer) {
    return (
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
    );
  }

  return (
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
  );
}
