# Run Forge - Complete Setup and Start Script
# This script adds Poetry to PATH, installs dependencies, and starts both servers

Write-Host "🚀 Forge Startup Script" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

# Add Poetry to PATH
$poetryPath = "$env:APPDATA\Python\Scripts"
if (Test-Path $poetryPath) {
    if ($env:Path -notlike "*$poetryPath*") {
        $env:Path += ";$poetryPath"
        Write-Host "✅ Added Poetry to PATH" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  Poetry not found. Please install it first:" -ForegroundColor Yellow
    Write-Host "   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python" -ForegroundColor Yellow
    exit 1
}

# Verify Poetry is available
try {
    $poetryVersion = poetry --version 2>&1
    Write-Host "✅ Poetry found: $poetryVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Poetry not accessible. Please add it to your PATH manually." -ForegroundColor Red
    Write-Host "   Add this to your PATH: $poetryPath" -ForegroundColor Yellow
    exit 1
}

# Change to project directory
Set-Location -Path $PSScriptRoot
Write-Host "`n📁 Working directory: $(Get-Location)" -ForegroundColor Cyan

# Check if dependencies are installed
Write-Host "`n🔍 Checking dependencies..." -ForegroundColor Cyan
$venvExists = Test-Path ".venv"
if (-not $venvExists) {
    Write-Host "📦 Installing dependencies with Poetry..." -ForegroundColor Yellow
    poetry install --no-root
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment exists" -ForegroundColor Green
}

# Start backend server in new window
Write-Host "`n🚀 Starting backend server..." -ForegroundColor Green
Write-Host "   Backend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   API Docs: http://localhost:3000/docs" -ForegroundColor Cyan

$backendScript = @"
`$env:Path += ';$env:APPDATA\Python\Scripts'
cd '$PSScriptRoot'
poetry run python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -WindowStyle Normal

# Wait a moment for backend to initialize
Start-Sleep -Seconds 3

# Start frontend server in new window
Write-Host "🚀 Starting frontend server..." -ForegroundColor Green
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Cyan

$frontendScript = @"
cd '$PSScriptRoot\frontend'
pnpm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript -WindowStyle Normal

Write-Host "`n✅ Both servers are starting in separate windows!" -ForegroundColor Green
Write-Host "`n📝 Access the application:" -ForegroundColor Cyan
Write-Host "   • Frontend (Dev): http://localhost:5173" -ForegroundColor White
Write-Host "   • Backend API: http://localhost:3000/api" -ForegroundColor White
Write-Host "   • API Documentation: http://localhost:3000/docs" -ForegroundColor White
Write-Host "`n💡 Tip: Close the server windows or press Ctrl+C in each to stop the servers" -ForegroundColor Yellow
