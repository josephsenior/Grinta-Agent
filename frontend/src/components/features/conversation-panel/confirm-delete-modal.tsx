import React from "react";
import { useTranslation } from "react-i18next";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import { I18nKey } from "#/i18n/declaration";

interface ConfirmDeleteModalProps {
  onConfirm: () => void;
  onCancel: () => void;
}

function ModalHeader({
  title,
  description,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6 w-full text-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-16 h-16 rounded-3xl bg-error-500/10 flex items-center justify-center">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-error-500 to-error-500/80 flex items-center justify-center">
            <svg
              className="w-5 h-5 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"
                clipRule="evenodd"
              />
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>
        <h2 className="text-4xl font-extrabold leading-tight text-error-500">
          {title}
        </h2>
      </div>
      {description && (
        <div className="card-modern border-error-500/20 bg-error-500/5">
          <p className="text-base font-medium leading-relaxed">
            {description}
          </p>
        </div>
      )}
    </div>
  );
}
export function ConfirmDeleteModal({
  onConfirm,
  onCancel,
}: ConfirmDeleteModalProps) {
  const { t } = useTranslation();
  const confirmRef = React.useRef<HTMLButtonElement | null>(null);

  React.useEffect(() => {
    confirmRef.current?.focus();
  }, []);

  return (
    <ModalBackdrop onClose={onCancel}>
      <ModalBody className="items-center" width="medium">
        <div onClick={(e) => e.stopPropagation()} className="w-full max-w-2xl">
          <ModalHeader
            title={t(I18nKey.CONVERSATION$CONFIRM_DELETE)}
            description={t(I18nKey.CONVERSATION$DELETE_WARNING)}
          />
          <div className="mt-8 w-full space-y-4">
            <div className="flex flex-col sm:flex-row gap-3 w-full">
              <button
                ref={confirmRef}
                type="button"
                onClick={onConfirm}
                className="flex-1 px-8 py-4 rounded-2xl bg-error-500 text-white font-bold hover:bg-error-500/90 hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-error-500/50 transition-all duration-300"
                data-testid="confirm-button"
                aria-label={t(I18nKey.ACTION$CONFIRM)}
              >
                {t(I18nKey.ACTION$CONFIRM)}
              </button>
              <button
                type="button"
                onClick={onCancel}
                className="flex-1 px-8 py-4 rounded-2xl border-2 border-border text-foreground-secondary bg-background-tertiary hover:bg-background-tertiary/70 hover:border-border-hover hover:text-foreground transition-all duration-300"
                data-testid="cancel-button"
                aria-label={t(I18nKey.BUTTON$CANCEL)}
              >
                {t(I18nKey.BUTTON$CANCEL)}
              </button>
            </div>
          </div>
        </div>
      </ModalBody>
    </ModalBackdrop>
  );
}
