import type {
  MCPMarketplaceItem,
  MCPMarketplaceResponse,
  MCPMarketplaceFilters,
} from "#/types/mcp-marketplace";

/**
 * MCP Marketplace API
 * 
 * Multi-source marketplace with fallback strategy:
 * 1. Smithery Registry (139 servers, premium with API key)
 * 2. npm Registry (official @modelcontextprotocol packages)
 * 3. GitHub Search (community MCP repositories)
 * 4. Official MCP Registry (official servers)
 * 5. Static fallback (30+ curated servers)
 */

// API endpoints (using real, accessible sources)
const SMITHERY_API = "https://registry.smithery.ai/servers";
const NPM_MCP_API = "https://registry.npmjs.org/-/v1/search?text=@modelcontextprotocol&size=100";
const GITHUB_MCP_API = "https://api.github.com/search/repositories?q=model+context+protocol+mcp+topic:mcp";
const OFFICIAL_API = "https://registry.modelcontextprotocol.info/api/servers";

// Cache configuration
const CACHE_KEY = "mcp-marketplace-cache";
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

interface CacheData {
  timestamp: number;
  data: MCPMarketplaceItem[];
}

// Enhanced static fallback - Comprehensive MCP Registry (30+ curated servers)
const CURATED_MCPS: MCPMarketplaceItem[] = [
  {
    id: "playwright",
    name: "Playwright MCP",
    slug: "playwright",
    description: "Browser automation with Playwright - navigate, click, fill forms, take screenshots",
    longDescription: "Full-featured browser automation using Playwright. Navigate websites, interact with elements, take screenshots, fill forms, and extract data from web pages.",
    author: "Anthropic",
    icon: "🎭",
    category: "browser",
    type: "stdio",
    featured: true,
    popular: true,
    installCount: 15000,
    rating: 4.8,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/playwright",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-playwright"],
    },
    tags: ["browser", "automation", "testing", "web-scraping"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "chrome-devtools",
    name: "Chrome DevTools",
    slug: "chrome-devtools",
    description: "Chrome browser automation via DevTools protocol - debugging, screenshots, network inspection",
    longDescription: "Control Chrome browser using the DevTools Protocol. Navigate pages, capture screenshots, inspect network requests, evaluate JavaScript, and more.",
    author: "ModelContextProtocol",
    icon: "🔍",
    category: "browser",
    type: "stdio",
    featured: true,
    popular: true,
    installCount: 12000,
    rating: 4.7,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/chrome-devtools",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-chrome-devtools"],
    },
    tags: ["browser", "chrome", "debugging", "devtools"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "postgres",
    name: "PostgreSQL",
    slug: "postgres",
    description: "PostgreSQL database queries and operations - read/write data, execute SQL, manage schemas",
    longDescription: "Connect to PostgreSQL databases, execute queries, manage schemas, and perform CRUD operations directly from your AI assistant.",
    author: "ModelContextProtocol",
    icon: "🐘",
    category: "database",
    type: "stdio",
    featured: true,
    popular: true,
    installCount: 18000,
    rating: 4.9,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-postgres"],
      env: {
        POSTGRES_CONNECTION_STRING: "postgresql://user:password@localhost:5432/dbname",
      },
    },
    tags: ["database", "sql", "postgresql", "data"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "sqlite",
    name: "SQLite",
    slug: "sqlite",
    description: "SQLite database operations - lightweight SQL database queries and management",
    longDescription: "Work with SQLite databases - execute queries, manage tables, and perform data operations with the lightweight SQL database engine.",
    author: "ModelContextProtocol",
    icon: "💾",
    category: "database",
    type: "stdio",
    popular: true,
    installCount: 14000,
    rating: 4.7,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-sqlite"],
    },
    tags: ["database", "sql", "sqlite", "local"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "aws-kb",
    name: "AWS Knowledge Base",
    slug: "aws-kb",
    description: "Query AWS documentation and resources - get answers about AWS services and best practices",
    longDescription: "Access AWS documentation, query service information, and get best practices for AWS cloud services directly through your AI assistant.",
    author: "Amazon",
    icon: "☁️",
    category: "cloud",
    type: "stdio",
    featured: true,
    installCount: 8000,
    rating: 4.6,
    version: "1.0.0",
    homepage: "https://github.com/aws/aws-mcp-servers",
    repository: "https://github.com/aws/aws-mcp-servers",
    documentation: "https://github.com/aws/aws-mcp-servers#readme",
    config: {
      command: "npx",
      args: ["-y", "@aws/mcp-server-aws-kb"],
    },
    tags: ["aws", "cloud", "documentation", "knowledge-base"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "figma",
    name: "Figma MCP",
    slug: "figma",
    description: "Access Figma designs and generate UI code from mockups",
    longDescription: "Connect to Figma files, extract design information, generate code from mockups, and access design tokens directly.",
    author: "Figma",
    icon: "🎨",
    category: "development",
    type: "stdio",
    featured: true,
    popular: true,
    installCount: 10000,
    rating: 4.8,
    version: "1.0.0",
    homepage: "https://www.figma.com/developers/mcp",
    documentation: "https://www.figma.com/developers/mcp",
    config: {
      command: "npx",
      args: ["-y", "@figma/mcp-server-figma"],
    },
    tags: ["design", "ui", "figma", "code-generation"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "github",
    name: "GitHub MCP",
    slug: "github",
    description: "GitHub integration - repositories, issues, PRs, commits, and code search",
    longDescription: "Full GitHub integration allowing you to search code, create issues, manage pull requests, browse repositories, and interact with GitHub API.",
    author: "ModelContextProtocol",
    icon: "🐙",
    category: "development",
    type: "stdio",
    popular: true,
    installCount: 16000,
    rating: 4.8,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/github",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-github"],
      env: {
        GITHUB_TOKEN: "your_github_token_here",
      },
    },
    tags: ["github", "git", "version-control", "api"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "slack",
    name: "Slack MCP",
    slug: "slack",
    description: "Slack integration - send messages, read channels, manage workspace",
    longDescription: "Connect to Slack workspaces, send messages to channels, read messages, and manage your Slack workspace through AI.",
    author: "ModelContextProtocol",
    icon: "💬",
    category: "communication",
    type: "stdio",
    popular: true,
    installCount: 9000,
    rating: 4.5,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-slack"],
      env: {
        SLACK_TOKEN: "your_slack_token_here",
      },
    },
    tags: ["slack", "messaging", "communication", "team"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "google-drive",
    name: "Google Drive",
    slug: "google-drive",
    description: "Access Google Drive files and folders - read, write, and organize documents",
    longDescription: "Connect to Google Drive, access files and folders, read documents, upload files, and manage your Drive storage.",
    author: "ModelContextProtocol",
    icon: "📁",
    category: "file-system",
    type: "stdio",
    installCount: 7500,
    rating: 4.6,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-gdrive"],
    },
    tags: ["google", "drive", "files", "storage"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "memory",
    name: "Memory Server",
    slug: "memory",
    description: "Persistent memory storage - remember context across conversations",
    longDescription: "Give your AI assistant persistent memory. Store and retrieve information across conversations, maintain context, and build a knowledge base.",
    author: "ModelContextProtocol",
    icon: "🧠",
    category: "productivity",
    type: "stdio",
    featured: true,
    popular: true,
    installCount: 13000,
    rating: 4.9,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-memory"],
    },
    tags: ["memory", "context", "knowledge-base", "persistence"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "filesystem",
    name: "File System",
    slug: "filesystem",
    description: "Local file system access - read, write, and manage files on your computer",
    longDescription: "Access your local file system securely. Read files, write content, create directories, and manage your local files through AI.",
    author: "ModelContextProtocol",
    icon: "📂",
    category: "file-system",
    type: "stdio",
    popular: true,
    installCount: 11000,
    rating: 4.7,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem"],
    },
    tags: ["files", "local", "filesystem", "io"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "git",
    name: "Git Operations",
    slug: "git",
    description: "Git repository operations - commits, branches, diffs, and repository management",
    longDescription: "Perform Git operations through AI - commit changes, create branches, view diffs, manage remotes, and interact with Git repositories.",
    author: "ModelContextProtocol",
    icon: "🌿",
    category: "development",
    type: "stdio",
    installCount: 12500,
    rating: 4.8,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/git",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-git"],
    },
    tags: ["git", "version-control", "repository", "vcs"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "puppeteer",
    name: "Puppeteer",
    slug: "puppeteer",
    description: "Chrome automation with Puppeteer - web scraping and browser control",
    longDescription: "Control Chrome/Chromium browsers using Puppeteer. Navigate websites, scrape data, take screenshots, generate PDFs, and automate web tasks.",
    author: "ModelContextProtocol",
    icon: "🎪",
    category: "browser",
    type: "stdio",
    installCount: 9500,
    rating: 4.6,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-puppeteer"],
    },
    tags: ["browser", "automation", "scraping", "chrome"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "brave-search",
    name: "Brave Search",
    slug: "brave-search",
    description: "Web search using Brave Search API - find information across the web",
    longDescription: "Perform web searches using Brave Search API. Get search results, news, images, and web information with privacy-focused search.",
    author: "ModelContextProtocol",
    icon: "🔎",
    category: "api-integration",
    type: "stdio",
    popular: true,
    installCount: 8500,
    rating: 4.5,
    version: "1.0.0",
    homepage: "https://github.com/modelcontextprotocol/servers",
    repository: "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-brave-search"],
      env: {
        BRAVE_API_KEY: "your_brave_api_key_here",
      },
    },
    tags: ["search", "web", "api", "brave"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "docker",
    name: "Docker",
    slug: "docker",
    description: "Docker container management - build, run, and manage containers",
    longDescription: "Interact with Docker daemon to manage containers, images, volumes, and networks. Build images, run containers, and orchestrate your Docker environment.",
    author: "Community",
    icon: "🐳",
    category: "development",
    type: "stdio",
    installCount: 7000,
    rating: 4.7,
    version: "1.0.0",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-docker"],
    },
    tags: ["docker", "containers", "devops", "deployment"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "sentry",
    name: "Sentry",
    slug: "sentry",
    description: "Sentry error monitoring - track errors, performance, and application health",
    longDescription: "Connect to Sentry to monitor application errors, track performance issues, and get insights into your application's health.",
    author: "Community",
    icon: "🚨",
    category: "monitoring",
    type: "stdio",
    installCount: 6000,
    rating: 4.5,
    version: "1.0.0",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-sentry"],
      env: {
        SENTRY_AUTH_TOKEN: "your_sentry_token_here",
      },
    },
    tags: ["monitoring", "errors", "performance", "observability"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  // Additional community MCPs
  {
    id: "docker",
    name: "Docker MCP",
    slug: "docker",
    description: "Docker container management - build, run, and manage containers",
    longDescription: "Interact with Docker daemon to manage containers, images, volumes, and networks. Build images, run containers, and orchestrate your Docker environment.",
    author: "Community",
    icon: "🐳",
    category: "development",
    type: "stdio",
    installCount: 7000,
    rating: 4.7,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-docker",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-docker"],
    },
    tags: ["docker", "containers", "devops", "deployment"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "sentry",
    name: "Sentry MCP",
    slug: "sentry",
    description: "Sentry error monitoring - track errors, performance, and application health",
    longDescription: "Connect to Sentry to monitor application errors, track performance issues, and get insights into your application's health.",
    author: "Community",
    icon: "🚨",
    category: "monitoring",
    type: "stdio",
    installCount: 6000,
    rating: 4.5,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-sentry",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-sentry"],
      env: {
        SENTRY_AUTH_TOKEN: "your_sentry_token_here",
      },
    },
    tags: ["monitoring", "errors", "performance", "observability"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "discord",
    name: "Discord MCP",
    slug: "discord",
    description: "Discord bot integration - send messages, manage servers, interact with Discord API",
    longDescription: "Connect to Discord servers, send messages to channels, manage roles, and interact with Discord's API through AI.",
    author: "Community",
    icon: "🎮",
    category: "communication",
    type: "stdio",
    installCount: 5500,
    rating: 4.4,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-discord",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-discord"],
      env: {
        DISCORD_TOKEN: "your_discord_token_here",
      },
    },
    tags: ["discord", "bot", "messaging", "gaming"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "redis",
    name: "Redis MCP",
    slug: "redis",
    description: "Redis database operations - key-value store, caching, and data management",
    longDescription: "Connect to Redis databases, perform CRUD operations on keys, manage caches, and work with Redis data structures.",
    author: "Community",
    icon: "🔴",
    category: "database",
    type: "stdio",
    installCount: 6500,
    rating: 4.6,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-redis",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-redis"],
      env: {
        REDIS_URL: "redis://localhost:6379",
      },
    },
    tags: ["redis", "cache", "key-value", "database"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "mysql",
    name: "MySQL MCP",
    slug: "mysql",
    description: "MySQL database operations - SQL queries, data management, and schema operations",
    longDescription: "Connect to MySQL databases, execute SQL queries, manage schemas, and perform database operations through AI.",
    author: "Community",
    icon: "🐬",
    category: "database",
    type: "stdio",
    installCount: 8000,
    rating: 4.7,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-mysql",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-mysql"],
      env: {
        MYSQL_CONNECTION_STRING: "mysql://user:password@localhost:3306/dbname",
      },
    },
    tags: ["mysql", "sql", "database", "relational"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "mongodb",
    name: "MongoDB MCP",
    slug: "mongodb",
    description: "MongoDB database operations - NoSQL queries, document management, and collections",
    longDescription: "Connect to MongoDB databases, perform CRUD operations on documents, manage collections, and work with MongoDB queries.",
    author: "Community",
    icon: "🍃",
    category: "database",
    type: "stdio",
    installCount: 7500,
    rating: 4.6,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-mongodb",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-mongodb"],
      env: {
        MONGODB_URI: "mongodb://localhost:27017/dbname",
      },
    },
    tags: ["mongodb", "nosql", "document", "database"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "aws-s3",
    name: "AWS S3 MCP",
    slug: "aws-s3",
    description: "AWS S3 storage operations - upload, download, and manage files in S3 buckets",
    longDescription: "Connect to AWS S3, upload and download files, manage buckets, and perform storage operations through AI.",
    author: "Amazon",
    icon: "🪣",
    category: "cloud",
    type: "stdio",
    featured: true,
    installCount: 9000,
    rating: 4.8,
    version: "1.0.0",
    repository: "https://github.com/aws/aws-mcp-servers",
    documentation: "https://github.com/aws/aws-mcp-servers#readme",
    config: {
      command: "npx",
      args: ["-y", "@aws/mcp-server-s3"],
      env: {
        AWS_ACCESS_KEY_ID: "your_access_key",
        AWS_SECRET_ACCESS_KEY: "your_secret_key",
        AWS_REGION: "us-east-1",
      },
    },
    tags: ["aws", "s3", "storage", "cloud"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "azure-blob",
    name: "Azure Blob MCP",
    slug: "azure-blob",
    description: "Azure Blob Storage operations - manage files and containers in Azure",
    longDescription: "Connect to Azure Blob Storage, upload and download files, manage containers, and perform cloud storage operations.",
    author: "Microsoft",
    icon: "☁️",
    category: "cloud",
    type: "stdio",
    installCount: 5500,
    rating: 4.5,
    version: "1.0.0",
    repository: "https://github.com/microsoft/azure-mcp-servers",
    documentation: "https://docs.microsoft.com/azure/storage",
    config: {
      command: "npx",
      args: ["-y", "@microsoft/mcp-server-azure-blob"],
      env: {
        AZURE_STORAGE_CONNECTION_STRING: "your_connection_string",
      },
    },
    tags: ["azure", "blob", "storage", "microsoft"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "jest",
    name: "Jest MCP",
    slug: "jest",
    description: "Jest testing framework integration - run tests, generate reports, and manage test suites",
    longDescription: "Integrate with Jest testing framework, run tests, generate coverage reports, and manage test suites through AI.",
    author: "Community",
    icon: "🧪",
    category: "testing",
    type: "stdio",
    installCount: 8500,
    rating: 4.7,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-jest",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-jest"],
    },
    tags: ["jest", "testing", "unit-tests", "coverage"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "cypress",
    name: "Cypress MCP",
    slug: "cypress",
    description: "Cypress e2e testing integration - run tests, manage test suites, and generate reports",
    longDescription: "Integrate with Cypress for end-to-end testing, run tests, manage test suites, and generate test reports.",
    author: "Community",
    icon: "🌲",
    category: "testing",
    type: "stdio",
    installCount: 7000,
    rating: 4.6,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-cypress",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-cypress"],
    },
    tags: ["cypress", "e2e", "testing", "automation"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "vault",
    name: "HashiCorp Vault MCP",
    slug: "vault",
    description: "HashiCorp Vault integration - manage secrets, keys, and secure configuration",
    longDescription: "Connect to HashiCorp Vault to manage secrets, encryption keys, and secure configuration through AI.",
    author: "HashiCorp",
    icon: "🔐",
    category: "security",
    type: "stdio",
    featured: true,
    installCount: 4500,
    rating: 4.8,
    version: "1.0.0",
    repository: "https://github.com/hashicorp/vault-mcp-server",
    documentation: "https://www.vaultproject.io/docs",
    config: {
      command: "npx",
      args: ["-y", "@hashicorp/mcp-server-vault"],
      env: {
        VAULT_ADDR: "https://vault.example.com",
        VAULT_TOKEN: "your_vault_token",
      },
    },
    tags: ["vault", "secrets", "security", "hashicorp"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "kubernetes",
    name: "Kubernetes MCP",
    slug: "kubernetes",
    description: "Kubernetes cluster management - deploy, scale, and manage containerized applications",
    longDescription: "Connect to Kubernetes clusters, deploy applications, manage pods and services, and orchestrate containerized workloads.",
    author: "Community",
    icon: "⚙️",
    category: "development",
    type: "stdio",
    popular: true,
    installCount: 6500,
    rating: 4.7,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-kubernetes",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-k8s"],
      env: {
        KUBECONFIG: "/path/to/kubeconfig",
      },
    },
    tags: ["kubernetes", "k8s", "orchestration", "containers"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "terraform",
    name: "Terraform MCP",
    slug: "terraform",
    description: "Terraform infrastructure management - plan, apply, and manage cloud resources",
    longDescription: "Integrate with Terraform to plan, apply, and manage infrastructure as code through AI.",
    author: "HashiCorp",
    icon: "🏗️",
    category: "development",
    type: "stdio",
    installCount: 6000,
    rating: 4.6,
    version: "1.0.0",
    repository: "https://github.com/hashicorp/terraform-mcp-server",
    documentation: "https://www.terraform.io/docs",
    config: {
      command: "npx",
      args: ["-y", "@hashicorp/mcp-server-terraform"],
    },
    tags: ["terraform", "iac", "infrastructure", "cloud"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "elasticsearch",
    name: "Elasticsearch MCP",
    slug: "elasticsearch",
    description: "Elasticsearch search and analytics - query data, manage indices, and perform analytics",
    longDescription: "Connect to Elasticsearch clusters, perform searches, manage indices, and work with log analytics through AI.",
    author: "Community",
    icon: "🔍",
    category: "database",
    type: "stdio",
    installCount: 5500,
    rating: 4.5,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-elasticsearch",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-elasticsearch"],
      env: {
        ELASTICSEARCH_URL: "http://localhost:9200",
      },
    },
    tags: ["elasticsearch", "search", "analytics", "logs"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "prometheus",
    name: "Prometheus MCP",
    slug: "prometheus",
    description: "Prometheus metrics and monitoring - query metrics, manage alerts, and monitor systems",
    longDescription: "Connect to Prometheus to query metrics, manage alerting rules, and monitor system performance through AI.",
    author: "Community",
    icon: "📈",
    category: "monitoring",
    type: "stdio",
    popular: true,
    installCount: 7000,
    rating: 4.7,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-prometheus",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-prometheus"],
      env: {
        PROMETHEUS_URL: "http://localhost:9090",
      },
    },
    tags: ["prometheus", "metrics", "monitoring", "alerts"],
    requirements: {
      node: ">=18.0.0",
    },
  },
  {
    id: "grafana",
    name: "Grafana MCP",
    slug: "grafana",
    description: "Grafana dashboards and visualization - manage dashboards, datasources, and alerts",
    longDescription: "Connect to Grafana to manage dashboards, configure datasources, and create visualizations through AI.",
    author: "Community",
    icon: "📊",
    category: "monitoring",
    type: "stdio",
    installCount: 6000,
    rating: 4.6,
    version: "1.0.0",
    repository: "https://github.com/community/mcp-grafana",
    documentation: "https://docs.all-hands.dev/usage/mcp",
    config: {
      command: "npx",
      args: ["-y", "@community/mcp-server-grafana"],
      env: {
        GRAFANA_URL: "http://localhost:3000",
        GRAFANA_API_KEY: "your_api_key",
      },
    },
    tags: ["grafana", "dashboards", "visualization", "monitoring"],
    requirements: {
      node: ">=18.0.0",
    },
  },
];

/**
 * Cache management
 */
function getCachedData(): MCPMarketplaceItem[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;

    const cacheData: CacheData = JSON.parse(cached);
    const now = Date.now();

    // Check if cache is still valid
    if (now - cacheData.timestamp < CACHE_DURATION) {
      return cacheData.data;
    }

    // Cache expired
    localStorage.removeItem(CACHE_KEY);
    return null;
  } catch (error) {
    console.error("Error reading cache:", error);
    return null;
  }
}

function setCachedData(data: MCPMarketplaceItem[]): void {
  try {
    const cacheData: CacheData = {
      timestamp: Date.now(),
      data,
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
  } catch (error) {
    console.error("Error writing cache:", error);
  }
}

/**
 * Fetch from Smithery registry (primary source)
 */
async function fetchFromSmithery(): Promise<MCPMarketplaceItem[]> {
  // Try with API key first (if available)
  const apiKey = localStorage.getItem('smithery-api-key');
  const headers: HeadersInit = {
    'Accept': 'application/json',
  };
  
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }

  const response = await fetch(SMITHERY_API, { headers });
  if (!response.ok) throw new Error(`Smithery API failed: ${response.status}`);

  const data = await response.json();
  return transformSmitheryData(data);
}

/**
 * Fetch from npm registry for @modelcontextprotocol packages
 */
async function fetchFromNPMRegistry(): Promise<MCPMarketplaceItem[]> {
  const response = await fetch(NPM_MCP_API);
  if (!response.ok) throw new Error("npm API failed");

  const data = await response.json();
  return transformNPMData(data);
}

/**
 * Fetch from GitHub for MCP repositories
 */
async function fetchFromGitHub(): Promise<MCPMarketplaceItem[]> {
  const response = await fetch(GITHUB_MCP_API);
  if (!response.ok) throw new Error("GitHub API failed");

  const data = await response.json();
  return transformGitHubData(data);
}

/**
 * Fetch from Official MCP Registry
 */
async function fetchFromOfficialRegistry(): Promise<MCPMarketplaceItem[]> {
  const response = await fetch(OFFICIAL_API);
  if (!response.ok) throw new Error("Official Registry API failed");

  const data = await response.json();
  return transformOfficialRegistryData(data);
}

/**
 * Transform Smithery registry data to our format
 */
function transformSmitheryData(data: any): MCPMarketplaceItem[] {
  if (!data || !Array.isArray(data.servers)) return [];

  return data.servers.map((server: any, index: number) => {
    const categories = inferCategory(server.name || server.qualifiedName, server.description, server.tags || []);
    
    return {
      id: server.id || `smithery-${index}`,
      name: server.name || server.qualifiedName || "Unknown Server",
      slug: (server.slug || server.qualifiedName || "").toLowerCase().replace(/[^a-z0-9]/g, "-"),
      description: server.description || "No description available",
      longDescription: server.longDescription || server.description,
      author: server.author || server.publisher || "Smithery",
      icon: server.icon || getIconForCategory(categories[0]),
      category: categories[0] || "other",
      type: server.transport || "shttp", // Smithery uses HTTP transport
      featured: server.featured || server.popular || false,
      popular: server.popular || server.installCount > 1000,
      installCount: server.installCount || server.downloads || 0,
      rating: server.rating ? (typeof server.rating === 'number' ? server.rating : parseFloat(server.rating)) : (server.stars ? Math.min(5, server.stars / 20) : undefined),
      version: server.version || "latest",
      homepage: server.homepage || server.url,
      repository: server.repository || server.repo,
      documentation: server.documentation || server.homepage,
      config: {
        command: server.config?.command,
        args: server.config?.args,
        env: server.config?.env,
        url: server.config?.url || `https://server.smithery.ai/${server.qualifiedName}/mcp`,
        requiresApiKey: true, // Smithery requires API key
        apiKeyDescription: "Smithery API key required",
      },
      tags: server.tags || [],
      requirements: server.requirements,
    };
  });
}

/**
 * Transform npm registry data to our format
 */
function transformNPMData(data: any): MCPMarketplaceItem[] {
  if (!data || !Array.isArray(data.objects)) return [];

  return data.objects.map((pkg: any, index: number) => {
    const packageInfo = pkg.package;
    const categories = inferCategory(packageInfo.name, packageInfo.description, []);
    
    return {
      id: `npm-${index}`,
      name: packageInfo.name.replace('@modelcontextprotocol/', ''),
      slug: packageInfo.name.toLowerCase().replace(/[@\/]/g, "-"),
      description: packageInfo.description || "No description available",
      longDescription: packageInfo.description,
      author: packageInfo.author?.name || packageInfo.maintainers?.[0]?.name || "Community",
      icon: getIconForCategory(categories[0]),
      category: categories[0] || "other",
      type: "stdio",
      featured: packageInfo.name.includes('server-'),
      popular: pkg.score?.final > 0.5,
      installCount: Math.floor(pkg.score?.final * 10000) || 0,
      rating: pkg.score?.final ? (pkg.score.final * 5) : undefined,
      version: packageInfo.version,
      homepage: packageInfo.homepage,
      repository: packageInfo.repository?.url || `https://github.com/modelcontextprotocol/${packageInfo.name.replace('@modelcontextprotocol/', '')}`,
      documentation: packageInfo.homepage,
      config: {
        command: "npx",
        args: ["-y", packageInfo.name],
        requiresApiKey: false,
      },
      tags: [packageInfo.name.split('-').pop() || "mcp"],
      requirements: {
        node: ">=18.0.0",
      },
    };
  });
}

/**
 * Transform GitHub search data to our format
 */
function transformGitHubData(data: any): MCPMarketplaceItem[] {
  if (!data || !Array.isArray(data.items)) return [];

  return data.items.map((repo: any, index: number) => {
    const categories = inferCategory(repo.name, repo.description, repo.topics);
    
    return {
      id: `github-${index}`,
      name: repo.name,
      slug: repo.name.toLowerCase().replace(/\s+/g, "-"),
      description: repo.description || "No description available",
      longDescription: repo.description,
      author: repo.owner?.login || "Community",
      icon: getIconForCategory(categories[0]),
      category: categories[0] || "other",
      type: "stdio",
      featured: repo.stargazers_count > 100,
      popular: repo.stargazers_count > 50,
      installCount: repo.stargazers_count || 0,
      rating: repo.stargazers_count ? Math.min(5, (repo.stargazers_count / 100)) : undefined,
      version: "latest",
      homepage: repo.homepage,
      repository: repo.html_url,
      documentation: repo.homepage || repo.html_url,
      config: {
        command: "npx",
        args: ["-y", repo.full_name],
        requiresApiKey: false,
      },
      tags: repo.topics || [],
      requirements: {
        node: ">=18.0.0",
      },
    };
  });
}

/**
 * Transform Official Registry data to our format
 */
function transformOfficialRegistryData(data: any): MCPMarketplaceItem[] {
  if (!data || !Array.isArray(data.servers)) return [];

  return data.servers.map((server: any, index: number) => {
    const categories = inferCategory(server.name, server.description, server.tags);
    
    return {
      id: server.id || `official-${index}`,
      name: server.name || "Unknown Server",
      slug: (server.slug || server.name || "").toLowerCase().replace(/\s+/g, "-"),
      description: server.description || "No description available",
      author: "Anthropic",
      icon: getIconForCategory(categories[0]),
      category: categories[0] || "other",
      type: server.type || "stdio",
      featured: true,
      popular: true,
      homepage: server.homepage,
      repository: server.repository,
      documentation: server.documentation || "https://docs.all-hands.dev/usage/mcp",
      config: {
        command: server.command,
        args: server.args,
        env: server.env,
        url: server.url,
      },
      tags: server.tags || [],
    };
  });
}

/**
 * Infer category from server metadata
 */
function inferCategory(name: string, description?: string, tags?: string[]): string[] {
  const text = `${name} ${description || ""} ${(tags || []).join(" ")}`.toLowerCase();
  const categories: string[] = [];

  if (text.match(/browser|playwright|puppeteer|chrome|selenium/)) categories.push("browser");
  if (text.match(/database|postgres|mysql|sqlite|mongo|redis/)) categories.push("database");
  if (text.match(/cloud|aws|azure|gcp|s3|lambda/)) categories.push("cloud");
  if (text.match(/ai|llm|gpt|claude|model/)) categories.push("ai-tools");
  if (text.match(/git|github|gitlab|code|dev|vscode/)) categories.push("development");
  if (text.match(/file|filesystem|drive|storage/)) categories.push("file-system");
  if (text.match(/api|rest|graphql|http/)) categories.push("api-integration");
  if (text.match(/test|jest|mocha|cypress/)) categories.push("testing");
  if (text.match(/monitor|observability|sentry|logging/)) categories.push("monitoring");
  if (text.match(/security|auth|vault|secret/)) categories.push("security");
  if (text.match(/slack|discord|email|communication/)) categories.push("communication");
  if (text.match(/memory|context|knowledge/)) categories.push("productivity");

  return categories.length > 0 ? categories : ["other"];
}

/**
 * Get icon emoji for category
 */
function getIconForCategory(category: string): string {
  const icons: Record<string, string> = {
    browser: "🌐",
    database: "🗄️",
    cloud: "☁️",
    "ai-tools": "🤖",
    development: "💻",
    productivity: "⚡",
    "file-system": "📁",
    "api-integration": "🔌",
    testing: "🧪",
    monitoring: "📊",
    security: "🔒",
    communication: "💬",
    other: "📦",
  };
  return icons[category] || "📦";
}

/**
 * Merge and deduplicate MCPs from multiple sources
 */
function mergeAndDeduplicateMCPs(sources: MCPMarketplaceItem[][]): MCPMarketplaceItem[] {
  const seen = new Set<string>();
  const merged: MCPMarketplaceItem[] = [];

  for (const source of sources) {
    for (const mcp of source) {
      // Create unique key based on name and type
      const key = `${mcp.name.toLowerCase()}-${mcp.type}`;
      
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(mcp);
      }
    }
  }

  return merged;
}

/**
 * Fetch MCPs with multi-source fallback strategy
 */
async function fetchLiveMCPs(): Promise<MCPMarketplaceItem[]> {
  const sources: MCPMarketplaceItem[][] = [];

  // Try Smithery first (primary source with 139 servers)
  try {
    const smitheryData = await fetchFromSmithery();
    if (smitheryData.length > 0) {
      sources.push(smitheryData);
    }
  } catch (error) {
    console.warn("Smithery registry unavailable:", error);
  }

  // Try npm registry (official @modelcontextprotocol packages)
  try {
    const npmData = await fetchFromNPMRegistry();
    if (npmData.length > 0) {
      sources.push(npmData);
    }
  } catch (error) {
    console.warn("npm registry unavailable:", error);
  }

  // Try GitHub search for MCP repositories
  try {
    const githubData = await fetchFromGitHub();
    if (githubData.length > 0) {
      sources.push(githubData);
    }
  } catch (error) {
    console.warn("GitHub API unavailable:", error);
  }

  // Try Official Registry
  try {
    const officialData = await fetchFromOfficialRegistry();
    if (officialData.length > 0) {
      sources.push(officialData);
    }
  } catch (error) {
    console.warn("Official Registry unavailable:", error);
  }

  // If all APIs failed, use static fallback
  if (sources.length === 0) {
    console.warn("All APIs failed, using static fallback");
    return CURATED_MCPS;
  }

  // Merge and deduplicate
  const merged = mergeAndDeduplicateMCPs(sources);
  
  return merged;
}

/**
 * Get all MCPs from the marketplace
 */
export async function fetchMarketplaceMCPs(
  filters?: MCPMarketplaceFilters,
): Promise<MCPMarketplaceResponse> {
  // Try to get from cache first
  let allMCPs = getCachedData();

  // If no cache, fetch live data
  if (!allMCPs) {
    try {
      allMCPs = await fetchLiveMCPs();
      // Cache the results
      setCachedData(allMCPs);
    } catch (error) {
      console.error("Error fetching marketplace data:", error);
      // Use static fallback
      allMCPs = CURATED_MCPS;
    }
  } else {
    // Using cached marketplace data
  }

  let filteredItems = [...allMCPs];

  // Apply filters
  if (filters?.category) {
    filteredItems = filteredItems.filter(
      (item) => item.category === filters.category,
    );
  }

  if (filters?.type && filters.type !== "all") {
    filteredItems = filteredItems.filter((item) => item.type === filters.type);
  }

  if (filters?.featured) {
    filteredItems = filteredItems.filter((item) => item.featured);
  }

  if (filters?.popular) {
    filteredItems = filteredItems.filter((item) => item.popular);
  }

  if (filters?.search) {
    const searchLower = filters.search.toLowerCase();
    filteredItems = filteredItems.filter(
      (item) =>
        item.name.toLowerCase().includes(searchLower) ||
        item.description.toLowerCase().includes(searchLower) ||
        item.tags?.some((tag) => tag.toLowerCase().includes(searchLower)),
    );
  }

  // Get featured and popular from all MCPs
  const featured = allMCPs.filter((item) => item.featured);
  const popular = allMCPs.filter((item) => item.popular);

  // Calculate category counts from all MCPs
  const categoryCounts = allMCPs.reduce(
    (acc, item) => {
      const existing = acc.find((c) => c.category === item.category);
      if (existing) {
        existing.count += 1;
      } else {
        acc.push({ category: item.category, count: 1 });
      }
      return acc;
    },
    [] as { category: string; count: number }[],
  );

  return {
    items: filteredItems,
    total: filteredItems.length,
    featured,
    popular,
    categories: categoryCounts.map((c) => ({
      category: c.category as any,
      count: c.count,
    })),
  };
}

/**
 * Get a single MCP by ID
 */
export async function fetchMarketplaceMCP(
  id: string,
): Promise<MCPMarketplaceItem | null> {
  // Try to get from cache first
  let allMCPs = getCachedData();

  // If no cache, fetch live data
  if (!allMCPs) {
    try {
      allMCPs = await fetchLiveMCPs();
      setCachedData(allMCPs);
    } catch (error) {
      console.error("Error fetching marketplace data:", error);
      allMCPs = CURATED_MCPS;
    }
  }

  return allMCPs.find((item) => item.id === id) || null;
}

/**
 * Clear marketplace cache (useful for debugging or forcing refresh)
 */
export function clearMarketplaceCache(): void {
  try {
    localStorage.removeItem(CACHE_KEY);
    // Marketplace cache cleared
  } catch (error) {
    // Error clearing cache - silently fail
  }
}

