import { useQueryClient } from "@tanstack/react-query";
import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { useCreateSecret } from "#/hooks/mutation/use-create-secret";
import { useUpdateSecret } from "#/hooks/mutation/use-update-secret";
import { SettingsInput } from "../settings-input";
import { cn } from "#/utils/utils";
import { BrandButton } from "../brand-button";
import { useGetSecrets } from "#/hooks/query/use-get-secrets";
import { GetSecretsResponse } from "#/api/secrets-service.types";
import { OptionalTag } from "../optional-tag";

interface SecretFormProps {
  mode: "add" | "edit";
  selectedSecret: string | null;
  onCancel: () => void;
}

export function SecretForm({
  mode,
  selectedSecret,
  onCancel,
}: SecretFormProps) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const { data: secrets } = useGetSecrets();
  const { mutate: createSecret } = useCreateSecret();
  const { mutate: updateSecret } = useUpdateSecret();

  const { secretDescription, nameError, valueError, handleSubmit } = useSecretFormState({
    mode,
    selectedSecret,
    onCancel,
    secrets,
    createSecret,
    updateSecret,
    queryClient,
    t,
  });

  const formTestId = mode === "add" ? "add-secret-form" : "edit-secret-form";

  return (
    <form
      data-testid={formTestId}
      onSubmit={handleSubmit}
      className="flex flex-col items-start gap-6"
    >
      <SettingsInput
        testId="name-input"
        name="secret-name"
        type="text"
        label="Name"
        className="w-full max-w-[350px]"
        required
        defaultValue={mode === "edit" && selectedSecret ? selectedSecret : ""}
        placeholder={t("SECRETS$API_KEY_EXAMPLE")}
        pattern="^\S*$"
        error={nameError}
      />

      {mode === "add" && (
        <label className="flex flex-col gap-2.5 w-full max-w-[680px]">
          <span className="text-sm">{t(I18nKey.FORM$VALUE)}</span>
          <textarea
            aria-invalid={!!valueError}
            aria-describedby={valueError ? "secret-value-error" : undefined}
            data-testid="value-input"
            name="secret-value"
            required
            className={cn(
              "resize-none",
              "bg-background-secondary backdrop-blur-xl border border-border rounded-xl p-3 placeholder:italic placeholder:text-foreground-secondary text-foreground transition-all duration-200 focus:border-brand-500/50 focus:bg-brand-500/5 focus:shadow-lg focus:shadow-brand-500/10",
              valueError ? "border-danger-500/80 bg-danger-500/5" : "",
              "disabled:bg-background-tertiary disabled:border-border disabled:cursor-not-allowed disabled:opacity-50",
            )}
            rows={8}
          />
          {valueError && (
            <p
              id="secret-value-error"
              role="alert"
              className="text-danger-500 text-sm mt-1"
            >
              {valueError}
            </p>
          )}
        </label>
      )}

      <label className="flex flex-col gap-2.5 w-full max-w-[680px]">
        <div className="flex items-center gap-2">
          <span className="text-sm">{t(I18nKey.FORM$DESCRIPTION)}</span>
          <OptionalTag />
        </div>
        <input
          data-testid="description-input"
          name="secret-description"
          defaultValue={secretDescription}
          className={cn(
            "resize-none",
            "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl p-3 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
            "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
          )}
        />
      </label>

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
          {mode === "add" && t("SECRETS$ADD_SECRET")}
          {mode === "edit" && t("SECRETS$EDIT_SECRET")}
        </BrandButton>
      </div>
    </form>
  );
}

function useSecretFormState({
  mode,
  selectedSecret,
  onCancel,
  secrets,
  createSecret,
  updateSecret,
  queryClient,
  t,
}: {
  mode: SecretFormProps["mode"];
  selectedSecret: SecretFormProps["selectedSecret"];
  onCancel: SecretFormProps["onCancel"];
  secrets: GetSecretsResponse["custom_secrets"] | undefined;
  createSecret: ReturnType<typeof useCreateSecret>["mutate"];
  updateSecret: ReturnType<typeof useUpdateSecret>["mutate"];
  queryClient: ReturnType<typeof useQueryClient>;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const [nameError, setNameError] = React.useState<string | null>(null);
  const [valueError, setValueError] = React.useState<string | null>(null);

  const secretDescription = React.useMemo(() => {
    if (mode !== "edit" || !selectedSecret || !secrets) {
      return "";
    }

    return secrets.find((secret) => secret.name === selectedSecret)?.description?.trim() ?? "";
  }, [mode, secrets, selectedSecret]);

  const handleCreateSecret = React.useCallback(
    (name: string, value: string, description?: string) => {
      createSecret(
        { name, value, description },
        {
          onSettled: onCancel,
          onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["secrets"] });
          },
        },
      );
    },
    [createSecret, onCancel, queryClient],
  );

  const updateSecretOptimistically = React.useCallback(
    (oldName: string, name: string, description?: string) => {
      queryClient.setQueryData<GetSecretsResponse["custom_secrets"]>(
        ["secrets"],
        (oldSecrets) => {
          if (!oldSecrets) {
            return [];
          }
          return oldSecrets.map((secret) => {
            if (secret.name === oldName) {
              return {
                ...secret,
                name,
                description,
              };
            }
            return secret;
          });
        },
      );
    },
    [queryClient],
  );

  const revertOptimisticUpdate = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["secrets"] });
  }, [queryClient]);

  const handleEditSecret = React.useCallback(
    (secretToEdit: string, name: string, description?: string) => {
      updateSecretOptimistically(secretToEdit, name, description);
      updateSecret(
        { secretToEdit, name, description },
        {
          onSettled: onCancel,
          onError: revertOptimisticUpdate,
        },
      );
    },
    [onCancel, revertOptimisticUpdate, updateSecret, updateSecretOptimistically],
  );

  const handleSubmit = React.useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const formData = new FormData(event.currentTarget);
      const name = formData.get("secret-name")?.toString();
      const value = formData.get("secret-value")?.toString().trim();
      const description = formData.get("secret-description")?.toString();

      setNameError(null);
      setValueError(null);

      const isNameAlreadyUsed = secrets?.some(
        (secret) => secret.name === name && secret.name !== selectedSecret,
      );
      if (isNameAlreadyUsed) {
        setNameError(t("SECRETS$SECRET_ALREADY_EXISTS"));
        return;
      }

      if (mode === "add") {
        if (!value) {
          setValueError(t("SECRETS$SECRET_VALUE_REQUIRED"));
          return;
        }
        handleCreateSecret(name, value, description || undefined);
        return;
      }

      if (mode === "edit" && selectedSecret) {
        handleEditSecret(selectedSecret, name, description || undefined);
      }
    },
    [
      handleCreateSecret,
      handleEditSecret,
      mode,
      secrets,
      selectedSecret,
      t,
    ],
  );

  return {
    secretDescription,
    nameError,
    valueError,
    handleSubmit,
  };
}
