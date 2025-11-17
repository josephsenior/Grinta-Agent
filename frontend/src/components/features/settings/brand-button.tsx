import { cn } from "#/utils/utils";

interface BrandButtonProps {
  testId?: string;
  name?: string;
  variant: "primary" | "secondary" | "danger";
  type: React.ButtonHTMLAttributes<HTMLButtonElement>["type"];
  isDisabled?: boolean;
  className?: string;
  onClick?: () => void;
  startContent?: React.ReactNode;
}

export function BrandButton({
  testId,
  name,
  children,
  variant,
  type,
  isDisabled,
  className,
  onClick,
  startContent,
}: React.PropsWithChildren<BrandButtonProps>) {
  return (
    <button
      name={name}
      data-testid={testId}
      disabled={isDisabled}
      // The type is alreadt passed as a prop to the button component
      // eslint-disable-next-line react/button-has-type
      type={type}
      onClick={onClick}
      className={cn(
        "w-fit px-6 py-2.5 text-sm font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-all duration-200",
        variant === "primary" && "bg-white text-black hover:bg-white/90",
        variant === "secondary" &&
          "border border-white/20 bg-transparent text-foreground hover:bg-white/10",
        variant === "danger" && "bg-danger-500 text-white hover:bg-danger-600",
        startContent && "flex items-center justify-center gap-2",
        className,
      )}
    >
      {startContent}
      {children}
    </button>
  );
}
