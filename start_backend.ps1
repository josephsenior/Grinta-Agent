# Start Forge Backend Server
# Sets PYTHONPATH correctly so forge module can be found

Write-Host "🚀 Starting Forge Backend Server..." -ForegroundColor Cyan

# Add Poetry to PATH
$env:Path += ";$env:APPDATA\Python\Scripts"

# Change to project directory
Set-Location -Path $PSScriptRoot

# Set Python path to include backend directory (critical!)
$env:PYTHONPATH = "$PSScriptRoot\backend"

Write-Host "`n📁 Project root: $PSScriptRoot" -ForegroundColor Gray
Write-Host "📁 Backend path: $PSScriptRoot\backend" -ForegroundColor Gray
Write-Host "🐍 Python path: $env:PYTHONPATH" -ForegroundColor Gray

# Verify forge can be imported
Write-Host "`n🔍 Verifying forge module..." -ForegroundColor Yellow
python -c "import sys; sys.path.insert(0, r'$PSScriptRoot\backend'); import forge; print('✅ Forge module found')" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Forge module not found!" -ForegroundColor Red
    Write-Host "Trying to install package..." -ForegroundColor Yellow
    poetry install
}

Write-Host "`n🚀 Starting server on http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

# Start server with PYTHONPATH set
$env:PYTHONPATH = "$PSScriptRoot\backend"
poetry run python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload
