@echo off
echo Starting BabelMap...
echo.

set ROOT=%~dp0
rem Resolve parent directory (project root)
pushd "%ROOT%.."
set PROJ=%CD%
popd

echo [0/2] Killing previous processes...
:: Kill process on backend port 17890
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":17890" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul
    echo        Killed PID %%a on port 17890
)
:: Kill process on frontend port 5173
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul
    echo        Killed PID %%a on port 5173
)

echo [1/2] Starting Python backend...
cd /d "%PROJ%"
set PYTHONPATH=%PROJ%
start "" /B python babelmap/backend/server.py 2>&1
echo        Backend: http://127.0.0.1:17890

echo [2/2] Starting Svelte frontend...
cd /d "%ROOT%frontend"
start "" /B npm run dev

echo.
echo BabelMap is running!
echo    Frontend: http://localhost:5173
echo.
echo Press any key to stop all processes...
pause >nul

taskkill /f /im python.exe /fi "WINDOWTITLE eq *server.py*" 2>nul
taskkill /f /im node.exe /fi "WINDOWTITLE eq *vite*" 2>nul
echo Stopped.
