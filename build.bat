@echo off
echo ========================================
echo   VDI Toolkit - Build Script
echo ========================================
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Build EXE
echo.
echo Building VDIToolkit.exe from VDIToolkit.spec...
pyinstaller VDIToolkit.spec --noconfirm

echo.
if exist "dist\VDIToolkit.exe" (
    echo ========================================
    echo SUCCESS! EXE created at: dist\VDIToolkit.exe
    echo ========================================
) else (
    echo Build may have failed. Check errors above.
)
echo.
pause
