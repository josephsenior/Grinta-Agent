# ============================================
# RUN FORGE NOW - Simple Startup Script
# ============================================

Write-Host "🚀 Starting Forge..." -ForegroundColor Cyan
Write-Host ""

# Add Poetry to PATH
$env:Path += ";$env:APPDATA\Python\Scripts"

# Change to project directory
cd C:\Users\GIGABYTE\Desktop\Forge

# Install uvicorn and fastapi directly (workaround for lock file issues)
Write-Host "📦 Installing essential packages..." -ForegroundColor Yellow
python -m pip install fastapi uvicorn[standard] python-socketio python-multipart --quiet --user

# Set Python path
$env:PYTHONPATH = "C:\Users\GIGABYTE\Desktop\Forge\backend"

# Start backend
Write-Host "`n🚀 Starting backend (http://localhost:3000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:PYTHONPATH='C:\Users\GIGABYTE\Desktop\Forge\backend'; cd 'C:\Users\GIGABYTE\Desktop\Forge'; Write-Host '🚀 Backend Server - http://localhost:3000' -ForegroundColor Green; python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Start frontend
Write-Host "🚀 Starting frontend (http://localhost:5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd 'C:\Users\GIGABYTE\Desktop\Forge\frontend'; Write-Host '🚀 Frontend Server - http://localhost:5173' -ForegroundColor Green; pnpm run dev"
) -WindowStyle Normal

Write-Host "`n✅ Both servers are starting in separate windows!" -ForegroundColor Green
Write-Host "   • Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   • Backend: http://localhost:3000" -ForegroundColor White
Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
