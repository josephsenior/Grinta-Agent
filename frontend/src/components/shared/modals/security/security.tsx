import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { BaseModal } from "../base-modal/base-modal";

interface SecurityProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  securityAnalyzer: string;
}

function Security({ isOpen, onOpenChange, securityAnalyzer }: SecurityProps) {
  const { t } = useTranslation();

  const AnalyzerComponent = () => (
    <div className="flex items-center justify-center h-full text-foreground-secondary">
      {t(I18nKey.SECURITY$UNKNOWN_ANALYZER_LABEL)}
    </div>
  );

  return (
    <BaseModal
      isOpen={isOpen && !!securityAnalyzer}
      contentClassName="max-w-[80%] h-[80%]"
      bodyClassName="px-0 py-0 max-h-[100%]"
      onOpenChange={onOpenChange}
      title=""
    >
      <AnalyzerComponent />
    </BaseModal>
  );
}

export default Security;
