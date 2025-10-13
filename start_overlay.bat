@echo off
REM Lanceur Kill Feed Star Citizen avec Overlay

cd /d "%~dp0"

echo.
echo ========================================
echo  Kill Feed Star Citizen - OVERLAY MODE
echo ========================================
echo.
echo Configuration requise:
echo - Star Citizen en mode Borderless Window
echo.
echo Lancement du serveur...

REM Lancement du serveur Python dans une nouvelle fenêtre (sans ouvrir le navigateur)
start "Kill Feed Server" cmd /k python kill_feed_local.py

REM Attente de 3 secondes pour que le serveur démarre
echo Demarrage du serveur...
timeout /t 3 /nobreak >nul

REM Lancement de l'overlay
echo Lancement de l'overlay...
python overlay_window.py

echo.
echo L'overlay a ete ferme.
echo Pour arreter le serveur, fermez la fenetre "Kill Feed Server"
echo.
pause
