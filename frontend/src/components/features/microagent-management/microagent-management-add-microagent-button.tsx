import { useTranslation } from "react-i18next";
import { useDispatch, useSelector } from "react-redux";
import { I18nKey } from "#/i18n/declaration";
import {
  setAddMicroagentModalVisible,
  setSelectedRepository,
} from "#/state/microagent-management-slice";
import { RootState } from "#/store";
import { GitRepository } from "#/types/git";

interface MicroagentManagementAddMicroagentButtonProps {
  repository: GitRepository;
}

export function MicroagentManagementAddMicroagentButton({
  repository,
}: MicroagentManagementAddMicroagentButtonProps) {
  const { t } = useTranslation();

  const { addMicroagentModalVisible } = useSelector(
    (state: RootState) => state.microagentManagement,
  );

  const dispatch = useDispatch();

  const handleActivate = (
    e: React.MouseEvent<HTMLElement> | React.KeyboardEvent<HTMLElement>,
  ) => {
    // Stop propagation so parent accordion/button doesn't also toggle.
    // Tests render this inside another <button>, so we must not render a nested <button>.
    e.stopPropagation();
    dispatch(setAddMicroagentModalVisible(!addMicroagentModalVisible));
    dispatch(setSelectedRepository(repository));
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleActivate(e);
    }
  };

  return (
    <span
      role="button"
      tabIndex={0}
      onClick={handleActivate}
      onKeyDown={onKeyDown}
      className="translate-y-[-1px]"
      data-testid="add-microagent-button"
    >
      <span className="text-sm font-normal leading-5 text-[#8480FF] cursor-pointer hover:text-[#6C63FF] transition-colors duration-200">
        {t(I18nKey.COMMON$ADD_MICROAGENT)}
      </span>
    </span>
  );
}
