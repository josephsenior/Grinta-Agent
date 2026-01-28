# Quick Fix: Install core dependencies and run Forge
# This bypasses Poetry lock file issues

Write-Host "🔧 Quick Fix: Installing core dependencies..." -ForegroundColor Cyan

# Add Poetry to PATH
$env:Path += ";$env:APPDATA\Python\Scripts"

Set-Location -Path $PSScriptRoot

# Install core dependencies directly with pip (bypassing Poetry lock issues)
Write-Host "`n📦 Installing core server dependencies..." -ForegroundColor Yellow

# Get Python executable from Poetry
$pythonExe = poetry env info --path 2>$null
if ($pythonExe) {
    $pythonExe = Join-Path $pythonExe "Scripts\python.exe"
} else {
    $pythonExe = "python"
}

# Install essential packages
$packages = @(
    "fastapi",
    "uvicorn[standard]",
    "python-socketio",
    "python-multipart",
    "starlette",
    "sse-starlette",
    "python-dotenv",
    "pydantic",
    "aiohttp",
    "requests"
)

Write-Host "Installing: $($packages -join ', ')" -ForegroundColor Gray
& $pythonExe -m pip install $packages --quiet

# Add backend to Python path and start server
Write-Host "`n🚀 Starting backend server..." -ForegroundColor Green
$env:PYTHONPATH = "$PSScriptRoot\backend"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:Path += ';$env:APPDATA\Python\Scripts'; `$env:PYTHONPATH='$PSScriptRoot\backend'; cd '$PSScriptRoot'; Write-Host '🚀 Backend Server' -ForegroundColor Green; Write-Host 'http://localhost:3000' -ForegroundColor Cyan; python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload"
) -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "🚀 Starting frontend server..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PSScriptRoot\frontend'; Write-Host '🚀 Frontend Server' -ForegroundColor Green; Write-Host 'http://localhost:5173' -ForegroundColor Cyan; pnpm run dev"
) -WindowStyle Normal

Write-Host "`n✅ Servers starting!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   Backend: http://localhost:3000" -ForegroundColor White
