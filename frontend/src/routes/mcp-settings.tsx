import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
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

type TabType = "my-servers" | "marketplace";

type MCPView = "list" | "add" | "edit";

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

interface MCPSettingsScreenProps {
  initialTab?: TabType;
}

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
  t,
}: {
  serverToDelete: string | null;
  handleDeleteServer: (serverId: string) => void;
  setServerToDelete: React.Dispatch<React.SetStateAction<string | null>>;
  onAfterDelete?: () => void;
  t: TFunction;
}) {
  if (!serverToDelete) {
    displayErrorToast(
      t(
        "mcpSettings.notifications.delete.noSelection",
        "No server selected for deletion.",
      ),
    );
    return;
  }

  if (!handleDeleteServer) {
    displayErrorToast(
      t(
        "mcpSettings.notifications.delete.unavailable",
        "Unable to delete server right now.",
      ),
    );
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
  setView?: React.Dispatch<React.SetStateAction<MCPView>>;
}) {
  setActiveTab(tab);
  if (tab === "my-servers" && setView) {
    setView("list");
  }
}

export function createTemplateInstaller({
  addMcpServer,
  setActiveTab,
  t,
}: {
  addMcpServer: ReturnType<typeof useAddMcpServer>["mutate"];
  setActiveTab: React.Dispatch<React.SetStateAction<TabType>>;
  t: TFunction;
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
        displaySuccessToast(
          t("mcpSettings.notifications.template.success", "Template installed"),
        );
        setActiveTab("my-servers");
      },
      onError: (error) => {
        displayErrorToast(
          error instanceof Error
            ? error.message
            : t(
                "mcpSettings.notifications.template.error",
                "Failed to install template",
              ),
        );
      },
    });
  };
}

function McpSettingsSkeleton() {
  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        <div className="animate-pulse">
          <div className="h-6 bg-black rounded w-1/4 mb-4" />
          <div className="h-4 bg-black rounded w-1/2 mb-8" />
          <div className="h-10 bg-black rounded w-32" />
        </div>
      </div>
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
  icon: ReactNode;
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
          ? "bg-white text-black shadow-sm"
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

function TabNavigation({
  activeTab,
  totalServers,
  isLoading,
  onChange,
  t,
}: {
  activeTab: TabType;
  totalServers: number;
  isLoading: boolean;
  onChange: (tab: TabType) => void;
  t: TFunction;
}) {
  return (
    <div className="flex items-center gap-1 p-1 bg-black/60 border border-white/10 rounded-xl w-fit">
      <TabButton
        isActive={activeTab === "my-servers"}
        label={t("mcpSettings.tabs.myServers", "My Servers")}
        icon={<Store className="w-4 h-4" />}
        badge={totalServers > 0 ? totalServers : undefined}
        onClick={() => {
          onChange("my-servers");
        }}
      />
      <TabButton
        isActive={activeTab === "marketplace"}
        label={t("mcpSettings.tabs.marketplace", "Marketplace")}
        icon={<ShoppingBag className="w-4 h-4" />}
        disabled={isLoading}
        onClick={() => onChange("marketplace")}
      />
    </div>
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
  view: MCPView;
  allServers: MCPServerConfig[];
  isLoading: boolean;
  editingServer: MCPServerConfig | null;
  t: TFunction;
  handleEditClick: (server: MCPServerConfig) => void;
  handleDeleteClick: (serverId: string) => void;
  handleAddServer: (server: MCPServerConfig) => void;
  handleEditServer: (server: MCPServerConfig) => void;
  setView: React.Dispatch<React.SetStateAction<MCPView>>;
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

function MCPSettingsScreen({
  initialTab = "my-servers",
}: MCPSettingsScreenProps = {}) {
  const { t } = useTranslation();
  const { data: settings, isLoading } = useSettings();
  const { mutate: deleteMcpServer } = useDeleteMcpServer();
  const { mutate: addMcpServer } = useAddMcpServer();
  const { mutate: updateMcpServer } = useUpdateMcpServer();

  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const [view, setView] = useState<MCPView>("list");
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

  const allServers = useMemo(() => buildServerList(mcpConfig), [mcpConfig]);

  const resolveErrorMessage = useCallback(
    (error: unknown, fallbackKey: string, fallbackDefault: string) =>
      error instanceof Error ? error.message : t(fallbackKey, fallbackDefault),
    [t],
  );

  const handleAddServer = (serverConfig: MCPServerConfig) => {
    addMcpServer(serverConfig, {
      onSuccess: () => {
        displaySuccessToast(
          t(
            "mcpSettings.notifications.create.success",
            "Server added successfully",
          ),
        );
        setView("list");
      },
      onError: (error) => {
        displayErrorToast(
          resolveErrorMessage(
            error,
            "mcpSettings.notifications.create.error",
            "Failed to add MCP server",
          ),
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
          displaySuccessToast(
            t(
              "mcpSettings.notifications.update.success",
              "Server updated successfully",
            ),
          );
          setView("list");
        },
        onError: (error) => {
          displayErrorToast(
            resolveErrorMessage(
              error,
              "mcpSettings.notifications.update.error",
              "Failed to update MCP server",
            ),
          );
        },
      },
    );
  };

  const handleDeleteServer = (serverId: string) => {
    deleteMcpServer(serverId, {
      onSuccess: () => {
        displaySuccessToast(
          t(
            "mcpSettings.notifications.delete.success",
            "Server deleted successfully",
          ),
        );
        setConfirmationModalIsVisible(false);
      },
      onError: (error) => {
        displayErrorToast(
          resolveErrorMessage(
            error,
            "mcpSettings.notifications.delete.error",
            "Failed to delete MCP server",
          ),
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
      onAfterDelete: () => setConfirmationModalIsVisible(false),
      t,
    });
  };

  const handleCancelDelete = () => {
    setConfirmationModalIsVisible(false);
    setServerToDelete(null);
  };

  const handleInstallFromMarketplace = useCallback(
    createTemplateInstaller({
      addMcpServer,
      setActiveTab,
      t,
    }),
    [addMcpServer, setActiveTab, t],
  );

  const installedServerNames = useMemo(
    () => allServers.map((server) => server.name || ""),
    [allServers],
  );

  if (isLoading) {
    return <McpSettingsSkeleton />;
  }

  if (!settings) {
    return (
      <div className="p-6 sm:p-8 lg:p-10">
        <div className="bg-black/60 border border-white/10 rounded-2xl p-6 text-center space-y-3">
          <h2 className="text-lg font-semibold text-foreground w-full">
            {t(I18nKey.SETTINGS$MCP_CONFIG_ERROR)}
          </h2>
          <p className="text-sm text-foreground-secondary w-full">
            {t(I18nKey.SETTINGS$MCP_CONFIG_DESCRIPTION)}
          </p>
          <BrandButton
            variant="secondary"
            onClick={() => window.location.reload()}
            type="button"
            testId="reload-mcp-settings"
          >
            {t("mcpSettings.actions.refresh", "Refresh")}
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
      t={t}
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
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        {tabNavigation}
        {content}
        {confirmationModal}
      </div>
    </div>
  );
}

export default MCPSettingsScreen;
