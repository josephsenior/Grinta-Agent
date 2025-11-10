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
  const controller = useMcpServerFormController({
    mode,
    server,
    existingServers,
    onSubmit,
    onCancel,
  });
  const {
    t,
    serverType,
    setServerType,
    error,
    serverTypeOptions,
    formatEnvironmentVariables,
    handleSubmit,
  } = controller;

  return (
    <form
      data-testid="mcp-server-form"
      onSubmit={handleSubmit}
      className="flex flex-col items-start gap-6"
    >
      {mode === "add" && (
        <SettingsDropdownInput
          testId="server-type-input"
          name="type"
          defaultSelectedKey={serverType}
          onSelectionChange={(value) => setServerType(value as MCPServerType)}
          items={serverTypeOptions}
        />
      )}

      {error && (
        <div className="text-danger text-sm" data-testid="form-error">
          {error}
        </div>
      )}

      <ServerSpecificFields
        serverType={serverType}
        server={server}
        formatEnvironmentVariables={formatEnvironmentVariables}
        t={controller.t}
      />

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

function ServerSpecificFields({
  serverType,
  server,
  formatEnvironmentVariables,
  t,
}: {
  serverType: MCPServerType;
  server?: MCPServerConfig;
  formatEnvironmentVariables: (env?: Record<string, string>) => string;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (serverType === "stdio") {
    return (
      <>
        <SettingsInput
          testId="name-input"
          name="name"
          label={t(I18nKey.SETTINGS$MCP_SERVER_TYPE)}
          type="text"
          defaultValue={server?.name}
          placeholder="my-stdio-server"
          className={cn(
            "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl px-3 py-2 placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
            "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
          )}
          required
        />

        <SettingsInput
          testId="command-input"
          name="command"
          label={t(I18nKey.SETTINGS$MCP_COMMAND)}
          type="text"
          defaultValue={server?.command}
          placeholder="python"
          className={cn(
            "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl px-3 py-2 placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
            "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
          )}
          required
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
            rows={4}
            defaultValue={server?.args?.join("\n")}
            placeholder="--option value"
            className={cn(
              "resize-none",
              "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl p-3 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
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
    );
  }

  return (
    <>
      <SettingsInput
        testId="url-input"
        name="url"
        label={t(I18nKey.SETTINGS$MCP_URL)}
        type="url"
        defaultValue={server?.url}
        placeholder="https://your-mcp-server.com"
        className={cn(
          "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl px-3 py-2 placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
          "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
        )}
        required
      />

      <SettingsInput
        testId="api-key-input"
        name="api_key"
        label={t(I18nKey.SETTINGS$MCP_API_KEY)}
        showOptionalTag
        type="password"
        defaultValue={server?.api_key}
        placeholder={t(I18nKey.SETTINGS$MCP_API_KEY_PLACEHOLDER)}
        className={cn(
          "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl px-3 py-2 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
          "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
        )}
      />
    </>
  );
}

function createValidatorHelpers({
  t,
  mode,
  server,
  existingServers,
}: {
  t: ReturnType<typeof useTranslation>["t"];
  mode: MCPServerFormProps["mode"];
  server?: MCPServerConfig;
  existingServers?: MCPServerConfig[];
}) {
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

  const validateUrlUniqueness = (url: string): string | null => {
    if (!existingServers) {
      return null;
    }
    const originalUrl = server?.url;
    const changed = mode === "add" || (mode === "edit" && originalUrl !== url);
    if (!changed) {
      return null;
    }
    const exists = existingServers.some(
      (s) => (s.type === "sse" || s.type === "shttp") && s.url === url,
    );
    if (exists) {
      return t(I18nKey.SETTINGS$MCP_ERROR_URL_DUPLICATE);
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

    const envError = validateEnvFormat(envString);
    if (envError) {
      return envError;
    }

    return null;
  };

  const validateUrlServer = (formData: FormData): string | null => {
    const url = formData.get("url")?.toString().trim() || "";
    const urlError = validateUrl(url);
    if (urlError) {
      return urlError;
    }
    return validateUrlUniqueness(url);
  };

  const validators: Record<
    MCPServerType,
    (formData: FormData) => string | null
  > = {
    sse: validateUrlServer,
    shttp: validateUrlServer,
    stdio: validateStdioServer,
  };

  const validateForm = (serverType: MCPServerType, formData: FormData) =>
    validators[serverType]?.(formData) ?? null;

  return {
    validateForm,
  };
}

function buildServerPayload({
  formData,
  serverType,
  baseConfig,
  parseEnvironmentVariables,
}: {
  formData: FormData;
  serverType: MCPServerType;
  baseConfig: { id: string; type: MCPServerType };
  parseEnvironmentVariables: (envString: string) => Record<string, string>;
}): MCPServerConfig {
  const builder = SERVER_PAYLOAD_BUILDERS[serverType];
  return builder({ formData, baseConfig, parseEnvironmentVariables });
}

const SERVER_PAYLOAD_BUILDERS: Record<
  MCPServerType,
  ({
    formData,
    baseConfig,
    parseEnvironmentVariables,
  }: {
    formData: FormData;
    baseConfig: { id: string; type: MCPServerType };
    parseEnvironmentVariables: (envString: string) => Record<string, string>;
  }) => MCPServerConfig
> = {
  stdio: ({ formData, baseConfig, parseEnvironmentVariables }) => {
    const name = formData.get("name")?.toString().trim() || "";
    const command = formData.get("command")?.toString().trim() || "";
    const args = extractArgs(formData.get("args"));
    const envString = formData.get("env")?.toString() || "";

    return {
      ...baseConfig,
      name,
      command,
      args,
      env: parseEnvironmentVariables(envString),
    };
  },
  sse: ({ formData, baseConfig }) =>
    buildUrlServerPayload({ formData, baseConfig }),
  shttp: ({ formData, baseConfig }) =>
    buildUrlServerPayload({ formData, baseConfig }),
};

function extractArgs(value: FormDataEntryValue | null): string[] {
  const raw = value?.toString().trim() || "";
  if (!raw) {
    return [];
  }
  return raw
    .split("\n")
    .map((arg) => arg.trim())
    .filter(Boolean);
}

function buildUrlServerPayload({
  formData,
  baseConfig,
}: {
  formData: FormData;
  baseConfig: { id: string; type: MCPServerType };
}): MCPServerConfig {
  const url = formData.get("url")?.toString().trim() || "";
  const apiKey = formData.get("api_key")?.toString().trim();

  return {
    ...baseConfig,
    url,
    ...(apiKey && { api_key: apiKey }),
  };
}

function useMcpServerFormController({
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
  const [clientId, setClientId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (mode === "add" && !server?.id && !clientId) {
      setClientId(`${serverType}-${Math.floor(Math.random() * 1e9)}`);
    }
  }, [mode, server?.id, serverType, clientId]);

  const validators = React.useMemo(
    () =>
      createValidatorHelpers({
        t,
        mode,
        server,
        existingServers,
      }),
    [t, mode, server, existingServers],
  );

  const serverTypeOptions = React.useMemo(
    () => [
      { key: "sse", label: t(I18nKey.SETTINGS$MCP_SERVER_TYPE_SSE) },
      { key: "stdio", label: t(I18nKey.SETTINGS$MCP_SERVER_TYPE_STDIO) },
      { key: "shttp", label: t(I18nKey.SETTINGS$MCP_SERVER_TYPE_SHTTP) },
    ],
    [t],
  );

  const parseEnvironmentVariables = React.useCallback(
    (envString: string): Record<string, string> => {
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
    },
    [],
  );

  const formatEnvironmentVariables = React.useCallback(
    (env?: Record<string, string>): string => {
      if (!env) {
        return "";
      }
      return Object.entries(env)
        .map(([key, value]) => `${key}=${value}`)
        .join("\n");
    },
    [],
  );

  const handleSubmit = React.useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError(null);

      const formData = new FormData(event.currentTarget);
      const validationError = validators.validateForm(serverType, formData);

      if (validationError) {
        setError(validationError);
        return;
      }

      const baseConfig = {
        id: server?.id || clientId || `${serverType}-client`,
        type: serverType,
      } as { id: string; type: MCPServerType };

      const payload = buildServerPayload({
        formData,
        serverType,
        baseConfig,
        parseEnvironmentVariables,
      });

      onSubmit(payload);
    },
    [
      validators,
      serverType,
      server?.id,
      clientId,
      parseEnvironmentVariables,
      onSubmit,
    ],
  );

  return {
    t,
    serverType,
    setServerType,
    error,
    setError,
    serverTypeOptions,
    formatEnvironmentVariables,
    handleSubmit,
  } as const;
}
