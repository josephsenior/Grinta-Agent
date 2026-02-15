# Start Forge Backend Server
# Sets PYTHONPATH correctly so forge module can be found

Write-Host "🚀 Starting Forge Backend Server..." -ForegroundColor Cyan

# Add Poetry to PATH
$env:Path += ";$env:APPDATA\Python\Scripts"

# Change to project directory
Set-Location -Path $PSScriptRoot

# Set Python path to include project root (critical!)
$env:PYTHONPATH = "$PSScriptRoot"

Write-Host "`n📁 Project root: $PSScriptRoot" -ForegroundColor Gray
Write-Host "📁 Backend path: $PSScriptRoot\backend" -ForegroundColor Gray
Write-Host "🐍 Python path: $env:PYTHONPATH" -ForegroundColor Gray

# Verify backend module
Write-Host "`n🔍 Verifying backend module..." -ForegroundColor Yellow
python -c "import sys; sys.path.insert(0, r'$PSScriptRoot'); import backend; print('✅ Backend module found')" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend module not found!" -ForegroundColor Red
    Write-Host "Trying to install package..." -ForegroundColor Yellow
    poetry install
}

Write-Host "`n🚀 Starting server on http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

# Start server with PYTHONPATH set
$env:PYTHONPATH = "$PSScriptRoot\backend"
poetry run python start_server.py
