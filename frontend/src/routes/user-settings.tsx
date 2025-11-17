import React, { useState, useEffect, useRef, useId } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { useSettings } from "#/hooks/query/use-settings";
import { Forge } from "#/api/forge-axios";
import { displaySuccessToast } from "#/utils/custom-toast-handlers";
import { ThemeToggle } from "#/components/ui/theme-toggle";

// Email validation regex pattern
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

function EmailInputSection({
  email,
  onEmailChange,
  onSaveEmail,
  onResendVerification,
  isSaving,
  isResendingVerification,
  isEmailChanged,
  emailVerified,
  isEmailValid,
  children,
}: {
  email: string;
  onEmailChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSaveEmail: () => void;
  onResendVerification: () => void;
  isSaving: boolean;
  isResendingVerification: boolean;
  isEmailChanged: boolean;
  emailVerified?: boolean;
  isEmailValid: boolean;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3">
        <label className="text-sm font-medium text-foreground">
          {t("SETTINGS$USER_EMAIL")}
        </label>
        <div className="flex items-center gap-3">
          <input
            type="email"
            value={email}
            onChange={onEmailChange}
            className={`text-base text-foreground px-4 py-2.5 bg-black/60 rounded-xl border backdrop-blur-sm transition-all ${
              isEmailChanged && !isEmailValid
                ? "border-danger-500/50 focus:border-danger-500"
                : "border-white/10 focus:border-white/20 hover:border-white/15"
            } flex-grow focus:outline-none`}
            placeholder={t("SETTINGS$USER_EMAIL_LOADING")}
            data-testid="email-input"
          />
        </div>

        {isEmailChanged && !isEmailValid && (
          <div
            className="text-danger-400 text-sm"
            data-testid="email-validation-error"
          >
            {t("SETTINGS$INVALID_EMAIL_FORMAT")}
          </div>
        )}

        <div className="flex items-center gap-3 mt-1">
          <button
            type="button"
            onClick={onSaveEmail}
            disabled={!isEmailChanged || isSaving || !isEmailValid}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white font-medium shadow-lg shadow-brand-500/30 hover:shadow-xl hover:shadow-brand-500/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg"
            data-testid="save-email-button"
          >
            {isSaving ? t("SETTINGS$SAVING") : t("SETTINGS$SAVE")}
          </button>

          {emailVerified === false && (
            <button
              type="button"
              onClick={onResendVerification}
              disabled={isResendingVerification}
              className="px-5 py-2.5 rounded-xl border border-white/20 bg-white/5 text-foreground font-medium hover:bg-white/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="resend-verification-button"
            >
              {isResendingVerification
                ? t("SETTINGS$SENDING")
                : t("SETTINGS$RESEND_VERIFICATION")}
            </button>
          )}
        </div>

        {children}
      </div>
    </div>
  );
}

function VerificationAlert() {
  const { t } = useTranslation();
  return (
    <div
      className="rounded-xl border border-danger-500/30 bg-danger-500/10 backdrop-blur-sm px-4 py-3 mt-4"
      role="alert"
    >
      <p className="font-semibold text-danger-400">
        {t("SETTINGS$EMAIL_VERIFICATION_REQUIRED")}
      </p>
      <p className="text-sm text-danger-400/80 mt-1">
        {t("SETTINGS$EMAIL_VERIFICATION_RESTRICTION_MESSAGE")}
      </p>
    </div>
  );
}

// These components have been replaced with toast notifications

function UserSettingsScreen() {
  const { t } = useTranslation();
  const { data: settings, isLoading, refetch } = useSettings();
  const [email, setEmail] = useState("");
  const [originalEmail, setOriginalEmail] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isResendingVerification, setIsResendingVerification] = useState(false);
  const [isEmailValid, setIsEmailValid] = useState(true);
  const queryClient = useQueryClient();
  const pollingIntervalRef = useRef<number | null>(null);
  const prevVerificationStatusRef = useRef<boolean | undefined>(undefined);

  useEffect(() => {
    if (settings?.EMAIL) {
      setEmail(settings.EMAIL);
      setOriginalEmail(settings.EMAIL);
      setIsEmailValid(EMAIL_REGEX.test(settings.EMAIL));
    }
  }, [settings?.EMAIL]);

  useEffect(() => {
    if (pollingIntervalRef.current) {
      window.clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    if (
      prevVerificationStatusRef.current === false &&
      settings?.EMAIL_VERIFIED === true
    ) {
      // Display toast notification instead of setting state
      displaySuccessToast(t("SETTINGS$EMAIL_VERIFIED_SUCCESSFULLY"));
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["settings"] });
      }, 2000);
    }

    prevVerificationStatusRef.current = settings?.EMAIL_VERIFIED;

    if (settings?.EMAIL_VERIFIED === false) {
      pollingIntervalRef.current = window.setInterval(() => {
        refetch();
      }, 5000);
    }

    return () => {
      if (pollingIntervalRef.current) {
        window.clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [settings?.EMAIL_VERIFIED, refetch, queryClient, t]);

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEmail = e.target.value;
    setEmail(newEmail);
    setIsEmailValid(EMAIL_REGEX.test(newEmail));
  };

  const handleSaveEmail = async () => {
    if (email === originalEmail || !isEmailValid) {
      return;
    }
    try {
      setIsSaving(true);
      await Forge.post("/api/email", { email }, { withCredentials: true });
      setOriginalEmail(email);
      // Display toast notification instead of setting state
      displaySuccessToast(t("SETTINGS$EMAIL_SAVED_SUCCESSFULLY"));
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(t("SETTINGS$FAILED_TO_SAVE_EMAIL"), error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleResendVerification = async () => {
    try {
      setIsResendingVerification(true);
      await Forge.put("/api/email/verify", {}, { withCredentials: true });
      // Display toast notification instead of setting state
      displaySuccessToast(t("SETTINGS$VERIFICATION_EMAIL_SENT"));
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(t("SETTINGS$FAILED_TO_RESEND_VERIFICATION"), error);
    } finally {
      setIsResendingVerification(false);
    }
  };

  const isEmailChanged = email !== originalEmail;
  const themeTitleId = useId();
  const themeDescriptionId = useId();

  const panelClass =
    "relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 backdrop-blur-xl p-6 shadow-[0_40px_120px_rgba(0,0,0,0.45)]";

  return (
    <div data-testid="user-settings-screen" className="flex flex-col">
      <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
        <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
          {isLoading ? (
            <div className="animate-pulse h-8 w-64 bg-black/50 rounded-xl" />
          ) : (
            <>
              {/* Email Settings */}
              <div className={panelClass}>
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0"
                >
                  <div className="absolute inset-y-0 left-1/2 w-1/2 bg-gradient-to-r from-brand-500/5 via-accent-500/3 to-transparent blur-2xl" />
                </div>
                <div className="relative z-[1]">
                  <h2 className="text-lg font-semibold text-foreground mb-4">
                    {t("SETTINGS$USER_EMAIL", "Email Settings")}
                  </h2>
                  <EmailInputSection
                    email={email}
                    onEmailChange={handleEmailChange}
                    onSaveEmail={handleSaveEmail}
                    onResendVerification={handleResendVerification}
                    isSaving={isSaving}
                    isResendingVerification={isResendingVerification}
                    isEmailChanged={isEmailChanged}
                    emailVerified={settings?.EMAIL_VERIFIED}
                    isEmailValid={isEmailValid}
                  >
                    {settings?.EMAIL_VERIFIED === false && (
                      <VerificationAlert />
                    )}
                  </EmailInputSection>
                </div>
              </div>

              {/* Theme Settings */}
              <div className={panelClass}>
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0"
                >
                  <div className="absolute inset-y-0 left-1/2 w-1/2 bg-gradient-to-r from-brand-500/5 via-accent-500/3 to-transparent blur-2xl" />
                </div>
                <div className="relative z-[1]">
                  <div
                    className="flex flex-col gap-3"
                    role="group"
                    aria-labelledby={themeTitleId}
                    aria-describedby={themeDescriptionId}
                  >
                    <h3
                      id={themeTitleId}
                      className="text-xl font-semibold text-foreground"
                    >
                      {t("userSettings.theme.title", "Theme Preference")}
                    </h3>
                    <p
                      id={themeDescriptionId}
                      className="text-sm text-foreground-secondary mb-2"
                    >
                      {t(
                        "userSettings.theme.description",
                        "Choose your preferred theme or follow your system settings",
                      )}
                    </p>
                    <ThemeToggle variant="dropdown" />
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default UserSettingsScreen;
