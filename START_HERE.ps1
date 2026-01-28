# ============================================
# FORGE - Quick Start Script
# ============================================
# Run this script in PowerShell to start Forge
# Make sure you have internet access!

Write-Host "🚀 Starting Forge..." -ForegroundColor Cyan
Write-Host ""

# Add Poetry to PATH
$env:Path += ";$env:APPDATA\Python\Scripts"

# Change to project directory
Set-Location -Path $PSScriptRoot

# Step 1: Update lock file and install dependencies
Write-Host "📦 Step 1: Installing dependencies..." -ForegroundColor Yellow
poetry lock --no-update
poetry install --no-root

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Write-Host "Please check your internet connection and try again." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ Dependencies installed!" -ForegroundColor Green
Write-Host ""

# Step 2: Start backend server
Write-Host "🚀 Step 2: Starting backend server..." -ForegroundColor Yellow
Write-Host "   Backend will be available at: http://localhost:3000" -ForegroundColor Cyan

$backendWindow = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:Path += ';$env:APPDATA\Python\Scripts'; cd '$PSScriptRoot'; Write-Host '🚀 Backend Server' -ForegroundColor Green; Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow; poetry run python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload"
) -WindowStyle Normal -PassThru

# Wait for backend to start
Start-Sleep -Seconds 5

# Step 3: Start frontend server
Write-Host "🚀 Step 3: Starting frontend server..." -ForegroundColor Yellow
Write-Host "   Frontend will be available at: http://localhost:5173" -ForegroundColor Cyan

$frontendWindow = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PSScriptRoot\frontend'; Write-Host '🚀 Frontend Server' -ForegroundColor Green; Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow; pnpm run dev"
) -WindowStyle Normal -PassThru

Write-Host ""
Write-Host "✅ Both servers are starting!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Access the application:" -ForegroundColor Cyan
Write-Host "   • Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   • Backend API: http://localhost:3000/api" -ForegroundColor White
Write-Host "   • API Docs: http://localhost:3000/docs" -ForegroundColor White
Write-Host ""
Write-Host "💡 Two PowerShell windows opened - one for backend, one for frontend" -ForegroundColor Yellow
Write-Host "   Close those windows or press Ctrl+C to stop the servers" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this window (servers will keep running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
