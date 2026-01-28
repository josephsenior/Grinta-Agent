# PowerShell script to find PostgreSQL installation on Windows

Write-Host "Searching for PostgreSQL installation..." -ForegroundColor Cyan
Write-Host ""

$found = $false

# Common installation paths
$searchPaths = @(
    "C:\Program Files\PostgreSQL",
    "C:\Program Files (x86)\PostgreSQL",
    "C:\PostgreSQL"
)

foreach ($basePath in $searchPaths) {
    if (Test-Path $basePath) {
        Write-Host "Found PostgreSQL directory: $basePath" -ForegroundColor Green
        
        # Look for bin directories
        $binDirs = Get-ChildItem -Path $basePath -Directory -Filter "bin" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 5
        
        foreach ($binDir in $binDirs) {
            $pgDump = Join-Path $binDir.FullName "pg_dump.exe"
            if (Test-Path $pgDump) {
                Write-Host ""
                Write-Host "Found pg_dump at: $pgDump" -ForegroundColor Green
                Write-Host ""
                Write-Host "To use this installation, you have two options:" -ForegroundColor Yellow
                Write-Host ""
                Write-Host "Option 1: Add to PATH (Recommended)" -ForegroundColor Cyan
                Write-Host "  1. Open System Properties -> Environment Variables" -ForegroundColor White
                Write-Host "  2. Edit Path in System variables" -ForegroundColor White
                Write-Host "  3. Add: $($binDir.FullName)" -ForegroundColor White
                Write-Host "  4. Restart your terminal/PowerShell" -ForegroundColor White
                Write-Host ""
                Write-Host "Option 2: Set Environment Variable" -ForegroundColor Cyan
                Write-Host "  Set POSTGRES_BIN=$($binDir.FullName)" -ForegroundColor White
                Write-Host "  Add to your .env file or set in PowerShell:" -ForegroundColor White
                $envExample = '$env:POSTGRES_BIN = "' + $binDir.FullName + '"'
                Write-Host "  $envExample" -ForegroundColor White
                Write-Host ""
                $found = $true
            }
        }
    }
}

if (-not $found) {
    Write-Host "PostgreSQL client tools not found in common locations." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "  1. Verify PostgreSQL is installed" -ForegroundColor White
    Write-Host "  2. Find the bin directory (usually contains pg_dump.exe)" -ForegroundColor White
    Write-Host "  3. Set POSTGRES_BIN environment variable to that directory" -ForegroundColor White
}
