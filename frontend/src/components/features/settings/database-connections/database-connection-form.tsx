import { useMemo, useState, useCallback } from "react";
import { Database, TestTube, Eye, EyeOff, Loader2 } from "lucide-react";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import type { DatabaseType, TestConnectionRequest, TestConnectionResponse } from "#/types/database";
import { useTestDatabaseConnection } from "#/hooks/query/use-database-connections";
import { cn } from "#/utils/utils";

interface DatabaseConnectionFormProps {
  type: DatabaseType;
  onSubmit: (connection: any) => void;
  onCancel: () => void;
  existingConnection?: any;
}

type TestResult = (TestConnectionResponse & { details?: Record<string, any> }) | {
  success: boolean;
  message: string;
  details?: Record<string, any>;
};

type FormValues = {
  name: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
  connectionString: string;
};

const DATABASE_PLACEHOLDER: Record<DatabaseType, string> = {
  postgresql: "postgres",
  mongodb: "mydb",
  mysql: "mysql",
  redis: "0",
};

const USERNAME_PLACEHOLDER: Record<DatabaseType, string> = {
  postgresql: "postgres",
  mongodb: "user",
  mysql: "root",
  redis: "default",
};

export function DatabaseConnectionForm({
  type,
  onSubmit,
  onCancel,
  existingConnection,
}: DatabaseConnectionFormProps) {
  const {
    values,
    setValue,
    isMongoConnection,
    isRedisConnection,
    formIsValid,
    showPassword,
    toggleShowPassword,
    handleTest,
    handleSubmit,
    testResult,
    isTesting,
  } = useDatabaseConnectionFormState({ type, onSubmit, existingConnection });

  return (
    <div className="space-y-6 p-6 bg-background-secondary border border-border rounded-lg">
      <ConnectionHeader type={type} existingConnection={existingConnection} />
      <SecurityNoticeCard />

      <div className="space-y-4">
        <ConnectionNameInput value={values.name} onChange={(value) => setValue("name", value)} />
        {isMongoConnection ? (
          <MongoConnectionStringInput
            value={values.connectionString}
            onChange={(value) => setValue("connectionString", value)}
          />
        ) : null}
        <HostPortFields
          host={values.host}
          onHostChange={(value) => setValue("host", value)}
          port={values.port}
          onPortChange={(value) => setValue("port", value)}
          portPlaceholder={getDefaultPort(type).toString()}
        />
        {!isRedisConnection && (
          <DatabaseField
            database={values.database}
            onChange={(value) => setValue("database", value)}
            type={type}
            isMongoConnection={isMongoConnection}
          />
        )}
        {!isRedisConnection && (
          <UsernameField
            username={values.username}
            onChange={(value) => setValue("username", value)}
            type={type}
            isMongoConnection={isMongoConnection}
          />
        )}
        <PasswordField
          password={values.password}
          onChange={(value) => setValue("password", value)}
          showPassword={showPassword}
          onTogglePassword={toggleShowPassword}
        />
        <SslToggle ssl={values.ssl} onToggle={(value) => setValue("ssl", value)} />
      </div>

      <TestResultAlert testResult={testResult} />

      <FormActions
        existingConnection={existingConnection}
        onCancel={onCancel}
        onTest={handleTest}
        onSubmit={handleSubmit}
        isTesting={isTesting}
        formIsValid={formIsValid}
        testResult={testResult}
      />
    </div>
  );
}

function useDatabaseConnectionFormState({
  type,
  existingConnection,
  onSubmit,
}: {
  type: DatabaseType;
  existingConnection?: any;
  onSubmit: (connection: any) => void;
}) {
  const { mutateAsync: testConnection, isPending: isTesting } = useTestDatabaseConnection();

  const [values, setValues] = useState<FormValues>(() => ({
    name: existingConnection?.name ?? "",
    host: existingConnection?.host ?? "localhost",
    port: existingConnection?.port ?? getDefaultPort(type),
    database: existingConnection?.database ?? "",
    username: existingConnection?.username ?? "",
    password: existingConnection?.password ?? "",
    ssl: existingConnection?.ssl ?? false,
    connectionString: existingConnection?.connectionString ?? "",
  }));
  const [showPassword, setShowPassword] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  const isMongoConnection = type === "mongodb";
  const isRedisConnection = type === "redis";
  const formIsValid = Boolean(values.name && values.host && values.port);

  const setValue = useCallback(<K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const buildTestRequest = useCallback((): TestConnectionRequest => ({
    type,
    host: values.host,
    port: values.port,
    database: values.database || undefined,
    username: values.username || undefined,
    password: values.password || undefined,
    ssl: values.ssl,
    connectionString: values.connectionString || undefined,
  }), [type, values]);

  const submitPayload = useMemo(
    () => ({
      name: values.name,
      type,
      host: values.host,
      port: values.port,
      database: values.database || undefined,
      username: values.username || undefined,
      password: values.password || undefined,
      ssl: values.ssl,
      connectionString: type === "mongodb" ? values.connectionString : undefined,
    }),
    [type, values],
  );

  const handleTest = useCallback(async () => {
    setTestResult(null);

    try {
      const result = await testConnection(buildTestRequest());
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : "Test failed",
      });
    }
  }, [buildTestRequest, testConnection]);

  const handleSubmit = useCallback(() => {
    onSubmit(submitPayload);
  }, [onSubmit, submitPayload]);

  const toggleShowPassword = useCallback(() => {
    setShowPassword((prev) => !prev);
  }, []);

  return {
    values,
    setValue,
    isMongoConnection,
    isRedisConnection,
    formIsValid,
    showPassword,
    toggleShowPassword,
    handleTest,
    handleSubmit,
    testResult,
    isTesting,
  };
}

function ConnectionHeader({
  type,
  existingConnection,
}: {
  type: DatabaseType;
  existingConnection?: any;
}) {
  const title = existingConnection ? "Edit" : "Add";
  const formattedType = `${type.charAt(0).toUpperCase()}${type.slice(1)}`;

  return (
    <div className="flex items-center gap-3">
      <Database className="w-6 h-6 text-violet-500" />
      <h3 className="text-xl font-semibold text-foreground">
        {title} {formattedType} Connection
      </h3>
    </div>
  );
}

function SecurityNoticeCard() {
  return (
    <div className="p-4 bg-brand-500/10 border border-brand-500/30 rounded-lg">
      <h4 className="text-sm font-semibold text-violet-500 mb-2">🔒 Secure SaaS Deployment</h4>
      <p className="text-xs text-foreground-secondary mb-2">
        For maximum security, database connections execute in YOUR sandbox environment (not our servers).
        Credentials are stored as environment variables in YOUR environment only.
      </p>
      <p className="text-xs text-foreground-secondary">
        <strong>Recommended:</strong> Set credentials in <a href="/settings/secrets" className="text-violet-500 underline">Settings &gt; Secrets</a> as environment variables,
        then reference them in the agent's sandbox. This keeps your credentials private and secure.
      </p>
    </div>
  );
}

function ConnectionNameInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">Connection Name *</label>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="My Production Database"
        className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
      />
    </div>
  );
}

function MongoConnectionStringInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">
        Connection String
        <span className="text-foreground-secondary text-xs ml-2">(Optional - or use host/port below)</span>
      </label>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="mongodb://username:password@host:port/database"
        className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent font-mono text-sm"
      />
    </div>
  );
}

function HostPortFields({
  host,
  onHostChange,
  port,
  onPortChange,
  portPlaceholder,
}: {
  host: string;
  onHostChange: (value: string) => void;
  port: number;
  onPortChange: (value: number) => void;
  portPlaceholder: string;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">Host *</label>
        <input
          type="text"
          value={host}
          onChange={(event) => onHostChange(event.target.value)}
          placeholder="localhost"
          className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">Port *</label>
        <input
          type="number"
          value={port}
          onChange={(event) => onPortChange(parseInt(event.target.value, 10) || 0)}
          placeholder={portPlaceholder}
          className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
        />
      </div>
    </div>
  );
}

function DatabaseField({
  database,
  onChange,
  type,
  isMongoConnection,
}: {
  database: string;
  onChange: (value: string) => void;
  type: DatabaseType;
  isMongoConnection: boolean;
}) {
  const labelSuffix = isMongoConnection ? "" : "*";
  const placeholder = DATABASE_PLACEHOLDER[type];

  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">Database {labelSuffix}</label>
      <input
        type="text"
        value={database}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
      />
    </div>
  );
}

function UsernameField({
  username,
  onChange,
  type,
  isMongoConnection,
}: {
  username: string;
  onChange: (value: string) => void;
  type: DatabaseType;
  isMongoConnection: boolean;
}) {
  const labelSuffix = isMongoConnection ? "" : "*";
  const placeholder = USERNAME_PLACEHOLDER[type];

  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">Username {labelSuffix}</label>
      <input
        type="text"
        value={username}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
      />
    </div>
  );
}

function PasswordField({
  password,
  onChange,
  showPassword,
  onTogglePassword,
}: {
  password: string;
  onChange: (value: string) => void;
  showPassword: boolean;
  onTogglePassword: () => void;
}) {
  return (
    <div className="relative">
      <label className="block text-sm font-medium text-foreground mb-2">Password</label>
      <div className="relative">
        <input
          type={showPassword ? "text" : "password"}
          value={password}
          onChange={(event) => onChange(event.target.value)}
          placeholder="••••••••"
          className="w-full px-3 py-2 pr-10 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
        />
        <button
          type="button"
          onClick={onTogglePassword}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-secondary hover:text-foreground transition-colors"
        >
          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}

function SslToggle({
  ssl,
  onToggle,
}: {
  ssl: boolean;
  onToggle: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center gap-3 p-3 bg-background-tertiary border border-border rounded-md">
      <SettingsSwitch isToggled={ssl} onToggle={onToggle} testId="ssl-toggle">
        Use SSL/TLS
      </SettingsSwitch>
      <span className="text-sm text-foreground-secondary">Encrypt connection using SSL/TLS</span>
    </div>
  );
}

function TestResultAlert({ testResult }: { testResult: TestResult | null }) {
  if (!testResult) {
    return null;
  }

  const alertClass = testResult.success
    ? "bg-success-500/10 border-success-500 text-success-500"
    : "bg-error-500/10 border-error-500 text-error-500";

  return (
    <div className={cn("p-4 rounded-lg border", alertClass)}>
      <div className="flex items-start gap-2">
        <div className="flex-1">
          <p className="font-medium">{testResult.message}</p>
          {testResult.details?.version ? (
            <p className="text-sm opacity-80 mt-1">Version: {testResult.details.version}</p>
          ) : null}
          {testResult.details?.note ? (
            <p className="text-xs opacity-70 mt-1">{testResult.details.note}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function FormActions({
  existingConnection,
  onCancel,
  onTest,
  onSubmit,
  isTesting,
  formIsValid,
  testResult,
}: {
  existingConnection?: any;
  onCancel: () => void;
  onTest: () => void;
  onSubmit: () => void;
  isTesting: boolean;
  formIsValid: boolean;
  testResult: TestResult | null;
}) {
  const isSaveDisabled = !formIsValid || (testResult && !testResult.success);

  return (
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
        onClick={onTest}
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
        onClick={onSubmit}
        isDisabled={isSaveDisabled}
        type="button"
        testId="save-db-connection"
      >
        {existingConnection ? "Update" : "Save"} Connection
      </BrandButton>
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

