interface PasswordRequirementsProps {
  password: string;
}

interface Requirement {
  check: (password: string) => boolean;
  label: string;
}

const requirements: Requirement[] = [
  {
    check: (pwd) => pwd.length >= 8,
    label: "At least 8 characters",
  },
  {
    check: (pwd) => /[a-z]/.test(pwd) && /[A-Z]/.test(pwd),
    label: "Uppercase and lowercase letters",
  },
  {
    check: (pwd) => /[0-9]/.test(pwd),
    label: "At least one number",
  },
];

export function PasswordRequirements({ password }: PasswordRequirementsProps) {
  return (
    <div className="text-xs text-white/60 space-y-1">
      {requirements.map((req, index) => {
        const isValid = req.check(password);
        return (
          <p key={index} className={isValid ? "text-success-500" : ""}>
            {isValid ? "✓" : "○"} {req.label}
          </p>
        );
      })}
    </div>
  );
}
