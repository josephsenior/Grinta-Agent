# Install dependencies and run Forge
# Install dependencies and run Forge

Write-Host "🔧 Installing Forge dependencies..." -ForegroundColor Cyan

# Add Poetry to PATH
$env:Path += ";$env:APPDATA\Python\Scripts"

# Change to project directory
Set-Location -Path $PSScriptRoot

# Try to install without updating lock file
Write-Host "📦 Installing dependencies from existing lock file..." -ForegroundColor Yellow
poetry install --no-root --sync

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Installation had issues, but continuing..." -ForegroundColor Yellow
}

# Install uvicorn directly if missing
Write-Host "`n🔍 Checking for uvicorn..." -ForegroundColor Cyan
poetry run python -c "import uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "📦 Installing uvicorn..." -ForegroundColor Yellow
    poetry add uvicorn[standard] --group dev
}

# Start backend
Write-Host "`n🚀 Starting backend server..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:Path += ';$env:APPDATA\Python\Scripts'; cd '$PSScriptRoot'; Write-Host '🚀 Backend Server (http://localhost:3000)' -ForegroundColor Green; poetry run python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Start frontend
Write-Host "🚀 Starting frontend server..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PSScriptRoot\frontend'; Write-Host '🚀 Frontend Server (http://localhost:5173)' -ForegroundColor Green; pnpm run dev"
) -WindowStyle Normal

Write-Host "`n✅ Servers starting!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "   Backend: http://localhost:3000" -ForegroundColor Cyan
