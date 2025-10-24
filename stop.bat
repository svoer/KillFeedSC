@echo off
REM Arrêt du Kill Feed Star Citizen

echo.
echo ========================================
echo  Arret Kill Feed Star Citizen
echo ========================================
echo.

echo Arret du serveur et de l'overlay...

REM Arrêt de tous les processus Python liés à KillFeedSC
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID:"') do (
    wmic process where "ProcessId=%%i" get CommandLine 2>nul | findstr "kill_feed_local.py overlay_window.py" >nul
    if not errorlevel 1 (
        echo Arret du processus %%i...
        taskkill /PID %%i /F >nul 2>&1
    )
)

echo.
echo ========================================
echo  Kill Feed arrete avec succes
echo ========================================
echo.
REM pause removed for auto-close
