@echo off
echo Starting BabelMap...
echo.

set ROOT=%~dp0
rem Resolve parent directory (project root)
pushd "%ROOT%.."
set PROJ=%CD%
popd

echo [0/2] Killing previous processes...
:: Kill process on backend port 18080
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":18080" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul
    echo        Killed PID %%a on port 18080
)
:: Kill process on frontend port 18081
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":18081" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul
    echo        Killed PID %%a on port 18081
)

echo [1/2] Starting Python backend...
cd /d "%PROJ%"
set PYTHONPATH=%PROJ%\babellib
if not exist ".venv\Scripts\python.exe" (
    echo        Setting up uv environment (first run)...
    call uv sync
)
start "" /B uv run python babelmap/backend/server.py 2>&1
echo        Backend: http://127.0.0.1:18080

echo [2/2] Starting Svelte frontend...
cd /d "%ROOT%frontend"
start "" /B npm run dev

echo.
echo BabelMap is running!
echo    Frontend: http://localhost:18081
echo.
echo Press any key to stop all processes...
pause >nul

taskkill /f /im python.exe /fi "WINDOWTITLE eq *server.py*" 2>nul
taskkill /f /im node.exe /fi "WINDOWTITLE eq *vite*" 2>nul
echo Stopped.
