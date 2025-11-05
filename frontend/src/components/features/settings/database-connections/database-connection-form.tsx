import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Database, TestTube, Eye, EyeOff, Loader2 } from "lucide-react";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import type { DatabaseType, TestConnectionRequest } from "#/types/database";
import { useTestDatabaseConnection } from "#/hooks/query/use-database-connections";

interface DatabaseConnectionFormProps {
  type: DatabaseType;
  onSubmit: (connection: any) => void;
  onCancel: () => void;
  existingConnection?: any;
}

export function DatabaseConnectionForm({
  type,
  onSubmit,
  onCancel,
  existingConnection,
}: DatabaseConnectionFormProps) {
  const { t } = useTranslation();
  const { mutateAsync: testConnection, isPending: isTesting } =
    useTestDatabaseConnection();

  const [name, setName] = useState(existingConnection?.name || "");
  const [host, setHost] = useState(
    existingConnection?.host || "localhost",
  );
  const [port, setPort] = useState(
    existingConnection?.port || getDefaultPort(type),
  );
  const [database, setDatabase] = useState(existingConnection?.database || "");
  const [username, setUsername] = useState(existingConnection?.username || "");
  const [password, setPassword] = useState(existingConnection?.password || "");
  const [showPassword, setShowPassword] = useState(false);
  const [ssl, setSsl] = useState(existingConnection?.ssl || false);
  const [connectionString, setConnectionString] = useState(
    existingConnection?.connectionString || "",
  );
  const [testResult, setTestResult] = useState<any>(null);

  const handleTest = async () => {
    setTestResult(null);

    const testRequest: TestConnectionRequest = {
      type,
      host,
      port,
      database: database || undefined,
      username: username || undefined,
      password: password || undefined,
      ssl,
      connectionString: connectionString || undefined,
    };

    try {
      const result = await testConnection(testRequest);
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : "Test failed",
      });
    }
  };

  const handleSubmit = () => {
    const connection = {
      name,
      type,
      host,
      port,
      database: database || undefined,
      username: username || undefined,
      password: password || undefined,
      ssl,
      connectionString: type === "mongodb" ? connectionString : undefined,
    };

    onSubmit(connection);
  };

  const isMongoConnection = type === "mongodb";
  const formIsValid = name && host && port;

  return (
    <div className="space-y-6 p-6 bg-background-secondary border border-border rounded-lg">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Database className="w-6 h-6 text-violet-500" />
        <h3 className="text-xl font-semibold text-foreground">
          {existingConnection ? "Edit" : "Add"}{" "}
          {type.charAt(0).toUpperCase() + type.slice(1)} Connection
        </h3>
      </div>

      {/* Security Notice for SaaS */}
      <div className="p-4 bg-brand-500/10 border border-brand-500/30 rounded-lg">
        <h4 className="text-sm font-semibold text-violet-500 mb-2">
          🔒 Secure SaaS Deployment
        </h4>
        <p className="text-xs text-foreground-secondary mb-2">
          For maximum security, database connections execute in YOUR sandbox environment (not our servers).
          Credentials are stored as environment variables in YOUR environment only.
        </p>
        <p className="text-xs text-foreground-secondary">
          <strong>Recommended:</strong> Set credentials in <a href="/settings/secrets" className="text-violet-500 underline">Settings &gt; Secrets</a> as environment variables,
          then reference them in the agent's sandbox. This keeps your credentials private and secure.
        </p>
      </div>

      <div className="space-y-4">
        {/* Connection Name */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Connection Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Production Database"
            className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>

        {/* MongoDB Connection String (alternative input) */}
        {isMongoConnection && (
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Connection String
              <span className="text-foreground-secondary text-xs ml-2">
                (Optional - or use host/port below)
              </span>
            </label>
            <input
              type="text"
              value={connectionString}
              onChange={(e) => setConnectionString(e.target.value)}
              placeholder="mongodb://username:password@host:port/database"
              className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent font-mono text-sm"
            />
          </div>
        )}

        {/* Host and Port */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Host *
            </label>
            <input
              type="text"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="localhost"
              className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Port *
            </label>
            <input
              type="number"
              value={port}
              onChange={(e) => setPort(parseInt(e.target.value) || 0)}
              placeholder={getDefaultPort(type).toString()}
              className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Database Name (not for Redis) */}
        {type !== "redis" && (
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Database {type === "mongodb" ? "" : "*"}
            </label>
            <input
              type="text"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              placeholder={
                type === "postgresql"
                  ? "postgres"
                  : type === "mysql"
                    ? "mysql"
                    : "mydb"
              }
              className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>
        )}

        {/* Username */}
        {type !== "redis" && (
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Username {isMongoConnection ? "" : "*"}
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={
                type === "postgresql"
                  ? "postgres"
                  : type === "mysql"
                    ? "root"
                    : "user"
              }
              className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>
        )}

        {/* Password */}
        <div className="relative">
          <label className="block text-sm font-medium text-foreground mb-2">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2 pr-10 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-secondary hover:text-foreground transition-colors"
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* SSL/TLS Toggle */}
        <div className="flex items-center gap-3 p-3 bg-background-tertiary border border-border rounded-md">
          <SettingsSwitch
            isToggled={ssl}
            onToggle={setSsl}
            testId="ssl-toggle"
          >
            Use SSL/TLS
          </SettingsSwitch>
          <span className="text-sm text-foreground-secondary">
            Encrypt connection using SSL/TLS
          </span>
        </div>
      </div>

      {/* Test Result */}
      {testResult && (
        <div
          className={`p-4 rounded-lg border ${
            testResult.success
              ? "bg-success-500/10 border-success-500 text-success-500"
              : "bg-error-500/10 border-error-500 text-error-500"
          }`}
        >
          <div className="flex items-start gap-2">
            <div className="flex-1">
              <p className="font-medium">{testResult.message}</p>
              {testResult.details?.version && (
                <p className="text-sm opacity-80 mt-1">
                  Version: {testResult.details.version}
                </p>
              )}
              {testResult.details?.note && (
                <p className="text-xs opacity-70 mt-1">
                  {testResult.details.note}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 justify-end pt-4 border-t border-border">
        <BrandButton
          variant="secondary"
          onClick={onCancel}
          type="button"
          testId="cancel-db-connection"
        >
          Cancel
        </BrandButton>
        <BrandButton
          variant="secondary"
          onClick={handleTest}
          isDisabled={isTesting || !formIsValid}
          type="button"
          testId="test-db-connection"
          className="flex items-center gap-2"
        >
          {isTesting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Testing...
            </>
          ) : (
            <>
              <TestTube className="w-4 h-4" />
              Test Connection
            </>
          )}
        </BrandButton>
        <BrandButton
          variant="primary"
          onClick={handleSubmit}
          isDisabled={!formIsValid || (testResult && !testResult.success)}
          type="button"
          testId="save-db-connection"
        >
          {existingConnection ? "Update" : "Save"} Connection
        </BrandButton>
      </div>
    </div>
  );
}

function getDefaultPort(type: DatabaseType): number {
  switch (type) {
    case "postgresql":
      return 5432;
    case "mongodb":
      return 27017;
    case "mysql":
      return 3306;
    case "redis":
      return 6379;
    default:
      return 5432;
  }
}

