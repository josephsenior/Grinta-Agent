import React, { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import logo from "#/assets/branding/logo1.png";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import { BrandButton } from "../settings/brand-button";
import GitHubLogo from "#/assets/branding/github-logo.svg?react";
import GitLabLogo from "#/assets/branding/gitlab-logo.svg?react";
import BitbucketLogo from "#/assets/branding/bitbucket-logo.svg?react";
import { useAuthUrl } from "#/hooks/use-auth-url";
import { GetConfigResponse } from "#/api/forge.types";
import { Provider } from "#/types/settings";

interface AuthModalProps {
  githubAuthUrl: string | null;
  appMode?: GetConfigResponse["APP_MODE"] | null;
  authUrl?: GetConfigResponse["AUTH_URL"];
  providersConfigured?: Provider[];
}

export function AuthModal({
  githubAuthUrl,
  appMode,
  authUrl,
  providersConfigured,
}: AuthModalProps) {
  const { t } = useTranslation();

  const gitlabAuthUrl = useAuthUrl({
    appMode: appMode || null,
    identityProvider: "gitlab",
    authUrl,
  });

  const bitbucketAuthUrl = useAuthUrl({
    appMode: appMode || null,
    identityProvider: "bitbucket",
    authUrl,
  });

  const enterpriseSsoUrl = useAuthUrl({
    appMode: appMode || null,
    identityProvider: "enterprise_sso",
    authUrl,
  });

  const handleAuthClick = useCallback((url: string | null) => {
    if (url) {
      window.location.href = url;
    }
  }, []);

  const configuredProviders = useMemo(
    () => new Set<Provider>(providersConfigured ?? []),
    [providersConfigured],
  );

  const authOptions = useMemo(() => {
    const options: AuthProviderOption[] = [];

    if (configuredProviders.has("github") && githubAuthUrl) {
      options.push({
        key: "github",
        labelKey: I18nKey.GITHUB$CONNECT_TO_GITHUB,
        icon: <GitHubLogo width={20} height={20} />,
        url: githubAuthUrl,
      });
    }

    if (configuredProviders.has("gitlab") && gitlabAuthUrl) {
      options.push({
        key: "gitlab",
        labelKey: I18nKey.GITLAB$CONNECT_TO_GITLAB,
        icon: <GitLabLogo width={20} height={20} />,
        url: gitlabAuthUrl,
      });
    }

    if (configuredProviders.has("bitbucket") && bitbucketAuthUrl) {
      options.push({
        key: "bitbucket",
        labelKey: I18nKey.BITBUCKET$CONNECT_TO_BITBUCKET,
        icon: <BitbucketLogo width={20} height={20} />,
        url: bitbucketAuthUrl,
      });
    }

    if (configuredProviders.has("enterprise_sso") && enterpriseSsoUrl) {
      options.push({
        key: "enterprise_sso",
        labelKey: I18nKey.ENTERPRISE_SSO$CONNECT_TO_ENTERPRISE_SSO,
        icon: null,
        url: enterpriseSsoUrl,
      });
    }

    return options;
  }, [
    configuredProviders,
    githubAuthUrl,
    gitlabAuthUrl,
    bitbucketAuthUrl,
    enterpriseSsoUrl,
  ]);

  const hasProviders = authOptions.length > 0;

  return (
    <ModalBackdrop>
      <ModalBody className="border border-border">
        <img
          src={logo}
          alt="Forge Pro Logo"
          className="h-12 w-auto select-none drop-shadow-[0_0_4px_rgba(255,200,80,0.35)]"
          draggable={false}
        />
        <div className="flex flex-col gap-2 w-full items-center text-center">
          <h1 className="text-2xl font-bold">
            {t(I18nKey.AUTH$SIGN_IN_WITH_IDENTITY_PROVIDER)}
          </h1>
        </div>

        <div className="flex flex-col gap-3 w-full">
          {!hasProviders ? (
            <div className="text-center p-4 text-muted-foreground">
              {t(I18nKey.AUTH$NO_PROVIDERS_CONFIGURED)}
            </div>
          ) : (
            authOptions.map((option) => (
              <AuthProviderButton
                key={option.key}
                label={t(option.labelKey)}
                icon={option.icon}
                onClick={() => handleAuthClick(option.url)}
              />
            ))
          )}
        </div>

        <p
          className="mt-4 text-xs text-center text-muted-foreground"
          data-testid="auth-modal-terms-of-service"
        >
          {t(I18nKey.AUTH$BY_SIGNING_UP_YOU_AGREE_TO_OUR)}{" "}
          <a
            href="https://www.all-hands.dev/tos"
            target="_blank"
            className="underline hover:text-primary"
            rel="noopener noreferrer"
          >
            {t(I18nKey.COMMON$TERMS_OF_SERVICE)}
          </a>{" "}
          {t(I18nKey.COMMON$AND)}{" "}
          <a
            href="https://www.all-hands.dev/privacy"
            target="_blank"
            className="underline hover:text-primary"
            rel="noopener noreferrer"
          >
            {t(I18nKey.COMMON$PRIVACY_POLICY)}
          </a>
          .
        </p>
      </ModalBody>
    </ModalBackdrop>
  );
}

interface AuthProviderOption {
  key: Provider;
  labelKey: I18nKey;
  icon?: React.ReactNode | null;
  url: string;
}

function AuthProviderButton({
  label,
  icon,
  onClick,
}: {
  label: string;
  icon?: React.ReactNode | null;
  onClick: () => void;
}) {
  return (
    <BrandButton
      type="button"
      variant="primary"
      onClick={onClick}
      className="w-full"
      startContent={icon ?? undefined}
    >
      {label}
    </BrandButton>
  );
}
