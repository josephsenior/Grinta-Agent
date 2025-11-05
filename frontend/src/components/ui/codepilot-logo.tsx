import React from "react";
import { cn } from "#/utils/utils";

interface CodePilotLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  variant?: "icon" | "full" | "text";
}

const heightClasses = {
  sm: "h-6",
  md: "h-8", 
  lg: "h-12",
  xl: "h-16",
};

export function CodePilotLogo({ 
  className, 
  size = "md", 
  variant = "icon" 
}: CodePilotLogoProps) {
  const heightClass = heightClasses[size];

  if (variant === "text") {
    return (
      <span className="font-light text-white tracking-tight">
        Forge
      </span>
    );
  }

  // Both "icon" and "full" now use the actual logo image
  return (
    <img
      src="/forge-logo.png"
      alt="Forge"
      className={cn(heightClass, "w-auto", className)}
      draggable={false}
    />
  );
}

