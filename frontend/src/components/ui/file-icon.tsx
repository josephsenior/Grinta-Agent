import React from "react";
import { getFileIconInfo } from "#/utils/file-icons";
import { cn } from "#/utils/utils";

export interface FileIconProps {
  filename: string;
  className?: string;
  size?: number;
  showFallback?: boolean;
  status?: string;
  "data-testid"?: string;
  "data-category"?: string;
  "data-status"?: string;
}

export function FileIcon({
  filename,
  className,
  size = 16,
  showFallback = true,
  status,
  "data-testid": dataTestId,
  "data-category": dataCategory,
  "data-status": dataStatus,
}: FileIconProps) {
  const { iconClass, iconClassWithColor, fallback, category } =
    getFileIconInfo(filename);

  // If we have a CSS class from file-icons-js, use it
  if (iconClass && iconClass !== "default-icon") {
    return (
      <div
        className={cn("file-icon inline-flex items-center justify-center", className)}
        data-category={dataCategory || category}
        data-status={dataStatus || status}
        style={{ width: size, height: size }}
        title={`${filename} (${category})`}
        data-testid={dataTestId}
      >
        <i
          className={iconClassWithColor || iconClass}
          style={{ fontSize: size, lineHeight: 1, display: 'inline-block' }}
          aria-hidden="true"
        />
      </div>
    );
  }

  // Fallback to emoji (always use fallback if file-icons-js not loaded)
  return (
    <div
      className={cn("file-icon inline-flex items-center justify-center", className)}
      data-category={dataCategory || category}
      data-status={dataStatus || status}
      style={{ width: size, height: size }}
      title={`${filename} (${category})`}
      data-testid={dataTestId}
    >
      <span
        className="text-center flex items-center justify-center"
        style={{ fontSize: size * 0.7, lineHeight: 1 }}
        aria-label={`${filename} icon`}
      >
        {fallback}
      </span>
    </div>
  );
}

export default FileIcon;
