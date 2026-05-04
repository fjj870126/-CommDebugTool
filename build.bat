@echo off
REM ========================================
REM  CommDebugTool - Windows Build Script
REM ========================================
echo ========================================
echo  CommDebugTool - Windows Build Script
echo ========================================
echo.

cd /d "%~dp0"

REM Check python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python and add it to PATH.
    pause
    exit /b 1
)

echo Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

echo Installing pyserial...
python -m pip install pyserial 2>nul

REM Detect architecture
set PLATFORM=windows-x64
if "%PROCESSOR_ARCHITECTURE%"=="ARM64" set PLATFORM=windows-arm64
if "%PROCESSOR_ARCHITECTURE%"=="x86" set PLATFORM=windows-x86

set DIST_DIR=dist\%PLATFORM%
set BUILD_DIR=build\%PLATFORM%

echo.
echo Platform: %PLATFORM%
echo Output:   %DIST_DIR%\
echo.

REM Clean only this platform's build
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"

echo Building...
echo.

python -m PyInstaller CommDebugTool.spec --noconfirm --distpath "%DIST_DIR%" --workpath "%BUILD_DIR%"
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build complete!
echo ========================================
echo.
echo   Output: %DIST_DIR%\CommDebugTool.exe
echo.
pause
