@echo off
REM Lanceur Kill Feed Star Citizen

cd /d "%~dp0"

echo.
echo ========================================
echo  Kill Feed Star Citizen
echo ========================================
echo.

REM Nettoyer les processus existants pour éviter les conflits
echo Verification des processus existants...
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /I "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Arret des processus KillFeedSC existants...
    call kill_processes.bat >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo Lancement du serveur...

REM Detecter l'interpreteur Python
set "_PY=python"
where python >nul 2>&1
if errorlevel 1 (
  set "_PY=py -3"
  where py >nul 2>&1
  if errorlevel 1 (
    set "_PY=py"
  )
)

REM Lancement du serveur dans une console MINIMISEE (la fenetre batch se ferme)
start "Kill Feed Server" /min cmd /c %_PY% kill_feed_local.py

REM Attente courte pour laisser le serveur initialiser
echo Demarrage en cours...
timeout /t 1 /nobreak >nul

echo.
echo ========================================
echo  Kill Feed lance avec succes !
echo ========================================
echo.
echo - Interface Web : http://127.0.0.1:8080
echo - WebSocket : ws://127.0.0.1:8765
echo.
echo Utilisez l'interface web pour :
echo - Demarrer/Arreter l'overlay
echo - Voir les kills en temps reel
echo.
echo Pour arreter le serveur :
echo - Lancez stop.bat
echo - OU fermez la fenetre "Kill Feed Server"
echo.
