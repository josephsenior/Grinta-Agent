<#
.SYNOPSIS
    Generate TypeScript types from OpenAPI spec (Windows PowerShell version)

.DESCRIPTION
    This script:
    1. Checks if backend is running
    2. Fetches the OpenAPI spec
    3. Generates TypeScript types
    4. Saves to frontend/src/types/api-generated.ts

.EXAMPLE
    .\scripts\generate-api-types.ps1
#>

Write-Host "🚀 Generating TypeScript types from OpenAPI spec..." -ForegroundColor Cyan

# Check if backend is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/monitoring/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "✅ Backend is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend not running. Please start it first:" -ForegroundColor Yellow
    Write-Host "   poetry run python -m Forge.server.listen" -ForegroundColor White
    exit 1
}

# Fetch OpenAPI spec
Write-Host "📥 Fetching OpenAPI spec from http://localhost:3000/openapi.json..." -ForegroundColor Cyan
try {
    $spec = Invoke-RestMethod -Uri "http://localhost:3000/openapi.json"
    $spec | ConvertTo-Json -Depth 100 | Out-File -Encoding UTF8 "$env:TEMP\forge-openapi.json"
    Write-Host "✅ OpenAPI spec fetched successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to fetch OpenAPI spec: $_" -ForegroundColor Red
    exit 1
}

# Check if openapi-typescript is installed
Set-Location frontend
if (!(Test-Path "node_modules\.bin\openapi-typescript.cmd")) {
    Write-Host "📦 Installing openapi-typescript..." -ForegroundColor Cyan
    npm install -D openapi-typescript
}

# Generate TypeScript types
Write-Host "🔨 Generating TypeScript types..." -ForegroundColor Cyan
try {
    npx openapi-typescript "$env:TEMP\forge-openapi.json" `
        --output src/types/api-generated.ts `
        --export-type `
        --path-params-as-types
    
    Write-Host "✅ TypeScript types generated successfully!" -ForegroundColor Green
    Write-Host "   → frontend/src/types/api-generated.ts" -ForegroundColor White
    Write-Host ""
    Write-Host "Usage in your code:" -ForegroundColor Cyan
    Write-Host "   import type { paths, components } from '#/types/api-generated';" -ForegroundColor White
    Write-Host "   type SettingsResponse = components['schemas']['GETSettingsModel'];" -ForegroundColor White
    Write-Host ""
    Write-Host "Done! 🎉" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to generate types: $_" -ForegroundColor Red
    exit 1
} finally {
    Set-Location ..
}

