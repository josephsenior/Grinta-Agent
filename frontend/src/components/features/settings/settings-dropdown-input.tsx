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
  const [currentKey, setCurrentKey] = React.useState(
    (selectedKey ?? defaultSelectedKey ?? "") as string,
  );

  React.useEffect(() => {
    if (typeof selectedKey === "string") {
      setCurrentKey(selectedKey);
    }
  }, [selectedKey]);

  React.useEffect(() => {
    if (selectedKey === undefined && typeof defaultSelectedKey === "string") {
      setCurrentKey(defaultSelectedKey);
    }
  }, [defaultSelectedKey, selectedKey]);

  const handleSelectionChange = (key: React.Key | null) => {
    if (typeof key === "string") {
      setCurrentKey(key);
    }
    onSelectionChange?.(key);
  };

  const handleInputChange = (value: string) => {
    if (!allowsCustomValue) {
      setCurrentKey(value);
    }
    onInputChange?.(value);
  };

  const dropdownValue = allowsCustomValue ? undefined : currentKey;

  return (
    <label className={cn("flex flex-col gap-2.5", wrapperClassName)}>
      {label && (
        <div className="flex items-center gap-1">
          <span className="text-sm font-medium text-foreground">{label}</span>
          {showOptionalTag && <OptionalTag />}
        </div>
      )}
      <CustomDropdown
        aria-label={typeof label === "string" ? label : name}
        data-testid={testId}
        name={name}
        value={dropdownValue}
        defaultValue={defaultSelectedKey as string | undefined}
        placeholder={isLoading ? t("HOME$LOADING") : placeholder}
        disabled={isDisabled || isLoading}
        onSelectionChange={handleSelectionChange}
        onInputChange={handleInputChange}
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
