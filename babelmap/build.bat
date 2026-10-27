@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   BabelMap - Build ^& Run
echo ============================================
echo.

set ROOT=%~dp0
pushd "%ROOT%.."
set PROJ=%CD%
popd

:: [1/4] Frontend dependencies
echo [1/4] Checking frontend dependencies...
cd /d "%ROOT%frontend"
if not exist "node_modules\" (
    echo        Installing frontend packages...
    call npm install
) else (
    echo        Frontend dependencies OK.
)

cd /d "%PROJ%"
if not exist "node_modules\" (
    echo        Installing Tauri CLI...
    call npm install
) else (
    echo        Tauri CLI OK.
)

:: [2/4] Freeze the Python backend into the Tauri sidecar binary
echo.
echo [2/4] Building the Python backend sidecar...
cd /d "%PROJ%"
if not exist ".venv\Scripts\python.exe" (
    echo        Setting up uv environment ^(first run^)...
    call uv sync
)
call uv run python babelmap/backend/build_sidecar.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Sidecar build failed! See output above.
    pause
    exit /b 1
)

:: [3/4] Build the Tauri app (bundles the sidecar + babellib/data resources)
echo.
echo [3/4] Killing previous instance...
taskkill /f /im BabelMap.exe >nul 2>&1
echo        (Done)

echo.
echo [3/4] Building the frontend bundle...
cd /d "%ROOT%frontend"
call npm run build
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)

echo.
echo [3/4] Building BabelMap.exe (this may take a while, ~850 MB of data)...
cd /d "%PROJ%"
call npx tauri build --bundles nsis 2>&1
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
