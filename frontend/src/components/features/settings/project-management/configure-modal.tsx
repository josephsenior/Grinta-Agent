import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Trans, useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import axios from "axios";
import { I18nKey } from "#/i18n/declaration";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import {
  BaseModalDescription,
  BaseModalTitle,
} from "#/components/shared/modals/confirmation-modals/base-modal";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { useValidateIntegration } from "#/hooks/mutation/use-validate-integration";

interface ConfigureButtonProps {
  onClick: () => void;
  isDisabled: boolean;
  text?: string;
  "data-testid"?: string;
}

export function ConfigureButton({
  onClick,
  isDisabled,
  text,
  "data-testid": dataTestId,
}: ConfigureButtonProps) {
  const { t } = useTranslation();
  return (
    <BrandButton
      data-testid={dataTestId}
      variant="primary"
      onClick={onClick}
      isDisabled={isDisabled}
      type="button"
      className="w-30 min-w-20"
    >
      {t(I18nKey.PROJECT_MANAGEMENT$CONFIGURE_BUTTON_LABEL, {
        defaultValue: `${text}`,
      })}
    </BrandButton>
  );
}

interface ConfigureModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (data: {
    workspace: string;
    webhookSecret: string;
    serviceAccountEmail: string;
    serviceAccountApiKey: string;
    isActive: boolean;
  }) => void;
  onLink: (workspace: string) => void;
  onUnlink?: () => void;
  platformName: string;
  platform: "jira" | "jira-dc" | "linear";
  integrationData?: {
    id: number;
    keycloak_user_id: string;
    status: string;
    workspace?: {
      id: number;
      name: string;
      status: string;
      editable: boolean;
    };
  } | null;
}

export function ConfigureModal({
  isOpen,
  onClose,
  onConfirm,
  onLink,
  onUnlink,
  platformName,
  platform,
  integrationData,
}: ConfigureModalProps) {
  const { t } = useTranslation();
  const existingWorkspace = integrationData?.workspace ?? null;

  const state = useConfigureModalState({
    isOpen,
    existingWorkspace,
    platform,
    onClose,
    onConfirm,
    onLink,
    t,
  });

  if (!isOpen) {
    return null;
  }

  const workspacePlaceholder = t(state.workspacePlaceholderKey);
  const workspaceLabel = t(I18nKey.PROJECT_MANAGEMENT$WORKSPACE_NAME_LABEL);
  const connectLabel = getConnectButtonLabel({
    existingWorkspace,
    showConfigurationFields: state.showConfigurationFields,
    t,
  });
  const cancelLabel = t(I18nKey.FEEDBACK$CANCEL_LABEL);
  const unlinkLabel = t(I18nKey.PROJECT_MANAGEMENT$UNLINK_BUTTON_LABEL);
  const modalTitle = state.showConfigurationFields
    ? t(I18nKey.PROJECT_MANAGEMENT$CONFIGURE_MODAL_TITLE, {
        platform: platformName,
      })
    : t(I18nKey.PROJECT_MANAGEMENT$LINK_CONFIRMATION_TITLE);
  const descriptionVariant: "link" | "configure" = state.showConfigurationFields
    ? "configure"
    : "link";
  const configurationLabels = buildConfigurationLabels(t);

  return (
    <ModalBackdrop onClose={state.handleClose}>
      <ModalBody className="items-start border border-border w-96">
        <BaseModalTitle title={modalTitle} />
        <BaseModalDescription>
          <ConfigureModalDescription
            variant={descriptionVariant}
            platformName={platformName}
          />
          <p className="mt-4">
            {t(I18nKey.PROJECT_MANAGEMENT$WORKSPACE_NAME_HINT, {
              platform: platformName,
            })}
          </p>
        </BaseModalDescription>
        <div className="w-full flex flex-col gap-4 mt-1">
          <WorkspaceSection
            value={state.workspace}
            onChange={state.handleWorkspaceChange}
            error={state.workspaceError}
            label={workspaceLabel}
            placeholder={workspacePlaceholder}
            existingWorkspace={existingWorkspace}
            onUnlink={onUnlink}
            unlinkLabel={unlinkLabel}
          />

          {state.showConfigurationFields && (
            <ConfigurationFieldsSection
              values={state.configurationFields}
              errors={state.configurationErrors}
              onChange={state.configurationHandlers}
              onToggleActive={state.handleActiveToggle}
              isActive={state.isActive}
              labels={configurationLabels}
            />
          )}
        </div>
        <ModalActions
          showConnectButton={!existingWorkspace || state.isWorkspaceEditable}
          onConnect={state.handleConnect}
          onCancel={state.handleClose}
          connectLabel={connectLabel}
          cancelLabel={cancelLabel}
          isConnectDisabled={state.isConnectDisabled}
        />
      </ModalBody>
    </ModalBackdrop>
  );
}

interface ConfigureModalStateOptions {
  isOpen: boolean;
  existingWorkspace: {
    id: number;
    name: string;
    status: string;
    editable: boolean;
  } | null;
  platform: "jira" | "jira-dc" | "linear";
  onClose: () => void;
  onConfirm: ConfigureModalProps["onConfirm"];
  onLink: ConfigureModalProps["onLink"];
  t: TFunction;
}

type ConfigureModalStateReturn = {
  workspace: string;
  workspaceError: string | null;
  handleWorkspaceChange: (value: string) => void;
  showConfigurationFields: boolean;
  isWorkspaceEditable: boolean;
  configurationFields: {
    webhookSecret: string;
    serviceAccountEmail: string;
    serviceAccountApiKey: string;
  };
  configurationErrors: {
    webhookSecret: string | null;
    serviceAccountEmail: string | null;
    serviceAccountApiKey: string | null;
  };
  configurationHandlers: {
    onWebhookSecretChange: (value: string) => void;
    onServiceAccountEmailChange: (value: string) => void;
    onServiceAccountApiKeyChange: (value: string) => void;
  };
  isActive: boolean;
  handleActiveToggle: (value: boolean) => void;
  handleConnect: () => void;
  handleClose: () => void;
  isConnectDisabled: boolean;
  workspacePlaceholderKey: I18nKey;
};

function useConfigureModalState({
  isOpen,
  existingWorkspace,
  platform,
  onClose,
  onConfirm,
  onLink,
  t,
}: ConfigureModalStateOptions): ConfigureModalStateReturn {
  const [workspace, setWorkspace] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [serviceAccountEmail, setServiceAccountEmail] = useState("");
  const [serviceAccountApiKey, setServiceAccountApiKey] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [showConfigurationFields, setShowConfigurationFields] = useState(false);

  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [webhookSecretError, setWebhookSecretError] = useState<string | null>(
    null,
  );
  const [emailError, setEmailError] = useState<string | null>(null);
  const [apiKeyError, setApiKeyError] = useState<string | null>(null);

  const workspaceRef = useRef("");
  const isWorkspaceEditable = existingWorkspace?.editable ?? false;

  const workspacePlaceholderKey = useMemo(
    () => getWorkspacePlaceholderKey(platform),
    [platform],
  );

  const resetForm = useCallback(() => {
    setWorkspace("");
    workspaceRef.current = "";
    setWebhookSecret("");
    setServiceAccountEmail("");
    setServiceAccountApiKey("");
    setIsActive(true);
    setShowConfigurationFields(false);
    setWorkspaceError(null);
    setWebhookSecretError(null);
    setEmailError(null);
    setApiKeyError(null);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    resetForm();

    if (existingWorkspace) {
      const name = existingWorkspace.name ?? "";
      setWorkspace(name);
      workspaceRef.current = name;
      setShowConfigurationFields(isWorkspaceEditable);
    }
  }, [isOpen, existingWorkspace, isWorkspaceEditable, resetForm]);

  const validateMutation = useValidateIntegration(platform, {
    onSuccess: (data) => {
      if (data.data.status === "active") {
        onLink(workspaceRef.current);
      } else {
        setShowConfigurationFields(true);
        setIsActive(true);
      }
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        setShowConfigurationFields(true);
        setIsActive(true);
        return;
      }
      setShowConfigurationFields(true);
      setIsActive(true);
    },
  });

  const handleWorkspaceChange = useCallback(
    (value: string) => {
      workspaceRef.current = value;
      setWorkspace(value);
      setWorkspaceError(validateWorkspaceValue(value, t));
    },
    [t],
  );

  const handleWebhookSecretChange = useCallback(
    (value: string) => {
      setWebhookSecret(value);
      setWebhookSecretError(
        validateNoSpacesValue(
          value,
          I18nKey.PROJECT_MANAGEMENT$WEBHOOK_SECRET_NAME_VALIDATION_ERROR,
          t,
        ),
      );
    },
    [t],
  );

  const handleEmailChange = useCallback(
    (value: string) => {
      setServiceAccountEmail(value);
      setEmailError(validateEmailValue(value, t));
    },
    [t],
  );

  const handleApiKeyChange = useCallback(
    (value: string) => {
      setServiceAccountApiKey(value);
      setApiKeyError(
        validateNoSpacesValue(
          value,
          I18nKey.PROJECT_MANAGEMENT$SVC_ACC_API_KEY_VALIDATION_ERROR,
          t,
        ),
      );
    },
    [t],
  );

  const handleActiveToggle = useCallback((value: boolean) => {
    setIsActive(value);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose, resetForm]);

  const handleConnect = useCallback(() => {
    const trimmedWorkspace = workspace.trim();
    workspaceRef.current = trimmedWorkspace;

    if (showConfigurationFields) {
      onConfirm({
        workspace: trimmedWorkspace,
        webhookSecret: webhookSecret.trim(),
        serviceAccountEmail: serviceAccountEmail.trim(),
        serviceAccountApiKey: serviceAccountApiKey.trim(),
        isActive,
      });
      return;
    }

    if (!existingWorkspace) {
      validateMutation.mutate(trimmedWorkspace);
    }
  }, [
    existingWorkspace,
    isActive,
    onConfirm,
    serviceAccountApiKey,
    serviceAccountEmail,
    showConfigurationFields,
    validateMutation,
    webhookSecret,
    workspace,
  ]);

  const isConnectDisabled = useMemo(() => {
    if (showConfigurationFields) {
      return (
        !workspace.trim() ||
        !webhookSecret.trim() ||
        !serviceAccountEmail.trim() ||
        !serviceAccountApiKey.trim() ||
        Boolean(
          workspaceError || webhookSecretError || emailError || apiKeyError,
        ) ||
        validateMutation.isPending
      );
    }

    return (
      !workspace.trim() || workspaceError !== null || validateMutation.isPending
    );
  }, [
    apiKeyError,
    emailError,
    serviceAccountApiKey,
    serviceAccountEmail,
    showConfigurationFields,
    validateMutation.isPending,
    webhookSecret,
    webhookSecretError,
    workspace,
    workspaceError,
  ]);

  return {
    workspace,
    workspaceError,
    handleWorkspaceChange,
    showConfigurationFields,
    isWorkspaceEditable,
    configurationFields: {
      webhookSecret,
      serviceAccountEmail,
      serviceAccountApiKey,
    },
    configurationErrors: {
      webhookSecret: webhookSecretError,
      serviceAccountEmail: emailError,
      serviceAccountApiKey: apiKeyError,
    },
    configurationHandlers: {
      onWebhookSecretChange: handleWebhookSecretChange,
      onServiceAccountEmailChange: handleEmailChange,
      onServiceAccountApiKeyChange: handleApiKeyChange,
    },
    isActive,
    handleActiveToggle,
    handleConnect,
    handleClose,
    isConnectDisabled,
    workspacePlaceholderKey,
  };
}

function WorkspaceSection({
  value,
  onChange,
  error,
  label,
  placeholder,
  existingWorkspace,
  onUnlink,
  unlinkLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  error: string | null;
  label: string;
  placeholder: string;
  existingWorkspace: {
    id: number;
    name: string;
    status: string;
    editable: boolean;
  } | null;
  onUnlink?: () => void;
  unlinkLabel: string;
}) {
  const isDisabled = Boolean(existingWorkspace);

  return (
    <div>
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <SettingsInput
            label={label}
            placeholder={placeholder}
            value={value}
            onChange={onChange}
            className="w-full"
            type="text"
            pattern="^[a-zA-Z0-9\-_.]*$"
            isDisabled={isDisabled}
          />
        </div>
        {existingWorkspace && onUnlink && (
          <BrandButton
            variant="secondary"
            onClick={onUnlink}
            data-testid="unlink-button"
            type="button"
            className="mb-0"
          >
            {unlinkLabel}
          </BrandButton>
        )}
      </div>
      {error && <p className="text-error-500 text-sm mt-2">{error}</p>}
    </div>
  );
}

function ConfigurationFieldsSection({
  values,
  errors,
  onChange,
  onToggleActive,
  isActive,
  labels,
}: {
  values: {
    webhookSecret: string;
    serviceAccountEmail: string;
    serviceAccountApiKey: string;
  };
  errors: {
    webhookSecret: string | null;
    serviceAccountEmail: string | null;
    serviceAccountApiKey: string | null;
  };
  onChange: {
    onWebhookSecretChange: (value: string) => void;
    onServiceAccountEmailChange: (value: string) => void;
    onServiceAccountApiKeyChange: (value: string) => void;
  };
  onToggleActive: (value: boolean) => void;
  isActive: boolean;
  labels: ReturnType<typeof buildConfigurationLabels>;
}) {
  return (
    <>
      <div>
        <SettingsInput
          label={labels.webhookSecretLabel}
          placeholder={labels.webhookSecretPlaceholder}
          value={values.webhookSecret}
          onChange={onChange.onWebhookSecretChange}
          className="w-full"
          type="password"
        />
        {errors.webhookSecret && (
          <p className="text-error-500 text-sm mt-2">{errors.webhookSecret}</p>
        )}
      </div>
      <div>
        <SettingsInput
          label={labels.serviceAccountEmailLabel}
          placeholder={labels.serviceAccountEmailPlaceholder}
          value={values.serviceAccountEmail}
          onChange={onChange.onServiceAccountEmailChange}
          className="w-full"
          type="email"
        />
        {errors.serviceAccountEmail && (
          <p className="text-error-500 text-sm mt-2">
            {errors.serviceAccountEmail}
          </p>
        )}
      </div>
      <div>
        <SettingsInput
          label={labels.serviceAccountApiKeyLabel}
          placeholder={labels.serviceAccountApiKeyPlaceholder}
          value={values.serviceAccountApiKey}
          onChange={onChange.onServiceAccountApiKeyChange}
          className="w-full"
          type="password"
        />
        {errors.serviceAccountApiKey && (
          <p className="text-error-500 text-sm mt-2">
            {errors.serviceAccountApiKey}
          </p>
        )}
      </div>
      <div className="mt-4">
        <SettingsSwitch
          testId="active-toggle"
          onToggle={onToggleActive}
          isToggled={isActive}
        >
          {labels.activeToggleLabel}
        </SettingsSwitch>
      </div>
    </>
  );
}

function ModalActions({
  showConnectButton,
  onConnect,
  onCancel,
  connectLabel,
  cancelLabel,
  isConnectDisabled,
}: {
  showConnectButton: boolean;
  onConnect: () => void;
  onCancel: () => void;
  connectLabel: string;
  cancelLabel: string;
  isConnectDisabled: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 w-full mt-4">
      {showConnectButton && (
        <BrandButton
          variant="primary"
          onClick={onConnect}
          data-testid="connect-button"
          type="button"
          className="w-full"
          isDisabled={isConnectDisabled}
        >
          {connectLabel}
        </BrandButton>
      )}
      <BrandButton
        variant="secondary"
        onClick={onCancel}
        data-testid="cancel-button"
        type="button"
        className="w-full"
      >
        {cancelLabel}
      </BrandButton>
    </div>
  );
}

function ConfigureModalDescription({
  variant,
  platformName,
}: {
  variant: "link" | "configure";
  platformName: string;
}) {
  const link = (
    <a
      href="https://docs.all-hands.dev/usage/cloud/Forge-cloud"
      target="_blank"
      rel="noopener noreferrer"
      className="text-violet-500 hover:text-brand-400 hover:underline transition-colors duration-200"
    >
      Check the document for more information
    </a>
  );

  const baseComponents = {
    b: <b />,
    a: link,
  };

  if (variant === "configure") {
    return (
      <Trans
        i18nKey={I18nKey.PROJECT_MANAGEMENT$CONFIGURE_MODAL_DESCRIPTION_STAGE_2}
        components={baseComponents}
      />
    );
  }

  return (
    <Trans
      i18nKey={I18nKey.PROJECT_MANAGEMENT$CONFIGURE_MODAL_DESCRIPTION_STAGE_1}
      components={baseComponents}
      values={{ platform: platformName }}
    />
  );
}

function buildConfigurationLabels(t: TFunction) {
  return {
    webhookSecretLabel: t(I18nKey.PROJECT_MANAGEMENT$WEBHOOK_SECRET_LABEL),
    webhookSecretPlaceholder: t(
      I18nKey.PROJECT_MANAGEMENT$WEBHOOK_SECRET_PLACEHOLDER,
    ),
    serviceAccountEmailLabel: t(
      I18nKey.PROJECT_MANAGEMENT$SERVICE_ACCOUNT_EMAIL_LABEL,
    ),
    serviceAccountEmailPlaceholder: t(
      I18nKey.PROJECT_MANAGEMENT$SERVICE_ACCOUNT_EMAIL_PLACEHOLDER,
    ),
    serviceAccountApiKeyLabel: t(
      I18nKey.PROJECT_MANAGEMENT$SERVICE_ACCOUNT_API_LABEL,
    ),
    serviceAccountApiKeyPlaceholder: t(
      I18nKey.PROJECT_MANAGEMENT$SERVICE_ACCOUNT_API_PLACEHOLDER,
    ),
    activeToggleLabel: t(I18nKey.PROJECT_MANAGEMENT$ACTIVE_TOGGLE_LABEL),
  };
}

function getConnectButtonLabel({
  existingWorkspace,
  showConfigurationFields,
  t,
}: {
  existingWorkspace: {
    id: number;
    name: string;
    status: string;
    editable: boolean;
  } | null;
  showConfigurationFields: boolean;
  t: TFunction;
}): string {
  if (existingWorkspace && showConfigurationFields) {
    return t(I18nKey.PROJECT_MANAGEMENT$UPDATE_BUTTON_LABEL);
  }
  return t(I18nKey.PROJECT_MANAGEMENT$CONNECT_BUTTON_LABEL);
}

function getWorkspacePlaceholderKey(platform: "jira" | "jira-dc" | "linear") {
  if (platform === "jira") {
    return I18nKey.PROJECT_MANAGEMENT$JIRA_WORKSPACE_NAME_PLACEHOLDER;
  }
  if (platform === "jira-dc") {
    return I18nKey.PROJECT_MANAGEMENT$JIRA_DC_WORKSPACE_NAME_PLACEHOLDER;
  }
  return I18nKey.PROJECT_MANAGEMENT$LINEAR_WORKSPACE_NAME_PLACEHOLDER;
}

function validateWorkspaceValue(value: string, t: TFunction): string | null {
  const isValid = /^[a-zA-Z0-9\-_.]*$/.test(value);
  if (!isValid && value.length > 0) {
    return t(I18nKey.PROJECT_MANAGEMENT$WORKSPACE_NAME_VALIDATION_ERROR);
  }
  return null;
}

function validateNoSpacesValue(
  value: string,
  errorKey: I18nKey,
  t: TFunction,
): string | null {
  if (value && /\s/.test(value)) {
    return t(errorKey);
  }
  return null;
}

function validateEmailValue(value: string, t: TFunction): string | null {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (value && !emailRegex.test(value)) {
    return t(I18nKey.PROJECT_MANAGEMENT$SVC_ACC_EMAIL_VALIDATION_ERROR);
  }
  return null;
}
