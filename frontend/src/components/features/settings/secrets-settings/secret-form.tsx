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

  // error state removed; individual field errors are tracked separately
  const [nameError, setNameError] = React.useState<string | null>(null);
  const [valueError, setValueError] = React.useState<string | null>(null);

  const secretDescription =
    (mode === "edit" &&
      selectedSecret &&
      secrets
        ?.find((secret) => secret.name === selectedSecret)
        ?.description?.trim()) ||
    "";

  const handleCreateSecret = (
    name: string,
    value: string,
    description?: string,
  ) => {
    createSecret(
      { name, value, description },
      {
        onSettled: onCancel,
        onSuccess: async () => {
          await queryClient.invalidateQueries({ queryKey: ["secrets"] });
        },
      },
    );
  };

  const updateSecretOptimistically = (
    oldName: string,
    name: string,
    description?: string,
  ) => {
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
  };

  const revertOptimisticUpdate = () => {
    queryClient.invalidateQueries({ queryKey: ["secrets"] });
  };

  const handleEditSecret = (
    secretToEdit: string,
    name: string,
    description?: string,
  ) => {
    updateSecretOptimistically(secretToEdit, name, description);
    updateSecret(
      { secretToEdit, name, description },
      {
        onSettled: onCancel,
        onError: revertOptimisticUpdate,
      },
    );
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const name = formData.get("secret-name")?.toString();
    const value = formData.get("secret-value")?.toString().trim();
    const description = formData.get("secret-description")?.toString();

    // clear previous errors
    setNameError(null);
    setValueError(null);

    if (name) {
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
      } else if (mode === "edit" && selectedSecret) {
        handleEditSecret(selectedSecret, name, description || undefined);
      }
    }
  };

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
