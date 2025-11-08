import React from "react";
import { useTranslation } from "react-i18next";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import { I18nKey } from "#/i18n/declaration";
import logo from "#/assets/branding/logo1.png";

export function ReauthModal() {
  const { t } = useTranslation();

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
            {t(I18nKey.AUTH$LOGGING_BACK_IN)}
          </h1>
        </div>
      </ModalBody>
    </ModalBackdrop>
  );
}
