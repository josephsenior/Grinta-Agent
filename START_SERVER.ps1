# ============================================
# START FORGE SERVERS - Complete Solution
# ============================================

Write-Host "🚀 Starting Forge Application..." -ForegroundColor Cyan
Write-Host ""

# Add Poetry to PATH
$env:Path += ";$env:APPDATA\Python\Scripts"

# Project root
$projectRoot = "C:\Users\GIGABYTE\Desktop\Forge"
Set-Location -Path $projectRoot

# Set PYTHONPATH to include backend directory
$env:PYTHONPATH = "$projectRoot\backend"

Write-Host "📁 Project: $projectRoot" -ForegroundColor Gray
Write-Host "🐍 PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Gray
Write-Host ""

# Verify forge module
Write-Host "🔍 Verifying setup..." -ForegroundColor Yellow
$testResult = poetry run python -c "import sys; sys.path.insert(0, r'$projectRoot\backend'); import forge; print('OK')" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Installing dependencies..." -ForegroundColor Yellow
    poetry install --no-root
}

# Start backend
Write-Host "`n🚀 Starting backend server..." -ForegroundColor Green
Write-Host "   URL: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   API Docs: http://localhost:3000/docs" -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:Path += ';$env:APPDATA\Python\Scripts'; `$env:PYTHONPATH='$projectRoot\backend'; cd '$projectRoot'; Write-Host '🚀 Backend Server' -ForegroundColor Green; Write-Host 'http://localhost:3000' -ForegroundColor Cyan; Write-Host ''; poetry run python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Start frontend
Write-Host "🚀 Starting frontend server..." -ForegroundColor Green
Write-Host "   URL: http://localhost:5173" -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$projectRoot\frontend'; Write-Host '🚀 Frontend Server' -ForegroundColor Green; Write-Host 'http://localhost:5173' -ForegroundColor Cyan; Write-Host ''; pnpm run dev"
) -WindowStyle Normal

Write-Host "`n✅ Both servers are starting!" -ForegroundColor Green
Write-Host "`n📝 Access:" -ForegroundColor Cyan
Write-Host "   • Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   • Backend: http://localhost:3000" -ForegroundColor White
Write-Host "   • API Docs: http://localhost:3000/docs" -ForegroundColor White
Write-Host "`n💡 Close the server windows or press Ctrl+C to stop" -ForegroundColor Yellow
