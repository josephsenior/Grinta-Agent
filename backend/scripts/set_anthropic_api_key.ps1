<#
Set your Anthropic API key persistently for the current user.
This script uses `Read-Host -AsSecureString` to avoid echoing secrets.
It writes the variable persistently using `setx` and also updates the current session.

Usage (PowerShell):
    .\scripts\set_anthropic_api_key.ps1

Note: After setting, restart Docker containers to pick up the new key.
#>

# Prompt securely
$secureKey = Read-Host -Prompt "Enter your Anthropic API key (starts with sk-ant-)" -AsSecureString
if (-not $secureKey) {
    Write-Host "No key entered — aborting." -ForegroundColor Yellow
    exit 1
}

# Convert SecureString to plain text in a safe local-only variable
$ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

# Persist for the current user (will be available in new shells)
setx ANTHROPIC_API_KEY $plainKey | Out-Null

# Also set for current session
$env:ANTHROPIC_API_KEY = $plainKey

Write-Host ""
Write-Host "✅ ANTHROPIC_API_KEY set successfully!" -ForegroundColor Green
Write-Host "   - Persisted for your user account" -ForegroundColor Cyan
Write-Host "   - Available in current session" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔄 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Restart Docker containers: docker-compose restart" -ForegroundColor White
Write-Host "   2. Or update docker-compose.yml to pass the env var" -ForegroundColor White
Write-Host ""

# Zero-out sensitive variable
$plainKey = $null
$secureKey = $null

exit 0

