@echo off
REM Arrêt du Kill Feed Star Citizen

echo Arret du Kill Feed Server...

REM Arrêt de tous les processus Python qui exécutent kill_feed_local.py
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID:"') do (
    wmic process where "ProcessId=%%i" get CommandLine 2>nul | findstr "kill_feed_local.py" >nul
    if not errorlevel 1 (
        echo Arret du processus %%i...
        taskkill /PID %%i /F >nul 2>&1
    )
)

echo.
echo Kill Feed Server arrete.
echo.
pause
