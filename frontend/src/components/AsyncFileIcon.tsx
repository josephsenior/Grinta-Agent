import React, { useState, useEffect } from "react";
import {
  getFileIconClassAsync,
  getFileTypeCategory,
  getFallbackIcon,
} from "../utils/file-icons";

interface AsyncFileIconProps {
  filename: string;
  className?: string;
  size?: number;
}

export const AsyncFileIcon: React.FC<AsyncFileIconProps> = ({
  filename,
  className = "",
  size = 16,
}) => {
  const [iconClass, setIconClass] = useState<string>("default-icon");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadIcon = async () => {
      try {
        setIsLoading(true);
        const classWithIcon = await getFileIconClassAsync(filename);

        if (isMounted) {
          setIconClass(classWithIcon);
        }
      } catch (error) {
        if (isMounted) {
          // Use fallback icon based on file type
          const category = getFileTypeCategory(filename);
          const fallback = getFallbackIcon(category);
          setIconClass("default-icon");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadIcon();

    return () => {
      isMounted = false;
    };
  }, [filename]);

  if (isLoading) {
    return (
      <div
        className={`inline-flex items-center justify-center ${className}`}
        style={{ width: size, height: size }}
      >
        <div className="w-3 h-3 border border-border border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <i
      className={`${iconClass} ${className}`}
      style={{ fontSize: size }}
      title={filename}
    />
  );
};
