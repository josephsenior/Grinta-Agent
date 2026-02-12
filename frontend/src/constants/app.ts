export const ASSET_FILE_TYPES = [
  ".png",
  ".jpg",
  ".jpeg",
  ".bmp",
  ".gif",
  ".pdf",
  ".mp4",
  ".webm",
  ".ogg",
];

export const JSON_VIEW_THEME = {
  base00: "transparent", // background
  base01: "#2d2d2d", // lighter background
  base02: "#4e4e4e", // selection background
  base03: "#6c6c6c", // comments, invisibles
  base04: "#969896", // dark foreground
  base05: "#d9d9d9", // default foreground
  base06: "#e8e8e8", // light foreground
  base07: "#ffffff", // light background
  base08: "#ff5370", // variables, red
  base09: "#f78c6c", // integers, orange
  base0A: "#ffcb6b", // booleans, yellow
  base0B: "#c3e88d", // strings, green
  base0C: "#89ddff", // support, cyan
  base0D: "#82aaff", // functions, blue
  base0E: "#c792ea", // keywords, purple
  base0F: "#ff5370", // deprecated, red
};

export const DOCUMENTATION_URL = {
  HOME: "https://docs.forge.dev",
  GUIDE: "https://docs.forge.dev/guide",
  GETTING_STARTED: "https://docs.forge.dev/usage/getting-started",
  TROUBLESHOOTING: "https://docs.forge.dev/usage/troubleshooting",
  LLMS: "https://docs.forge.dev/usage/llms",
  LOCAL_SETUP_API_KEY: "https://docs.forge.dev/usage/local-setup#getting-an-api-key",
  MCP: "https://docs.forge.dev/usage/mcp",
  CLOUD_API: "https://docs.forge.dev/usage/cloud/cloud-api",
  CLOUD_Forge_CLOUD: "https://docs.forge.dev/usage/cloud/Forge-cloud",
  HEALTH_CHECK: "https://docs.forge.dev/api-reference/health-check",
  BLOG: "https://www.forge.dev/blog",
  PROMPTING: {
    BEST_PRACTICES: "https://docs.forge.dev/usage/prompting/prompting-best-practices",
    PLAYBOOKS_REPO: "https://docs.forge.dev/usage/prompting/playbooks-repo",
    REPOSITORY_SETUP: "https://docs.forge.dev/usage/prompting/repository#setup-script",
  },
  HOW_TO: {
    HEADLESS_MODE: "https://docs.forge.dev/usage/how-to/headless-mode",
    CLI_MODE: "https://docs.forge.dev/usage/how-to/cli-mode",
  },
  GITHUB: {
    INSTALLATION: "https://docs.forge.dev/usage/cloud/github-installation#working-on-github-issues-and-pull-requests-using-Forge",
  },
  PLAYBOOKS: {
    PLAYBOOKS_OVERVIEW:
      "https://docs.forge.dev/usage/prompting/playbooks-overview",
    ORGANIZATION_AND_USER_PLAYBOOKS:
      "https://docs.forge.dev/usage/prompting/playbooks-org",
  },
};

export const MAX_FILE_SIZE_MB = 3;
export const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024; // 3MB maximum file size
export const MAX_TOTAL_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024; // 3MB maximum total size for all files combined

// Toast duration constants
export const TOAST_SUCCESS_DURATION = 3000;
export const TOAST_MIN_DURATION_SUCCESS = 5000;
export const TOAST_MIN_DURATION_ERROR = 4000;
export const TOAST_DETAILED_ERROR_MIN_DURATION = 8000;
export const TOAST_MAX_DURATION = 10000;
export const TOAST_WORDS_PER_MINUTE = 200;
export const TOAST_CHARS_PER_WORD = 5;
export const TOAST_BUFFER_FACTOR = 1.5;

// Verified Models and Providers
export const VERIFIED_PROVIDERS = ["openai", "anthropic", "gemini", "xai"];

export const VERIFIED_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "claude-3-5-sonnet-20241022",
  "claude-3-7-sonnet-20250219",
  "gemini-1.5-pro",
  "gemini-1.5-flash",
  "grok-beta",
];

export const VERIFIED_OPENAI_MODELS = [
  "gpt-5-2025-08-07",
  "gpt-5-mini-2025-08-07",
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-4.1",
  "gpt-4.1-2025-04-14",
  "o3",
  "o3-2025-04-16",
  "o4-mini",
  "o4-mini-2025-04-16",
  "codex-mini-latest",
];

export const VERIFIED_ANTHROPIC_MODELS = [
  "claude-3-5-sonnet-20240620",
  "claude-3-5-sonnet-20241022",
  "claude-3-5-haiku-20241022",
  "claude-3-7-sonnet-20250219",
];

export const DEFAULT_FORGE_MODEL = "claude-3-5-sonnet-20241022";

