@echo off
REM Lanceur Kill Feed Star Citizen

cd /d "%~dp0"

echo.
echo ========================================
echo  Kill Feed Star Citizen
echo ========================================
echo.
echo Lancement du serveur...

REM Lancement du serveur Python dans une nouvelle fenêtre
REM Le serveur Python ouvrira automatiquement le navigateur
start "Kill Feed Server" cmd /k python kill_feed_local.py

REM Attente de 3 secondes pour que le serveur démarre
echo Demarrage en cours...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo  Kill Feed lance avec succes !
echo ========================================
echo.
echo - Serveur : http://127.0.0.1:8081
echo - WebSocket : ws://127.0.0.1:8765
echo.
echo Pour arreter le serveur :
echo - Fermez la fenetre "Kill Feed Server"
echo - OU lancez stop.bat
echo.
pause
