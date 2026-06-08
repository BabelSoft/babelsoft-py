@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   BabelMap - Build ^& Run
echo ============================================
echo.

set ROOT=%~dp0

:: [1/3] Install npm dependencies (if needed)
echo [1/3] Checking frontend dependencies...
cd /d "%ROOT%frontend"
if not exist "node_modules\" (
    echo        Installing frontend packages...
    call npm install
) else (
    echo        Frontend dependencies OK.
)

cd /d "%ROOT%"
if not exist "node_modules\" (
    echo        Installing Tauri CLI...
    call npm install
) else (
    echo        Tauri CLI OK.
)

:: [2/3] Build the Tauri app
echo.
echo [2/3] Killing previous instance...
taskkill /f /im BabelMap.exe >nul 2>&1
echo        (Done)

echo.
echo [3/4] Building BabelMap.exe (this may take a while)...
cd /d "%ROOT%"
call npx tauri build 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed! See output above for details.
    pause
    exit /b 1
)

:: [4/4] Launch the exe
echo.
echo [4/4] Launching BabelMap...
set EXE=%ROOT%src-tauri\target\release\BabelMap.exe
if exist "!EXE!" (
    echo        !EXE!
    explorer.exe "!EXE!"
) else (
    echo [ERROR] Exe not found at: !EXE!
    echo        Check build output above for the actual location.
    pause
    exit /b 1
)

echo.
echo Done! BabelMap is running.
exit /b 0
