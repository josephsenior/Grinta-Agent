// Handle file-icons-js with fallback for environments where it's not available
let fileIcons: unknown = null;
let fileIconsPromise: Promise<unknown> | null = null;

// Async loader for file-icons-js
const loadFileIcons = async (): Promise<unknown> => {
  if (fileIcons) return fileIcons;

  if (!fileIconsPromise) {
    fileIconsPromise = (async () => {
      try {
        // Try to load file-icons-js asynchronously
        if (typeof window !== "undefined") {
          // Check if already loaded on window
          // @ts-expect-error - fileIconsJs may be loaded on window
          if (window.fileIconsJs) {
            // @ts-expect-error - fileIconsJs may be loaded on window
            return window.fileIconsJs;
          }

          // Try dynamic import
          const module = await import("file-icons-js");
          return module.default || module;
        }
        // Server-side fallback using dynamic import
        const srvModule = await import("file-icons-js");
        return srvModule.default || srvModule;
      } catch (_err) {
        // file-icons-js not available; fall back to built-in icons silently
        return null;
      }
    })();
  }

  fileIcons = await fileIconsPromise;
  return fileIcons;
};

// Initialize on client side with logging
if (typeof window !== "undefined") {
  // Initialize loader on client; failures are handled by the loader itself.
  loadFileIcons().catch(() => {
    /* silently fallback to built-in icons */
  });
}

export interface FileIconProps {
  name: string;
  className?: string;
  size?: number;
}

/**
 * Get the appropriate file icon class for a given filename
 */
export function getFileIconClass(filename: string): string {
  if (!fileIcons) {
    return "default-icon";
  }
  try {
    if (
      typeof fileIcons === "object" &&
      fileIcons !== null &&
      "getClass" in (fileIcons as Record<string, unknown>)
    ) {
      const ic = fileIcons as Record<string, unknown> & {
        getClass?: (n: string) => string;
      };
      const iconClass = ic.getClass ? ic.getClass(filename) : undefined;
      return iconClass || "default-icon";
    }
    return "default-icon";
  } catch (_) {
    return "default-icon";
  }
}

/**
 * Get the appropriate file icon class for a given filename (async version)
 */
export async function getFileIconClassAsync(filename: string): Promise<string> {
  const icons = await loadFileIcons();
  if (!icons) {
    return "default-icon";
  }
  try {
    if (
      typeof icons === "object" &&
      icons !== null &&
      "getClass" in (icons as Record<string, unknown>)
    ) {
      const ic = icons as Record<string, unknown> & {
        getClass?: (n: string) => string;
      };
      const iconClass = ic.getClass ? ic.getClass(filename) : undefined;
      return iconClass || "default-icon";
    }
    return "default-icon";
  } catch (_) {
    return "default-icon";
  }
}

/**
 * Get the file icon class with color information
 */
export function getFileIconClassWithColor(filename: string): string {
  if (!fileIcons) {
    return "default-icon";
  }
  try {
    if (
      typeof fileIcons === "object" &&
      fileIcons !== null &&
      "getClassWithColor" in (fileIcons as Record<string, unknown>)
    ) {
      const ic = fileIcons as Record<string, unknown> & {
        getClassWithColor?: (n: string) => string;
      };
      const iconClassWithColor = ic.getClassWithColor
        ? ic.getClassWithColor(filename)
        : undefined;
      return iconClassWithColor || "default-icon";
    }
    return "default-icon";
  } catch (_) {
    return "default-icon";
  }
}

/**
 * Check if a file icon is available for the given filename
 */
export function hasFileIcon(filename: string): boolean {
  if (!fileIcons) {
    return false;
  }
  try {
    if (
      typeof fileIcons === "object" &&
      fileIcons !== null &&
      "getClass" in (fileIcons as Record<string, unknown>)
    ) {
      const ic = fileIcons as Record<string, unknown> & {
        getClass?: (n: string) => string;
      };
      const iconClass = ic.getClass ? ic.getClass(filename) : undefined;
      return !!iconClass && iconClass !== "default-icon";
    }
    return false;
  } catch (_) {
    return false;
  }
}

/**
 * Get file type category for better icon fallbacks
 */
export function getFileTypeCategory(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";

  // Programming languages
  const programmingLanguages = [
    "js",
    "ts",
    "jsx",
    "tsx",
    "py",
    "java",
    "c",
    "cpp",
    "cs",
    "php",
    "rb",
    "go",
    "rs",
    "swift",
    "kt",
    "scala",
    "dart",
    "r",
    "m",
    "h",
    "hpp",
    "cc",
    "cxx",
  ];

  // Web technologies
  const webTech = [
    "html",
    "htm",
    "css",
    "scss",
    "sass",
    "less",
    "vue",
    "svelte",
    "astro",
    "pug",
    "jade",
    "haml",
    "erb",
  ];

  // Configuration files
  const configFiles = [
    "json",
    "yaml",
    "yml",
    "toml",
    "ini",
    "cfg",
    "conf",
    "config",
    "env",
    "gitignore",
    "dockerignore",
    "editorconfig",
  ];

  // Documentation
  const documentation = [
    "md",
    "markdown",
    "rst",
    "txt",
    "rtf",
    "doc",
    "docx",
    "pdf",
  ];

  // Data files
  const dataFiles = ["csv", "xml", "sql", "db", "sqlite", "sqlite3"];

  // Images
  const images = [
    "png",
    "jpg",
    "jpeg",
    "gif",
    "svg",
    "ico",
    "bmp",
    "tiff",
    "webp",
    "avif",
  ];

  // Archives
  const archives = ["zip", "tar", "gz", "bz2", "xz", "7z", "rar"];

  if (programmingLanguages.includes(ext)) return "programming";
  if (webTech.includes(ext)) return "web";
  if (configFiles.includes(ext)) return "config";
  if (documentation.includes(ext)) return "documentation";
  if (dataFiles.includes(ext)) return "data";
  if (images.includes(ext)) return "image";
  if (archives.includes(ext)) return "archive";

  return "unknown";
}

/**
 * Get fallback icon based on file type category
 */
export function getFallbackIcon(category: string): string {
  const fallbackIcons: Record<string, string> = {
    programming: "📝",
    web: "🌐",
    config: "⚙️",
    documentation: "📄",
    data: "📊",
    image: "🖼️",
    archive: "📦",
    unknown: "📄",
  };

  return fallbackIcons[category] || "📄";
}

/**
 * Enhanced file icon component that handles both file-icons-js and fallbacks
 */
export function getFileIconInfo(filename: string): {
  iconClass: string;
  iconClassWithColor: string;
  fallback: string;
  category: string;
} {
  const category = getFileTypeCategory(filename);
  const iconClass = getFileIconClass(filename);
  const iconClassWithColor = getFileIconClassWithColor(filename);
  const fallback = getFallbackIcon(category);

  return {
    iconClass,
    iconClassWithColor,
    fallback,
    category,
  };
}
