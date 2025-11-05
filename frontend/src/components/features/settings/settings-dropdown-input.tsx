import React, { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { OptionalTag } from "./optional-tag";
import { cn } from "#/utils/utils";
import { CustomDropdown } from "#/components/shared/inputs/custom-dropdown";

interface SettingsDropdownInputProps {
  testId: string;
  name: string;
  items: { key: React.Key; label: string }[];
  label?: ReactNode;
  wrapperClassName?: string;
  placeholder?: string;
  showOptionalTag?: boolean;
  isDisabled?: boolean;
  isLoading?: boolean;
  defaultSelectedKey?: string;
  selectedKey?: string;
  isClearable?: boolean;
  allowsCustomValue?: boolean;
  required?: boolean;
  error?: string;
  onSelectionChange?: (key: React.Key | null) => void;
  onInputChange?: (value: string) => void;
  defaultFilter?: (textValue: string, inputValue: string) => boolean;
}

export function SettingsDropdownInput({
  testId,
  label,
  wrapperClassName,
  name,
  items,
  placeholder,
  showOptionalTag,
  isDisabled,
  isLoading,
  defaultSelectedKey,
  selectedKey,
  isClearable,
  allowsCustomValue,
  required,
  error,
  onSelectionChange,
  onInputChange,
  defaultFilter,
}: SettingsDropdownInputProps) {
  const { t } = useTranslation();

  return (
    <label className={cn("flex flex-col gap-2.5", wrapperClassName)}>
      {label && (
        <div className="flex items-center gap-1">
          <span className="text-sm">{label}</span>
          {showOptionalTag && <OptionalTag />}
        </div>
      )}
      <CustomDropdown
        aria-label={typeof label === "string" ? label : name}
        data-testid={testId}
        placeholder={isLoading ? t("HOME$LOADING") : placeholder}
        disabled={isDisabled || isLoading}
        value={selectedKey as string}
        onSelectionChange={(key) => onSelectionChange?.(key)}
        onInputChange={onInputChange}
        isClearable={isClearable}
        allowsCustomValue={allowsCustomValue}
        isLoading={isLoading}
        loadingText={t("HOME$LOADING")}
        error={error}
        items={items.map((item) => ({
          key: item.key as string,
          label: item.label,
        }))}
      />
    </label>
  );
}
