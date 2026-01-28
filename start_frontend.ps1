# Start the frontend development server
Set-Location -Path "$PSScriptRoot\frontend"
Write-Host "🚀 Starting Forge frontend on http://localhost:5173" -ForegroundColor Green
pnpm run dev
