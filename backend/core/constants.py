import os
from typing import Any

# Re-export enums and provider configs from dedicated modules.
# Consumers can continue to ``from backend.core.constants import ActionType``
# or migrate to ``from backend.core.enums import ActionType`` at their leisure.
from backend.core.enums import (  # noqa: F401
    ActionConfirmationStatus,
    ActionSecurityRisk,
    ActionType,
    AgentState,
    AppMode,
    CircuitState,
    ContentType,
    ErrorCategory,
    ErrorSeverity,
    EventSource,
    EventVersion,
    ExitReason,
    FileEditSource,
    FileReadSource,
    ObservationType,
    QuotaPlan,
    RecallType,
    RetryStrategy,
    RuntimeStatus,
)
from backend.core.providers import (  # noqa: F401
    DEFAULT_API_KEY_MIN_LENGTH,
    PROVIDER_CONFIGURATIONS,
    PROVIDER_FALLBACK_PATTERNS,
    PROVIDER_KEYWORD_PATTERNS,
    PROVIDER_PREFIX_PATTERNS,
    UNKNOWN_PROVIDER_CONFIG,
    VERIFIED_ANTHROPIC_MODELS,
    VERIFIED_MISTRAL_MODELS,
    VERIFIED_OPENAI_MODELS,
    VERIFIED_PROVIDERS,
    _LazyModelList,
)

"""Central location for Forge core constants."""

FORGE_DEFAULT_AGENT = "Orchestrator"
FORGE_MAX_ITERATIONS = 500  # Increased from 100 for complex tasks with dynamic iteration management

# Workspace constants
JWT_SECRET_FILE = ".jwt_secret"
DEFAULT_WORKSPACE_BASE = "~/.Forge"
DEFAULT_CONFIG_FILE = "config.toml"

# URL constants
GUIDE_URL = "https://docs.forge.dev/guide"
TROUBLESHOOTING_URL = "https://docs.forge.dev/usage/troubleshooting"

# Security constants
SECRET_PLACEHOLDER = "**********"

# Cache constants
SETTINGS_CACHE_TTL = 60  # seconds

# Timeout constants
GENERAL_TIMEOUT = 15
COMPLETION_TIMEOUT = 30.0

# Threshold constants
MAX_LINES_TO_EDIT = 300
IDLE_RECLAIM_SPIKE_THRESHOLD = 3
EVICTION_SPIKE_THRESHOLD = 1

# Runtime constants
MICROMAMBA_ENV_NAME = "Forge"
DEFAULT_PYTHON_PREFIX = [
    "/Forge/micromamba/bin/micromamba",
    "run",
    "-n",
    MICROMAMBA_ENV_NAME,
    "poetry",
    "run",
]
DEFAULT_MAIN_MODULE = "forge.runtime.action_execution_server"

# Storage constants
CONVERSATION_BASE_DIR = "sessions"

# Default configuration constants
DEFAULT_RUNTIME = "local"
DEFAULT_FILE_STORE = "local"
DEFAULT_CACHE_DIR = "/tmp/cache"
DEFAULT_CONVERSATION_MAX_AGE_SECONDS = 864000
DEFAULT_MAX_CONCURRENT_CONVERSATIONS = 3
DEFAULT_GIT_USER_NAME = "forge"
DEFAULT_GIT_USER_EMAIL = "Forge@forge.dev"
DEFAULT_LOG_FORMAT = "text"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_ENABLE_BROWSER = True
DEFAULT_ENABLE_DEFAULT_CONDENSER = True

# Sandbox defaults
DEFAULT_SANDBOX_TIMEOUT = 120
DEFAULT_SANDBOX_CLOSE_DELAY = 60
DEFAULT_SANDBOX_AUTO_LINT_ENABLED = True
DEFAULT_SANDBOX_REMOTE_RUNTIME_RESOURCE_FACTOR = 1.0
DEFAULT_SANDBOX_KEEP_RUNTIME_ALIVE = False
DEFAULT_SANDBOX_USE_HOST_NETWORK = False
DEFAULT_SANDBOX_FORCE_REBUILD_RUNTIME = False

# LLM defaults
DEFAULT_LLM_MODEL = "claude-sonnet-4-20250514"
DEFAULT_LLM_NUM_RETRIES = 5
DEFAULT_LLM_RETRY_MULTIPLIER = 8
DEFAULT_LLM_RETRY_MIN_WAIT = 8
DEFAULT_LLM_RETRY_MAX_WAIT = 64
DEFAULT_LLM_MAX_MESSAGE_CHARS = 30000
DEFAULT_LLM_TEMPERATURE = 0.0
DEFAULT_LLM_TOP_P = 1.0
DEFAULT_LLM_CORRECT_NUM = 5

# File upload configuration
DEFAULT_MAX_FILE_UPLOAD_SIZE_MB = 100
FILES_TO_IGNORE = [
    ".git/",
    ".DS_Store",
    "node_modules/",
    "__pycache__/",
    "lost+found/",
    ".vscode/",
    ".downloads/",
]

# Agent defaults
DEFAULT_AGENT_MEMORY_MAX_THREADS = 10
CURRENT_AGENT_CONFIG_SCHEMA_VERSION = "2025-11-14"
DEFAULT_AGENT_MEMORY_ENABLED = True
DEFAULT_AGENT_PROMPT_EXTENSIONS_ENABLED = True
DEFAULT_AGENT_BROWSING_ENABLED = True
DEFAULT_AGENT_VECTOR_MEMORY_ENABLED = False
DEFAULT_AGENT_HYBRID_RETRIEVAL_ENABLED = False
DEFAULT_AGENT_PROMPT_CACHING_ENABLED = True
DEFAULT_AGENT_AUTO_LINT_ENABLED = True
DEFAULT_AGENT_CONFIRM_ACTIONS = False
DEFAULT_AGENT_AUTO_RETRY_ON_ERROR = False
DEFAULT_AGENT_AUTONOMY_LEVEL = "balanced"
DEFAULT_AGENT_CMD_ENABLED = True
DEFAULT_AGENT_THINK_ENABLED = True
DEFAULT_AGENT_FINISH_ENABLED = True
DEFAULT_AGENT_CONDENSATION_REQUEST_ENABLED = False
DEFAULT_AGENT_EDITOR_ENABLED = True
DEFAULT_AGENT_LLM_EDITOR_ENABLED = False
DEFAULT_AGENT_ULTIMATE_EDITOR_ENABLED = False
DEFAULT_AGENT_HISTORY_TRUNCATION_ENABLED = True
DEFAULT_AGENT_PLAN_MODE_ENABLED = True
DEFAULT_AGENT_MCP_ENABLED = True
DEFAULT_AGENT_AUTO_PLANNING_ENABLED = True
DEFAULT_AGENT_PLANNING_COMPLEXITY_THRESHOLD = 3
DEFAULT_AGENT_REFLECTION_ENABLED = True
DEFAULT_AGENT_PLANNING_MIDDLEWARE_ENABLED = False
DEFAULT_AGENT_REFLECTION_MIDDLEWARE_ENABLED = False
DEFAULT_AGENT_REFLECTION_MAX_ATTEMPTS = 2
DEFAULT_AGENT_DYNAMIC_ITERATIONS_ENABLED = True
DEFAULT_AGENT_MIN_ITERATIONS = 20
DEFAULT_AGENT_COMPLEXITY_ITERATION_MULTIPLIER = 50.0
DEFAULT_AGENT_MAX_AUTONOMOUS_ITERATIONS = 0
DEFAULT_AGENT_STUCK_DETECTION_ENABLED = False
DEFAULT_AGENT_STUCK_THRESHOLD_ITERATIONS = 0
DEFAULT_AGENT_INTERNAL_TASK_TRACKER_ENABLED = True
DEFAULT_AGENT_SOM_VISUAL_BROWSING_ENABLED = False
DEFAULT_AGENT_SYSTEM_PROMPT_FILENAME = "system_prompt.j2"
DEFAULT_AGENT_CLI_MODE = False
DEFAULT_FORGE_MCP_CONFIG_CLS = "backend.core.config.mcp_config.ForgeMCPConfig"

# Server constants
API_VERSION_V1 = "v1"
CURRENT_API_VERSION = API_VERSION_V1
ENFORCE_API_VERSIONING = False
ROOM_KEY_TEMPLATE = "room_{sid}"
DEFAULT_SESSION_WAIT_TIME_BEFORE_CLOSE = 90
DEFAULT_SESSION_WAIT_TIME_BEFORE_CLOSE_INTERVAL = 5

# Quota and Plan constants (QuotaPlan enum in backend.core.enums)
DEFAULT_QUOTA_HOUR_WINDOW = 3600
DEFAULT_QUOTA_DAY_WINDOW = 86400
DEFAULT_QUOTA_MONTH_WINDOW = 2592000
QUOTA_EXEMPT_PATHS = {"/", "/health", "/api/health", "/api/monitoring/health"}
QUOTA_EXEMPT_PATH_PREFIXES = ["/assets"]


# Quota limits per plan (in USD)
FREE_PLAN_DAILY_LIMIT = 1.0
FREE_PLAN_MONTHLY_LIMIT = 20.0
FREE_PLAN_BURST_LIMIT = 0.5

PRO_PLAN_DAILY_LIMIT = 10.0
PRO_PLAN_MONTHLY_LIMIT = 200.0
PRO_PLAN_BURST_LIMIT = 5.0

ENTERPRISE_PLAN_DAILY_LIMIT = 100.0
ENTERPRISE_PLAN_MONTHLY_LIMIT = 2000.0
ENTERPRISE_PLAN_BURST_LIMIT = 50.0

# Circuit Breaker defaults (CircuitState enum in backend.core.enums)
DEFAULT_CIRCUIT_FAILURE_THRESHOLD = 5
DEFAULT_CIRCUIT_SUCCESS_THRESHOLD = 2
DEFAULT_CIRCUIT_TIMEOUT_SECONDS = 60

# Action execution constants
ROOT_GID = 0
SESSION_API_KEY_HEADER = "X-Session-API-Key"

# Logging constants
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]
DEBUG_LLM = os.getenv("DEBUG_LLM", "False").lower() in ["true", "1", "yes"]
DEBUG_LLM_PROMPT = os.getenv("DEBUG_LLM_PROMPT", "False").lower() in [
    "true",
    "1",
    "yes",
]
LOG_JSON = os.getenv("LOG_JSON", "True").lower() in [
    "true",
    "1",
    "yes",
]  # Default to JSON for production
LOG_JSON_LEVEL_KEY = os.getenv("LOG_JSON_LEVEL_KEY", "level")
# Enable OTEL log correlation when explicitly requested, defaulting to OTEL_ENABLED
OTEL_LOG_CORRELATION = os.getenv(
    "OTEL_LOG_CORRELATION", os.getenv("OTEL_ENABLED", "false")
).lower() in [
    "true",
    "1",
    "yes",
]
LOG_TO_FILE = os.getenv("LOG_TO_FILE", str(LOG_LEVEL == "DEBUG")).lower() in [
    "true",
    "1",
    "yes",
]
LOG_ALL_EVENTS = os.getenv("LOG_ALL_EVENTS", "False").lower() in ["true", "1", "yes"]
DEBUG_RUNTIME = os.getenv("DEBUG_RUNTIME", "False").lower() in ["true", "1", "yes"]

LOG_COLORS = {
    "ACTION": "green",
    "USER_ACTION": "light_red",
    "OBSERVATION": "yellow",
    "USER_OBSERVATION": "light_green",
    "DETAIL": "cyan",
    "ERROR": "red",
    "PLAN": "light_magenta",
}

# Tool name constants
EXECUTE_BASH_TOOL_NAME = "execute_bash"
STR_REPLACE_EDITOR_TOOL_NAME = "str_replace_editor"
BROWSER_TOOL_NAME = "browser"
FINISH_TOOL_NAME = "finish"
LLM_BASED_EDIT_TOOL_NAME = "edit_file"
TASK_TRACKER_TOOL_NAME = "task_tracker"

# Security Risk constants
SECURITY_RISK_DESC = "The LLM's assessment of the safety risk of this action. See the SECURITY_RISK_ASSESSMENT section in the system prompt for risk level definitions."
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]

# UX Presentation constants (ErrorSeverity, ErrorCategory enums in backend.core.enums)

# Browser Gym constants
BROWSER_EVAL_GET_GOAL_ACTION = "GET_EVAL_GOAL"
BROWSER_EVAL_GET_REWARDS_ACTION = "GET_EVAL_REWARDS"

# Command Output constants
CMD_OUTPUT_PS1_BEGIN = "\n###PS1JSON###\n"
CMD_OUTPUT_PS1_END = "\n###PS1END###"
MAX_CMD_OUTPUT_SIZE = 30000
DEFAULT_CMD_EXIT_CODE = -1
DEFAULT_CMD_PID = -1

# Runtime constants
BASH_TIMEOUT_MESSAGE_TEMPLATE = 'You may wait longer to see additional output by sending empty command \'\', send other commands to interact with the current process, send keys ("C-c", "C-z", "C-d") to interrupt/kill the previous command before sending your new command, or use the timeout parameter in execute_bash for future commands.'

# Condenser defaults
DEFAULT_CONDENSER_ATTENTION_WINDOW = 100
DEFAULT_BROWSER_CONDENSER_ATTENTION_WINDOW = 1
DEFAULT_CONDENSER_KEEP_FIRST = 1
DEFAULT_CONDENSER_MAX_EVENTS = 100
DEFAULT_CONDENSER_MAX_SIZE = 100
DEFAULT_CONDENSER_MAX_EVENT_LENGTH = 10000
DEFAULT_SMART_CONDENSER_MAX_SIZE = 200
DEFAULT_SMART_CONDENSER_KEEP_FIRST = 5
DEFAULT_SMART_CONDENSER_IMPORTANCE_THRESHOLD = 0.6
DEFAULT_SMART_CONDENSER_RECENCY_BONUS_WINDOW = 20

# Permissions defaults
DEFAULT_FILE_OPERATIONS_MAX_SIZE_MB = 50
DEFAULT_FILE_OPERATIONS_BLOCKED_PATHS = [
    "/etc/**",  # System config
    "/sys/**",  # System files
    "/proc/**",  # Process info
    "~/.ssh/**",  # SSH keys
    "**/.env",  # Environment files with secrets
    "**/id_rsa*",  # Private keys
    "**/id_ed25519*",  # Private keys
]
DEFAULT_GIT_PROTECTED_BRANCHES = ["main", "master", "production", "prod"]
DEFAULT_NETWORK_MAX_REQUESTS_PER_MINUTE = 60
DEFAULT_PACKAGE_ALLOWED_MANAGERS = ["pip", "npm", "yarn", "pnpm", "poetry", "cargo"]
DEFAULT_SHELL_BLOCKED_COMMANDS = [
    "rm -rf /",
    "mkfs",
    "dd",
    "fork",
    ":(){ :|:& };:",  # Fork bomb
]
DEFAULT_SHELL_CONFIRMATION_PATTERNS = [
    r"rm\s+-rf",
    r"sudo\s+",
    r"chmod\s+",
    r"chown\s+",
]
DEFAULT_BROWSER_MAX_PAGES = 10

# Runtime resource limits defaults
DEFAULT_RUNTIME_MAX_MEMORY_MB = 2048
DEFAULT_RUNTIME_MAX_CPU_PERCENT = 80.0
DEFAULT_RUNTIME_MAX_DISK_GB = 10
DEFAULT_RUNTIME_MAX_FILE_COUNT = 10000
DEFAULT_RUNTIME_MAX_NETWORK_REQUESTS_PER_MINUTE = 100
MAX_FILENAME_LENGTH = 255
MAX_PATH_LENGTH = 4096  # Maximum path length (POSIX limit)
MAX_FILE_SIZE_FOR_GIT_DIFF = 1024 * 1024

# Server and middleware constants
MIN_COMPRESS_SIZE = 1024  # 1KB
KNOWLEDGE_BASE_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
KNOWLEDGE_BASE_NAME_MAX_LENGTH = 200
KNOWLEDGE_BASE_DESCRIPTION_MAX_LENGTH = 1000
KNOWLEDGE_BASE_SEARCH_TOP_K_DEFAULT = 5
KNOWLEDGE_BASE_SEARCH_TOP_K_MAX = 100
KNOWLEDGE_BASE_RELEVANCE_THRESHOLD_DEFAULT = 0.7
CACHE_LONG = 31536000  # 1 year
CACHE_MEDIUM = 3600  # 1 hour
CACHE_SHORT = 300  # 5 minutes
CACHE_NONE = 0  # No cache

# MCP Client constants
DEFAULT_MCP_CACHE_TTL_SECONDS = 600
MAX_MCP_CACHE_ENTRY_BYTES = 5 * 1024 * 1024
MCP_CACHEABLE_TOOLS = {
    "list_components",
    "list_blocks",
    "get_component",
    "get_block",
    "get_component_metadata",
}

# Integration constants
MAX_GITHUB_BRANCHES = 5000
MAX_GITHUB_REPOS = 1000

# Whitespace handling defaults
DEFAULT_INDENT_SIZES = {
    "python": 4,
    "javascript": 2,
    "typescript": 2,
    "tsx": 2,
    "go": 1,  # Go uses tabs
    "rust": 4,
    "java": 4,
    "c": 4,
    "cpp": 4,
    "c_sharp": 4,
    "ruby": 2,
    "php": 4,
    "swift": 4,
    "kotlin": 4,
    "scala": 2,
    "json": 2,
    "yaml": 2,
    "html": 2,
    "css": 2,
}

# Storage defaults
DEFAULT_SECRETS_FILENAME = "user_secrets.json"

# All enum classes (ContentType, ActionType, AgentState, ObservationType,
# ExitReason, ActionConfirmationStatus, ActionSecurityRisk, AppMode,
# EventVersion, EventSource, FileEditSource, FileReadSource, RecallType,
# RetryStrategy, RuntimeStatus) are defined in backend.core.enums and
# re-exported above for backward compatibility.
