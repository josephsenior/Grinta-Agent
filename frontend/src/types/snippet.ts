/**
 * TypeScript types for code snippets
 */

export enum SnippetLanguage {
  PYTHON = "python",
  JAVASCRIPT = "javascript",
  TYPESCRIPT = "typescript",
  JAVA = "java",
  CSHARP = "csharp",
  CPP = "cpp",
  C = "c",
  GO = "go",
  RUST = "rust",
  PHP = "php",
  RUBY = "ruby",
  SWIFT = "swift",
  KOTLIN = "kotlin",
  SCALA = "scala",
  R = "r",
  MATLAB = "matlab",
  SQL = "sql",
  HTML = "html",
  CSS = "css",
  SCSS = "scss",
  LESS = "less",
  JSON = "json",
  YAML = "yaml",
  XML = "xml",
  MARKDOWN = "markdown",
  BASH = "bash",
  SHELL = "shell",
  POWERSHELL = "powershell",
  DOCKERFILE = "dockerfile",
  MAKEFILE = "makefile",
  GRAPHQL = "graphql",
  LUA = "lua",
  PERL = "perl",
  HASKELL = "haskell",
  ELIXIR = "elixir",
  CLOJURE = "clojure",
  VUE = "vue",
  REACT = "react",
  ANGULAR = "angular",
  PLAINTEXT = "plaintext",
}

export enum SnippetCategory {
  ALGORITHM = "algorithm",
  DATA_STRUCTURE = "data_structure",
  DATABASE = "database",
  API = "api",
  UI_COMPONENT = "ui_component",
  UTILITY = "utility",
  CONFIGURATION = "configuration",
  TEST = "test",
  DEBUGGING = "debugging",
  ERROR_HANDLING = "error_handling",
  AUTHENTICATION = "authentication",
  VALIDATION = "validation",
  PERFORMANCE = "performance",
  SECURITY = "security",
  BOILERPLATE = "boilerplate",
  CUSTOM = "custom",
}

export interface CodeSnippet {
  id: string;
  title: string;
  description?: string;
  language: SnippetLanguage;
  category: SnippetCategory;
  code: string;
  tags: string[];
  is_favorite: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  dependencies: string[];
  related_snippets: string[];
  source_url?: string;
  license?: string;
}

export interface CreateSnippetRequest {
  title: string;
  description?: string;
  language?: SnippetLanguage;
  category?: SnippetCategory;
  code: string;
  tags?: string[];
  is_favorite?: boolean;
  dependencies?: string[];
  source_url?: string;
  license?: string;
}

export interface UpdateSnippetRequest {
  title?: string;
  description?: string;
  language?: SnippetLanguage;
  category?: SnippetCategory;
  code?: string;
  tags?: string[];
  is_favorite?: boolean;
  dependencies?: string[];
  source_url?: string;
  license?: string;
}

export interface SearchSnippetsRequest {
  query?: string;
  language?: SnippetLanguage;
  category?: SnippetCategory;
  tags?: string[];
  is_favorite?: boolean;
  limit?: number;
  offset?: number;
}

export interface SnippetStats {
  total_snippets: number;
  snippets_by_language: Record<string, number>;
  snippets_by_category: Record<string, number>;
  total_favorites: number;
  most_used_snippets: [string, number][];
  total_tags: number;
}

export interface SnippetCollection {
  name: string;
  description?: string;
  version: string;
  snippets: CodeSnippet[];
  metadata: Record<string, unknown>;
}

export const SNIPPET_LANGUAGE_LABELS: Record<SnippetLanguage, string> = {
  [SnippetLanguage.PYTHON]: "Python",
  [SnippetLanguage.JAVASCRIPT]: "JavaScript",
  [SnippetLanguage.TYPESCRIPT]: "TypeScript",
  [SnippetLanguage.JAVA]: "Java",
  [SnippetLanguage.CSHARP]: "C#",
  [SnippetLanguage.CPP]: "C++",
  [SnippetLanguage.C]: "C",
  [SnippetLanguage.GO]: "Go",
  [SnippetLanguage.RUST]: "Rust",
  [SnippetLanguage.PHP]: "PHP",
  [SnippetLanguage.RUBY]: "Ruby",
  [SnippetLanguage.SWIFT]: "Swift",
  [SnippetLanguage.KOTLIN]: "Kotlin",
  [SnippetLanguage.SCALA]: "Scala",
  [SnippetLanguage.R]: "R",
  [SnippetLanguage.MATLAB]: "MATLAB",
  [SnippetLanguage.SQL]: "SQL",
  [SnippetLanguage.HTML]: "HTML",
  [SnippetLanguage.CSS]: "CSS",
  [SnippetLanguage.SCSS]: "SCSS",
  [SnippetLanguage.LESS]: "LESS",
  [SnippetLanguage.JSON]: "JSON",
  [SnippetLanguage.YAML]: "YAML",
  [SnippetLanguage.XML]: "XML",
  [SnippetLanguage.MARKDOWN]: "Markdown",
  [SnippetLanguage.BASH]: "Bash",
  [SnippetLanguage.SHELL]: "Shell",
  [SnippetLanguage.POWERSHELL]: "PowerShell",
  [SnippetLanguage.DOCKERFILE]: "Dockerfile",
  [SnippetLanguage.MAKEFILE]: "Makefile",
  [SnippetLanguage.GRAPHQL]: "GraphQL",
  [SnippetLanguage.LUA]: "Lua",
  [SnippetLanguage.PERL]: "Perl",
  [SnippetLanguage.HASKELL]: "Haskell",
  [SnippetLanguage.ELIXIR]: "Elixir",
  [SnippetLanguage.CLOJURE]: "Clojure",
  [SnippetLanguage.VUE]: "Vue",
  [SnippetLanguage.REACT]: "React (JSX)",
  [SnippetLanguage.ANGULAR]: "Angular",
  [SnippetLanguage.PLAINTEXT]: "Plain Text",
};

export const SNIPPET_CATEGORY_LABELS: Record<SnippetCategory, string> = {
  [SnippetCategory.ALGORITHM]: "Algorithm",
  [SnippetCategory.DATA_STRUCTURE]: "Data Structure",
  [SnippetCategory.DATABASE]: "Database",
  [SnippetCategory.API]: "API",
  [SnippetCategory.UI_COMPONENT]: "UI Component",
  [SnippetCategory.UTILITY]: "Utility",
  [SnippetCategory.CONFIGURATION]: "Configuration",
  [SnippetCategory.TEST]: "Test",
  [SnippetCategory.DEBUGGING]: "Debugging",
  [SnippetCategory.ERROR_HANDLING]: "Error Handling",
  [SnippetCategory.AUTHENTICATION]: "Authentication",
  [SnippetCategory.VALIDATION]: "Validation",
  [SnippetCategory.PERFORMANCE]: "Performance",
  [SnippetCategory.SECURITY]: "Security",
  [SnippetCategory.BOILERPLATE]: "Boilerplate",
  [SnippetCategory.CUSTOM]: "Custom",
};
