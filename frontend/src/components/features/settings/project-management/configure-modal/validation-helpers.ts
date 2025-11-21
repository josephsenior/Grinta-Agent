export interface ValidationInputs {
  showConfigurationFields: boolean;
  workspace: string;
  webhookSecret: string;
  serviceAccountEmail: string;
  serviceAccountApiKey: string;
  workspaceError: string | null;
  webhookSecretError: string | null;
  emailError: string | null;
  apiKeyError: string | null;
  isPending: boolean;
}

export function hasEmptyConfigurationFields(inputs: ValidationInputs): boolean {
  return (
    !inputs.workspace.trim() ||
    !inputs.webhookSecret.trim() ||
    !inputs.serviceAccountEmail.trim() ||
    !inputs.serviceAccountApiKey.trim()
  );
}

export function hasConfigurationErrors(inputs: ValidationInputs): boolean {
  return Boolean(
    inputs.workspaceError ||
      inputs.webhookSecretError ||
      inputs.emailError ||
      inputs.apiKeyError,
  );
}

export function hasBasicValidationErrors(inputs: ValidationInputs): boolean {
  return !inputs.workspace.trim() || inputs.workspaceError !== null;
}

export function validateConnectButton(inputs: ValidationInputs): boolean {
  if (inputs.isPending) {
    return true;
  }

  if (inputs.showConfigurationFields) {
    return (
      hasEmptyConfigurationFields(inputs) || hasConfigurationErrors(inputs)
    );
  }

  return hasBasicValidationErrors(inputs);
}
