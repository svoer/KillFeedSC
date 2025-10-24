@echo off
REM Script pour tuer les processus KillFeedSC existants

echo Arret des processus KillFeedSC existants...

REM Tuer les processus Python (console) qui utilisent kill_feed_local.py ou overlay_window.py
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /I "PID"') do (
    wmic process where "ProcessId=%%i" get CommandLine 2>nul | findstr /I "kill_feed_local.py overlay_window.py" >nul
    if not errorlevel 1 (
        echo Arret du processus PID %%i (python.exe)
        taskkill /F /PID %%i >nul 2>&1
    )
)

REM Tuer les processus Python (windowless) pythonw.exe
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO LIST ^| findstr /I "PID"') do (
    wmic process where "ProcessId=%%i" get CommandLine 2>nul | findstr /I "kill_feed_local.py overlay_window.py" >nul
    if not errorlevel 1 (
        echo Arret du processus PID %%i (pythonw.exe)
        taskkill /F /PID %%i >nul 2>&1
    )
)

REM Alternative plus simple : tuer tous les processus python.exe (attention si vous avez d'autres scripts Python)
REM taskkill /F /IM python.exe >nul 2>&1

echo Processus arretes.
