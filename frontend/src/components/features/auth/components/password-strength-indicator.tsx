interface PasswordStrengthIndicatorProps {
  strength: "weak" | "medium" | "strong";
}

const strengthConfig = {
  weak: {
    width: "w-1/3",
    bgColor: "bg-danger-500",
    textColor: "text-danger-500",
  },
  medium: {
    width: "w-2/3",
    bgColor: "bg-warning-500",
    textColor: "text-warning-500",
  },
  strong: {
    width: "w-full",
    bgColor: "bg-success-500",
    textColor: "text-success-500",
  },
};

export function PasswordStrengthIndicator({
  strength,
}: PasswordStrengthIndicatorProps) {
  const config = strengthConfig[strength];
  const label = strength.charAt(0).toUpperCase() + strength.slice(1);

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${config.bgColor} ${config.width}`}
        />
      </div>
      <span className={`text-xs font-medium ${config.textColor}`}>{label}</span>
    </div>
  );
}
