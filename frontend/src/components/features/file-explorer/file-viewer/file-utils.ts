const LANGUAGE_MAP: Record<string, string> = {
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "typescript",
  py: "python",
  java: "java",
  cpp: "cpp",
  c: "c",
  cs: "csharp",
  php: "php",
  rb: "ruby",
  go: "go",
  rs: "rust",
  swift: "swift",
  kt: "kotlin",
  scala: "scala",
  html: "html",
  css: "css",
  scss: "scss",
  sass: "sass",
  less: "less",
  json: "json",
  xml: "xml",
  yaml: "yaml",
  yml: "yaml",
  toml: "toml",
  ini: "ini",
  env: "bash",
  sh: "bash",
  bash: "bash",
  zsh: "bash",
  fish: "bash",
  ps1: "powershell",
  bat: "batch",
  cmd: "batch",
  md: "markdown",
  txt: "plaintext",
  sql: "sql",
  dockerfile: "dockerfile",
  gitignore: "gitignore",
  gitattributes: "gitattributes",
};

const BINARY_EXTENSIONS = new Set([
  "jpg",
  "jpeg",
  "png",
  "gif",
  "svg",
  "webp",
  "ico",
  "bmp",
  "tiff",
  "mp4",
  "avi",
  "mov",
  "wmv",
  "flv",
  "webm",
  "mkv",
  "mpg",
  "mpeg",
  "mp3",
  "wav",
  "flac",
  "aac",
  "ogg",
  "wma",
  "pdf",
  "doc",
  "docx",
  "xls",
  "xlsx",
  "ppt",
  "pptx",
  "zip",
  "rar",
  "7z",
  "tar",
  "gz",
  "bz2",
  "exe",
  "dll",
  "so",
  "dylib",
  "bin",
]);

export function getFileExtension(filePath: string): string {
  return filePath.split(".").pop()?.toLowerCase() ?? "";
}

export function getLanguageFromPath(filePath: string): string {
  const ext = getFileExtension(filePath);
  return LANGUAGE_MAP[ext] ?? "plaintext";
}

export function isBinaryFile(filePath: string): boolean {
  const ext = getFileExtension(filePath);
  return BINARY_EXTENSIONS.has(ext);
}

export function getViewerState({
  isLoading,
  isBinary,
  editing,
}: {
  isLoading: boolean;
  isBinary: boolean;
  editing: boolean;
}): "loading" | "binary" | "editing" | "preview" {
  if (isLoading) {
    return "loading";
  }

  if (isBinary) {
    return "binary";
  }

  if (editing) {
    return "editing";
  }

  return "preview";
}
