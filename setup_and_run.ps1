# Setup and Run Script for Forge
# This script checks dependencies and starts the servers

Write-Host "🔍 Checking Forge setup..." -ForegroundColor Cyan

# Check if Poetry is available
$poetryAvailable = Get-Command poetry -ErrorAction SilentlyContinue

if (-not $poetryAvailable) {
    Write-Host "⚠️  Poetry not found. Installing dependencies with pip..." -ForegroundColor Yellow
    
    # Try to install core dependencies
    Write-Host "Installing core dependencies..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    python -m pip install fastapi uvicorn python-socketio python-multipart
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies. Please install Poetry:" -ForegroundColor Red
        Write-Host "   Install: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python" -ForegroundColor Yellow
        Write-Host "   Then run: poetry install" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✅ Poetry found. Installing dependencies..." -ForegroundColor Green
    poetry install --no-root
}

# Check Python path setup
Write-Host "`n🔧 Setting up Python path..." -ForegroundColor Cyan
$env:PYTHONPATH = "$PSScriptRoot\backend;$env:PYTHONPATH"

# Start backend server
Write-Host "`n🚀 Starting backend server..." -ForegroundColor Green
Write-Host "   Backend will be available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop`n" -ForegroundColor Yellow

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; `$env:PYTHONPATH='$PSScriptRoot\backend'; python backend/scripts/dev/dev_server.py" -WindowStyle Normal

# Wait a moment for backend to start
Start-Sleep -Seconds 3

# Start frontend server
Write-Host "🚀 Starting frontend server..." -ForegroundColor Green
Write-Host "   Frontend will be available at: http://localhost:5173" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop`n" -ForegroundColor Yellow

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; pnpm run dev" -WindowStyle Normal

Write-Host "✅ Both servers are starting in separate windows!" -ForegroundColor Green
Write-Host "`n📝 Access the application at:" -ForegroundColor Cyan
Write-Host "   - Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   - Backend API: http://localhost:3000/api" -ForegroundColor White
Write-Host "   - API Docs: http://localhost:3000/docs" -ForegroundColor White
