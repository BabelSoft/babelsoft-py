@echo off
echo Starting BabelMap...
echo.

set ROOT=%~dp0

echo [1/2] Starting Python backend...
start "" /B python "%ROOT%backend\server.py" 2>nul
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
