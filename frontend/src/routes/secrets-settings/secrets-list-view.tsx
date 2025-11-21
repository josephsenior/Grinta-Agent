import React from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { BrandButton } from "#/components/features/settings/brand-button";
import {
  SecretListItem,
  SecretListItemSkeleton,
} from "#/components/features/settings/secrets-settings/secret-list-item";
import { I18nKey } from "#/i18n/declaration";
import type { GetSecretsResponse } from "#/api/secrets-service.types";

interface SecretsListViewProps {
  secrets: GetSecretsResponse["custom_secrets"] | undefined;
  isLoading: boolean;
  shouldRenderConnectButton: boolean;
  onAddNew: () => void;
  onEdit: (secretName: string) => void;
  onDelete: (secretName: string) => void;
}

export function SecretsListView({
  secrets,
  isLoading,
  shouldRenderConnectButton,
  onAddNew,
  onEdit,
  onDelete,
}: SecretsListViewProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <ul>
        <SecretListItemSkeleton />
        <SecretListItemSkeleton />
        <SecretListItemSkeleton />
      </ul>
    );
  }

  return (
    <>
      {shouldRenderConnectButton && (
        <Link
          to="/settings/integrations"
          data-testid="connect-git-button"
          type="button"
          className="self-start"
        >
          <BrandButton type="button" variant="secondary">
            {t(I18nKey.SECRETS$CONNECT_GIT_PROVIDER)}
          </BrandButton>
        </Link>
      )}

      {!shouldRenderConnectButton && (
        <BrandButton
          testId="add-secret-button"
          type="button"
          variant="primary"
          onClick={onAddNew}
          isDisabled={isLoading}
        >
          {t("SECRETS$ADD_NEW_SECRET")}
        </BrandButton>
      )}

      <div className="border border-white/10 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-base-tertiary">
            <tr className="flex w-full items-center">
              <th className="w-1/4 text-left p-3 text-sm font-medium">
                {t(I18nKey.SETTINGS$NAME)}
              </th>
              <th className="w-1/2 text-left p-3 text-sm font-medium">
                {t(I18nKey.SECRETS$DESCRIPTION)}
              </th>
              <th className="w-1/4 text-right p-3 text-sm font-medium">
                {t(I18nKey.SETTINGS$ACTIONS)}
              </th>
            </tr>
          </thead>
          <tbody>
            {secrets?.map((secret) => (
              <SecretListItem
                key={secret.name}
                title={secret.name}
                description={secret.description}
                onEdit={() => onEdit(secret.name)}
                onDelete={() => onDelete(secret.name)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
