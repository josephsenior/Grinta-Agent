@echo off
REM Enforce strict CSP for any auxiliary local commands (non-Docker portions)
set CSP_POLICY=strict
echo ========================================
echo   Restarting Forge Backend
echo ========================================

REM Stop existing containers
echo.
echo Stopping existing containers...
docker stop forge-app- 2>nul
docker rm forge-app- 2>nul

REM Start services
echo.
echo Starting backend server...
docker compose up -d

echo.
echo ========================================
echo   Waiting for backend to be ready...
echo ========================================
timeout /t 10 /nobreak

REM Check health
echo.
echo Checking backend health...
curl http://localhost:3000/health

echo.
echo ========================================
echo   Forge is ready!
echo   Frontend: http://localhost:3001
echo   Backend:  http://localhost:3000
echo ========================================
echo.
pause

