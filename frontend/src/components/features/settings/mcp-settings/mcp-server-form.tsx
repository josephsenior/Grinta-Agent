import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { SettingsInput } from "../settings-input";
import { SettingsDropdownInput } from "../settings-dropdown-input";
import { BrandButton } from "../brand-button";
import { OptionalTag } from "../optional-tag";
import { cn } from "#/utils/utils";

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

interface MCPServerFormProps {
  mode: "add" | "edit";
  server?: MCPServerConfig;
  existingServers?: MCPServerConfig[];
  onSubmit: (server: MCPServerConfig) => void;
  onCancel: () => void;
}

export function MCPServerForm({
  mode,
  server,
  existingServers,
  onSubmit,
  onCancel,
}: MCPServerFormProps) {
  const { t } = useTranslation();
  const [serverType, setServerType] = React.useState<MCPServerType>(
    server?.type || "sse",
  );
  const [error, setError] = React.useState<string | null>(null);

  const serverTypeOptions = [
    { key: "sse", label: t(I18nKey.SETTINGS$MCP_SERVER_TYPE_SSE) },
    { key: "stdio", label: t(I18nKey.SETTINGS$MCP_SERVER_TYPE_STDIO) },
    { key: "shttp", label: t(I18nKey.SETTINGS$MCP_SERVER_TYPE_SHTTP) },
  ];

  const validateUrl = (url: string): string | null => {
    if (!url) {
      return t(I18nKey.SETTINGS$MCP_ERROR_URL_REQUIRED);
    }
    try {
      const urlObj = new URL(url);
      if (!["http:", "https:"].includes(urlObj.protocol)) {
        return t(I18nKey.SETTINGS$MCP_ERROR_URL_INVALID_PROTOCOL);
      }
    } catch {
      return t(I18nKey.SETTINGS$MCP_ERROR_URL_INVALID);
    }
    return null;
  };

  const validateName = (name: string): string | null => {
    if (!name) {
      return t(I18nKey.SETTINGS$MCP_ERROR_NAME_REQUIRED);
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      return t(I18nKey.SETTINGS$MCP_ERROR_NAME_INVALID);
    }
    return null;
  };

  const validateNameUniqueness = (name: string): string | null => {
    if (!existingServers) {
      return null;
    }
    const shouldCheckUniqueness =
      mode === "add" || (mode === "edit" && server?.name !== name);
    if (!shouldCheckUniqueness) {
      return null;
    }

    const existingStdioNames = existingServers
      .filter((s) => s.type === "stdio")
      .map((s) => s.name)
      .filter(Boolean);
    if (existingStdioNames.includes(name)) {
      return t(I18nKey.SETTINGS$MCP_ERROR_NAME_DUPLICATE);
    }
    return null;
  };

  const validateCommand = (command: string): string | null => {
    if (!command) {
      return t(I18nKey.SETTINGS$MCP_ERROR_COMMAND_REQUIRED);
    }
    if (command.includes(" ")) {
      return t(I18nKey.SETTINGS$MCP_ERROR_COMMAND_NO_SPACES);
    }
    return null;
  };

  const validateUrlUniqueness = (url: string): string | null => {
    if (!existingServers) {
      return null;
    }
    const originalUrl = server?.url;
    const changed = mode === "add" || (mode === "edit" && originalUrl !== url);
    if (!changed) {
      return null;
    }
    // For URL-based servers (sse/shttp), ensure URL is unique across both types
    const exists = existingServers.some(
      (s) => (s.type === "sse" || s.type === "shttp") && s.url === url,
    );
    if (exists) {
      return t(I18nKey.SETTINGS$MCP_ERROR_URL_DUPLICATE);
    }
    return null;
  };

  const validateEnvFormat = (envString: string): string | null => {
    if (!envString.trim()) {
      return null;
    }
    const lines = envString.split("\n");
    for (let i = 0; i < lines.length; i += 1) {
      const trimmed = lines[i].trim();
      if (trimmed) {
        const eq = trimmed.indexOf("=");
        if (eq === -1) {
          return t(I18nKey.SETTINGS$MCP_ERROR_ENV_INVALID_FORMAT);
        }
        const key = trimmed.substring(0, eq).trim();
        if (!key) {
          return t(I18nKey.SETTINGS$MCP_ERROR_ENV_INVALID_FORMAT);
        }
      }
    }
    return null;
  };

  const validateStdioServer = (formData: FormData): string | null => {
    const name = formData.get("name")?.toString().trim() || "";
    const command = formData.get("command")?.toString().trim() || "";
    const envString = formData.get("env")?.toString() || "";

    const nameError = validateName(name);
    if (nameError) {
      return nameError;
    }

    const uniquenessError = validateNameUniqueness(name);
    if (uniquenessError) {
      return uniquenessError;
    }

    const commandError = validateCommand(command);
    if (commandError) {
      return commandError;
    }

    // Validate environment variable format
    const envError = validateEnvFormat(envString);
    if (envError) {
      return envError;
    }

    return null;
  };

  const validateForm = (formData: FormData): string | null => {
    if (serverType === "sse" || serverType === "shttp") {
      const url = formData.get("url")?.toString().trim() || "";
      const urlError = validateUrl(url);
      if (urlError) {
        return urlError;
      }
      const urlDupError = validateUrlUniqueness(url);
      if (urlDupError) {
        return urlDupError;
      }
      return null;
    }

    if (serverType === "stdio") {
      return validateStdioServer(formData);
    }

    return null;
  };

  const parseEnvironmentVariables = (
    envString: string,
  ): Record<string, string> => {
    const env: Record<string, string> = {};
    const input = envString.trim();
    if (!input) {
      return env;
    }

    for (const line of input.split("\n")) {
      const trimmed = line.trim();
      const eq = trimmed.indexOf("=");
      const key = eq >= 0 ? trimmed.substring(0, eq).trim() : "";
      if (trimmed && eq !== -1 && key) {
        env[key] = trimmed.substring(eq + 1).trim();
      }
    }
    return env;
  };

  const formatEnvironmentVariables = (env?: Record<string, string>): string => {
    if (!env) {
      return "";
    }
    return Object.entries(env)
      .map(([key, value]) => `${key}=${value}`)
      .join("\n");
  };

  // Generate a client-only id after mount when in add mode and no server id provided.
  const [clientId, setClientId] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (mode === "add" && !server?.id) {
      // Keep deterministic across renders by only generating on client after mount.
      setClientId(`${serverType}-${Math.floor(Math.random() * 1e9)}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const formData = new FormData(event.currentTarget);
    const validationError = validateForm(formData);

    if (validationError) {
      setError(validationError);
      return;
    }

    // Use client-generated id if adding a new server to avoid SSR/client mismatches.
    const baseConfig = {
      id: server?.id || clientId || `${serverType}-client`,
      type: serverType,
    } as { id: string; type: MCPServerType };

    if (serverType === "sse" || serverType === "shttp") {
      const url = formData.get("url")?.toString().trim();
      const apiKey = formData.get("api_key")?.toString().trim();

      onSubmit({
        ...baseConfig,
        url: url!,
        ...(apiKey && { api_key: apiKey }),
      });
    } else if (serverType === "stdio") {
      const name = formData.get("name")?.toString().trim();
      const command = formData.get("command")?.toString().trim();
      const argsString = formData.get("args")?.toString().trim();
      const envString = formData.get("env")?.toString().trim();

      const args = argsString
        ? argsString
            .split("\n")
            .map((arg) => arg.trim())
            .filter(Boolean)
        : [];
      const env = parseEnvironmentVariables(envString || "");

      onSubmit({
        ...baseConfig,
        name: name!,
        command: command!,
        ...(args.length > 0 && { args }),
        ...(Object.keys(env).length > 0 && { env }),
      });
    }
  };

  const formTestId =
    mode === "add" ? "add-mcp-server-form" : "edit-mcp-server-form";

  return (
    <form
      data-testid={formTestId}
      onSubmit={handleSubmit}
      className="flex flex-col items-start gap-6"
    >
      {mode === "add" && (
        <SettingsDropdownInput
          testId="server-type-dropdown"
          name="server-type"
          label={t(I18nKey.SETTINGS$MCP_SERVER_TYPE)}
          items={serverTypeOptions}
          selectedKey={serverType}
          onSelectionChange={(key) => setServerType(key as MCPServerType)}
          onInputChange={() => {}} // Prevent input changes
          isClearable={false}
          allowsCustomValue={false}
          required
          wrapperClassName={cn(
            "w-full",
            "sm:max-w-xs md:max-w-sm lg:max-w-[680px]",
          )}
        />
      )}

      {error && <p className="text-error-500 text-sm">{error}</p>}

      {(serverType === "sse" || serverType === "shttp") && (
        <>
          <SettingsInput
            testId="url-input"
            name="url"
            type="url"
            label={t(I18nKey.SETTINGS$MCP_URL)}
            className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
            required
            defaultValue={server?.url || ""}
            placeholder="https://api.example.com"
          />

          <SettingsInput
            testId="api-key-input"
            name="api_key"
            type="password"
            label={t(I18nKey.SETTINGS$MCP_API_KEY)}
            className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
            showOptionalTag
            defaultValue={server?.api_key || ""}
            placeholder={t(I18nKey.SETTINGS$MCP_API_KEY_PLACEHOLDER)}
          />
        </>
      )}

      {serverType === "stdio" && (
        <>
          <SettingsInput
            testId="name-input"
            name="name"
            type="text"
            label={t(I18nKey.SETTINGS$MCP_NAME)}
            className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
            required
            defaultValue={server?.name || ""}
            placeholder="my-mcp-server"
            pattern="^[a-zA-Z0-9_-]+$"
          />

          <SettingsInput
            testId="command-input"
            name="command"
            type="text"
            label={t(I18nKey.SETTINGS$MCP_COMMAND)}
            className="w-full max-w-[680px]"
            required
            defaultValue={server?.command || ""}
            placeholder="npx"
          />

          <label className="flex flex-col gap-2.5 w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]">
            <div className="flex items-center gap-2">
              <span className="text-sm">
                {t(I18nKey.SETTINGS$MCP_COMMAND_ARGUMENTS)}
              </span>
              <OptionalTag />
            </div>
            <textarea
              data-testid="args-input"
              name="args"
              rows={3}
              defaultValue={server?.args?.join("\n") || ""}
              placeholder="arg1&#10;arg2&#10;arg3"
              className={cn(
                "bg-background-glass backdrop-blur-xl border border-border-glass w-full rounded-xl p-3 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary resize-none transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
                "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
              )}
            />
            <p className="text-xs text-foreground-secondary-alt">
              {t(I18nKey.SETTINGS$MCP_COMMAND_ARGUMENTS_HELP)}
            </p>
          </label>

          <label className="flex flex-col gap-2.5 w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]">
            <div className="flex items-center gap-2">
              <span className="text-sm">
                {t(I18nKey.SETTINGS$MCP_ENVIRONMENT_VARIABLES)}
              </span>
              <OptionalTag />
            </div>
            <textarea
              data-testid="env-input"
              name="env"
              rows={4}
              defaultValue={formatEnvironmentVariables(server?.env)}
              placeholder="KEY1=value1&#10;KEY2=value2"
              className={cn(
                "resize-none",
                "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl p-3 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
                "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
              )}
            />
          </label>
        </>
      )}

      <div className="flex items-center gap-4">
        <BrandButton
          testId="cancel-button"
          type="button"
          variant="secondary"
          onClick={onCancel}
        >
          {t(I18nKey.BUTTON$CANCEL)}
        </BrandButton>
        <BrandButton testId="submit-button" type="submit" variant="primary">
          {mode === "add" && t(I18nKey.SETTINGS$MCP_ADD_SERVER)}
          {mode === "edit" && t(I18nKey.SETTINGS$MCP_SAVE_SERVER)}
        </BrandButton>
      </div>
    </form>
  );
}
