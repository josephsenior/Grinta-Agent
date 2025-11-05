import React, { ReactNode } from "react";
import EventLogger from "#/utils/event-logger";

/**
 * Decodes HTML entities in a string
 * @param text The text to decode
 * @returns The decoded text
 */
const decodeHtmlEntities = (text: string): string => {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = text;
  return textarea.value;
};

/**
 * Checks if a path is likely a directory
 * @param path The full path
 * @returns True if the path is likely a directory
 */
const isLikelyDirectory = (path: string): boolean => {
  if (!path) {
    return false;
  }
  // Check if path already ends with a slash
  if (path.endsWith("/") || path.endsWith("\\")) {
    return true;
  }
  // Check if path has no extension (simple heuristic)
  const lastPart = path.split(/[/\\]/).pop() || "";
  // If the last part has no dots, it's likely a directory
  return !lastPart.includes(".");
};

/**
 * Extracts the filename from a path
 * @param path The full path
 * @returns The filename (last part of the path)
 */
const extractFilename = (path: string): string => {
  if (!path) {
    return "";
  }
  // Handle both Unix and Windows paths
  const parts = path.split(/[/\\]/);
  const filename = parts[parts.length - 1];

  // Add trailing slash for directories
  if (isLikelyDirectory(path) && !filename.endsWith("/")) {
    return `${filename}/`;
  }

  return filename;
};

/**
 * Component that displays only the filename in the text but shows the full path on hover
 * Similar to MonoComponent but with path-specific functionality
 */
function PathComponent(props: { children?: ReactNode }) {
  const { children } = props;

  const processPath = (path: string, key?: React.Key) => {
    try {
      // First decode any HTML entities in the path
      const decodedPath = decodeHtmlEntities(path);
      // Extract the filename from the decoded path
      const filename = extractFilename(decodedPath);
      return (
        <span key={key} className="font-mono" title={decodedPath}>
          {filename}
        </span>
      );
    } catch (e) {
      // Just log the error without any message to avoid localization issues
      EventLogger.error(String(e));
      return (
        <span key={key} className="font-mono">
          {path}
        </span>
      );
    }
  };

  if (Array.isArray(children)) {
    const processedChildren = children.map((child, idx) => {
      const k = `path-${idx}`;
      if (typeof child === "string") {
        return processPath(child, k);
      }

      if (React.isValidElement(child)) {
        // Preserve existing key if provided, otherwise clone with a generated key
        return child.key != null
          ? child
          : React.cloneElement(child, { key: k });
      }

      // Fallback for other node types (number, boolean, etc.)
      return (
        <span key={k} className="font-mono">
          {String(child)}
        </span>
      );
    });

    return <strong className="font-mono">{processedChildren}</strong>;
  }

  if (typeof children === "string") {
    return <strong>{processPath(children)}</strong>;
  }

  return <strong className="font-mono">{children}</strong>;
}

export { PathComponent, isLikelyDirectory };
