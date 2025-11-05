// Language mapping for file extensions
const LANGUAGE_MAP: Record<string, string> = {
  // JavaScript/TypeScript
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "typescript",

  // Web technologies
  html: "html",
  css: "css",
  json: "json",
  md: "markdown",

  // Configuration files
  yml: "yaml",
  yaml: "yaml",

  // Scripts
  sh: "bash",
  bash: "bash",
  dockerfile: "dockerfile",

  // Programming languages
  py: "python",
  rs: "rust",
  go: "go",
  java: "java",
  cpp: "cpp",
  cc: "cpp",
  cxx: "cpp",
  c: "c",
  rb: "ruby",
  php: "php",
  sql: "sql",
};

export const getLanguageFromPath = (path: string): string => {
  const extension = path.split(".").pop()?.toLowerCase();
  return extension ? LANGUAGE_MAP[extension] || "text" : "text";
};
