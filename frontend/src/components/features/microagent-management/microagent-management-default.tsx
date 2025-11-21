import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

export function MicroagentManagementDefault() {
  const { t } = useTranslation();
  return (
    <div className="flex-1 flex flex-col h-full items-center justify-center">
      <div className="text-[#F9FBFE] text-xl font-bold pb-4">
        {t(I18nKey.MICROAGENT$READY_TO_ADD_GUIDE)}
      </div>
      <div className="text-white text-sm font-normal text-center max-w-[455px]">
        {t(I18nKey.MICROAGENT$FORGE_LEARN_REPOSITORIES)}
      </div>
    </div>
  );
}
