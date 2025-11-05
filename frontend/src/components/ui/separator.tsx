import * as React from "react";
import { cn } from "#/utils/utils";

export function Separator({
  className,
  orientation = "horizontal",
  id,
  title,
  style,
  role,
  tabIndex,
  onClick,
}: React.HTMLAttributes<HTMLDivElement> & {
  orientation?: "horizontal" | "vertical";
}) {
  return (
    <div
      id={id}
      title={title}
      role={role}
      tabIndex={tabIndex}
      onClick={onClick}
      style={style}
      className={cn(
        "shrink-0 bg-background-tertiary/70",
        orientation === "horizontal" ? "h-px w-full" : "w-px h-full",
        className,
      )}
    />
  );
}
