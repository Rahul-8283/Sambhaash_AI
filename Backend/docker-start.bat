@echo off
REM Docker Quick Start Script - Sambhaash AI Backend (Windows)
REM Usage: docker-start.bat

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo Sambhaash AI - Docker Setup (Windows)
echo ============================================================
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker not found. Please install Docker Desktop:
    echo https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('docker --version') do set DOCKER_VERSION=%%i
echo [OK] Docker found: !DOCKER_VERSION!

REM Check if docker-compose is available
where docker-compose >nul 2>nul
if errorlevel 1 (
    echo [ERROR] docker-compose not found.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('docker-compose --version') do set COMPOSE_VERSION=%%i
echo [OK] docker-compose found: !COMPOSE_VERSION!

REM Check if .env exists
if not exist ".env" (
    echo.
    echo [WARNING] .env file not found. Using .env.docker as template...
    copy .env.docker .env
    echo [OK] Created .env from .env.docker
    echo [WARNING] Update .env with your actual API keys!
)

REM Build images
echo.
echo [INFO] Building Docker images (this may take a few minutes)...
echo.
docker-compose build
if errorlevel 1 (
    echo [ERROR] Docker build failed
    pause
    exit /b 1
)

REM Start services
echo.
echo [INFO] Starting services...
echo.
docker-compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)

REM Wait for services
echo.
echo [INFO] Waiting for services to be ready...
timeout /t 5 /nobreak

REM Verify services
echo.
echo ============================================================
echo Service Status:
echo ============================================================
docker-compose ps

REM Health checks
echo.
echo ============================================================
echo Health Checks:
echo ============================================================

docker-compose exec redis redis-cli ping >nul 2>&1
if errorlevel 0 (
    echo [OK] Redis: Healthy
) else (
    echo [WARNING] Redis: Checking...
)

curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 0 (
    echo [OK] FastAPI: Healthy
) else (
    echo [WARNING] FastAPI: Still starting (wait 10 seconds)
)

echo.
echo ============================================================
echo Docker Setup Complete!
echo ============================================================
echo.
echo Next Steps:
echo   1. Open API Docs:  http://localhost:8000/docs
echo   2. View logs:      docker-compose logs -f
echo   3. Stop services:  docker-compose down
echo.
echo For more info, see DOCKER_SETUP_GUIDE.md
echo.
pause
