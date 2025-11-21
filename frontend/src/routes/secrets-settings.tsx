import { useQueryClient } from "@tanstack/react-query";
import React from "react";
import { useTranslation } from "react-i18next";
import { useGetSecrets } from "#/hooks/query/use-get-secrets";
import { useDeleteSecret } from "#/hooks/mutation/use-delete-secret";
import { SecretForm } from "#/components/features/settings/secrets-settings/secret-form";
import { ConfirmationModal } from "#/components/shared/modals/confirmation-modal";
import { GetSecretsResponse } from "#/api/secrets-service.types";
import { useUserProviders } from "#/hooks/use-user-providers";
import { useConfig } from "#/hooks/query/use-config";
import { useSecretsState } from "./secrets-settings/use-secrets-state";
import { SecretsListView } from "./secrets-settings/secrets-list-view";

function SecretsSettingsScreen() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const { data: config } = useConfig();
  const { data: secrets, isLoading: isLoadingSecrets } = useGetSecrets();
  const { mutate: deleteSecret } = useDeleteSecret();
  const { providers } = useUserProviders();

  const isSaas = config?.APP_MODE === "saas";
  const hasProviderSet = providers.length > 0;
  const shouldRenderConnectToGitButton = isSaas && !hasProviderSet;

  const {
    view,
    selectedSecret,
    confirmationModalIsVisible,
    handleEdit,
    handleDelete,
    handleCancel,
    handleAddNew,
    handleConfirmDelete,
    handleCancelDelete,
  } = useSecretsState();

  const deleteSecretOptimistically = (secret: string) => {
    queryClient.setQueryData<GetSecretsResponse["custom_secrets"]>(
      ["secrets"],
      (oldSecrets) => {
        if (!oldSecrets) {
          return [];
        }
        return oldSecrets.filter((s) => s.name !== secret);
      },
    );
  };

  const revertOptimisticUpdate = () => {
    queryClient.invalidateQueries({ queryKey: ["secrets"] });
  };

  const handleDeleteSecret = (secret: string) => {
    deleteSecretOptimistically(secret);
    deleteSecret(secret, {
      onSettled: handleConfirmDelete,
      onError: revertOptimisticUpdate,
    });
  };

  const onConfirmDeleteSecret = () => {
    if (selectedSecret) {
      handleDeleteSecret(selectedSecret);
    }
  };

  return (
    <div
      data-testid="secrets-settings-screen"
      className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8"
    >
      {view === "list" && (
        <SecretsListView
          secrets={secrets}
          isLoading={isLoadingSecrets}
          shouldRenderConnectButton={shouldRenderConnectToGitButton}
          onAddNew={handleAddNew}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}

      {(view === "add-secret-form" || view === "edit-secret-form") && (
        <SecretForm
          mode={view === "add-secret-form" ? "add" : "edit"}
          selectedSecret={selectedSecret}
          onCancel={handleCancel}
        />
      )}

      {confirmationModalIsVisible && (
        <ConfirmationModal
          text={t("SECRETS$CONFIRM_DELETE_KEY")}
          onConfirm={onConfirmDeleteSecret}
          onCancel={handleCancelDelete}
        />
      )}
    </div>
  );
}

export default SecretsSettingsScreen;
