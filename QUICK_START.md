# Quick Start Guide

## Prerequisites
- Python 3.12+
- Node.js 18+ (with pnpm)
- Poetry (already installed on your system)

## Quick Start (3 Steps)

### Option 1: Use the Startup Script (Easiest)

1. **Open PowerShell in the project directory**
2. **Run the startup script:**
   ```powershell
   .\START_HERE.ps1
   ```

This will:
- ✅ Add Poetry to PATH
- ✅ Update and install dependencies
- ✅ Start backend server (http://localhost:3000)
- ✅ Start frontend server (http://localhost:5173)

### Option 2: Manual Start

1. **Add Poetry to PATH** (if not already added):
   ```powershell
   $env:Path += ";$env:APPDATA\Python\Scripts"
   ```

2. **Install dependencies:**
   ```powershell
   poetry lock --no-update
   poetry install --no-root
   ```

3. **Start backend** (Terminal 1):
   ```powershell
   poetry run python -m uvicorn forge.server.listen:app --host 127.0.0.1 --port 3000 --reload
   ```

4. **Start frontend** (Terminal 2):
   ```powershell
   cd frontend
   pnpm run dev
   ```

## Access the Application

- **Frontend (Development)**: http://localhost:5173
- **Backend API**: http://localhost:3000/api
- **API Documentation**: http://localhost:3000/docs

## Troubleshooting

### Poetry not found
If you get "poetry: command not found", add Poetry to your PATH:
```powershell
$env:Path += ";$env:APPDATA\Python\Scripts"
```

Or add it permanently:
1. Open System Properties → Environment Variables
2. Add `%APPDATA%\Python\Scripts` to your PATH

### Lock file out of date
If you see "pyproject.toml changed significantly", run:
```powershell
poetry lock --no-update
poetry install --no-root
```

### Port already in use
If port 3000 or 5173 is already in use:
- Backend: Change port with `--port 3001` in the uvicorn command
- Frontend: Change port in `frontend/vite.config.ts`
