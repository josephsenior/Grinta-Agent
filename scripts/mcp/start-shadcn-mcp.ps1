<#!
.SYNOPSIS
  Starts the shadcn-ui MCP server via SuperGateway and keeps streaming logs.
.DESCRIPTION
  Ensures dependencies are installed, builds the local cloned repo if needed, then launches SuperGateway
  to expose the stdio MCP server as an SSE endpoint at http://localhost:8090/sse.
.PARAMETER Port
  Port to bind SuperGateway SSE endpoint (default 8090)
.PARAMETER Framework
  Framework to fetch (react|svelte|vue) passed through to the MCP server (default react)
.PARAMETER GitHubToken
  Personal access token to raise rate limits (optional)
.PARAMETER VerboseLogs
  Switch to enable MCP server debug logging
.EXAMPLE
  ./start-shadcn-mcp.ps1 -Port 8090 -Framework react -GitHubToken ghp_xxx
#>
param(
  [int]$Port = 8090,
  [ValidateSet('react','svelte','vue')] [string]$Framework = 'react',
  [string]$GitHubToken,
  [switch]$VerboseLogs
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$serverDir = Join-Path $repoRoot 'external/shadcn-ui-mcp-server'
if (-not (Test-Path $serverDir)) {
  Write-Error "Shadcn MCP server directory not found: $serverDir. Clone repo first."; exit 1
}

Push-Location $serverDir
try {
  if (-not (Test-Path 'node_modules')) {
    Write-Host '[setup] Installing dependencies...' -ForegroundColor Cyan
    npm install --no-audit --no-fund | Out-Null
  }
  if (-not (Test-Path 'build/index.js')) {
    Write-Host '[build] Building TypeScript sources...' -ForegroundColor Cyan
    npm run -s build | Out-Null
  }
}
finally { Pop-Location }

$envFlags = @()
if ($GitHubToken) { $env:SHADCN_MCP_GITHUB_TOKEN = $GitHubToken }
if ($VerboseLogs) { $env:MCP_DEBUG = '1' }

# Compose stdio command
$stdioCmd = "npx @jpisnice/shadcn-ui-mcp-server --framework $Framework" + ($GitHubToken ? ' --github-api-key *****' : '')
Write-Host "[run] Starting SuperGateway on port $Port wrapping: $stdioCmd" -ForegroundColor Green

# Note: we do not echo the full token for safety
if ($GitHubToken) { Write-Host '[info] GitHub token provided (redacted) – higher rate limits enabled.' -ForegroundColor Yellow }

# Start supergateway (assumes npx available in PATH)
# Using Start-Process so the user can keep terminal; -NoNewWindow to stay attached
$npxArgs = @('supergateway','--stdio',"npx @jpisnice/shadcn-ui-mcp-server --framework $Framework" ,'--port', "$Port")
if ($GitHubToken) {
  # pass token via env instead of CLI argument for privacy if server respects env var
  $env:GITHUB_PERSONAL_ACCESS_TOKEN = $GitHubToken
}

Write-Host "[run] Executing: npx $($npxArgs -join ' ')" -ForegroundColor DarkGray

# Direct invocation so we stream logs inline
npx @npxArgs
