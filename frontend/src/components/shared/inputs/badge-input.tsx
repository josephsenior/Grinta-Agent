import React from "react";
import { cn } from "#/utils/utils";
import { BrandBadge } from "../badge";
import XIcon from "#/icons/x.svg?react";

interface BadgeInputProps {
  name?: string;
  value: string[];
  placeholder?: string;
  onChange: (value: string[]) => void;
}

export function BadgeInput({
  name,
  value,
  placeholder,
  onChange,
}: BadgeInputProps) {
  const [inputValue, setInputValue] = React.useState("");

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // If pressing Backspace with empty input, remove the last badge
    if (e.key === "Backspace" && inputValue === "" && value.length > 0) {
      const newBadges = [...value];
      newBadges.pop();
      onChange(newBadges);
      return;
    }

    // If pressing Space or Enter with non-empty input, add a new badge
    const isSpaceOrEnter =
      e.key === " " ||
      e.key === "Space" ||
      e.key === "Spacebar" ||
      e.key === "Enter";
    if (isSpaceOrEnter && inputValue.trim() !== "") {
      e.preventDefault();
      const newBadge = inputValue.trim();
      onChange([...value, newBadge]);
      setInputValue("");
    }
  };

  const removeBadge = (indexToRemove: number) => {
    onChange(value.filter((_, index) => index !== indexToRemove));
  };

  return (
    <div
      className={cn(
        "bg-background-glass backdrop-blur-xl border border-border-glass rounded-xl w-full p-3 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary transition-all duration-200 focus-within:border-primary-500/50 focus-within:bg-primary-500/5 focus-within:shadow-lg focus-within:shadow-primary-500/10 hover:border-primary-500/30 hover:bg-primary-500/3",
        "flex flex-wrap items-center gap-2",
      )}
    >
      {value.map((badge, index) => (
        <div key={String(badge)}>
          <BrandBadge className="flex items-center gap-0.5 py-1 px-2.5 text-sm text-base font-semibold leading-[16px]">
            {badge}
            <button
              data-testid="remove-button"
              type="button"
              onClick={() => removeBadge(index)}
              className="cursor-pointer"
            >
              <XIcon width={14} height={14} color="#000000" />
            </button>
          </BrandBadge>
        </div>
      ))}
      <input
        data-testid={name || "badge-input"}
        name={name}
        value={inputValue}
        placeholder={value.length === 0 ? placeholder : ""}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        className="flex-grow outline-none bg-transparent"
      />
    </div>
  );
}
