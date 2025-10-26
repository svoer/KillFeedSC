# KillFeedSC

Interface locale affichant en temps réel les événements de kill de Star Citizen via une page web et un overlay optionnel.

Version: 1.0.0

---

## Objectif

- Lire en continu le `Game.log` de Star Citizen (Windows)
- Parser des événements pertinents (morts, kills, destructions de véhicules, hostilité)
- Diffuser ces événements aux clients via WebSocket
- Afficher les événements dans une interface web locale et/ou un overlay Tkinter

---

## Stack technique

- Python 3 (asyncio + threads pour tail/parse + serveurs)
- Bibliothèque `websockets` (serveur et clients)
- `http.server.SimpleHTTPRequestHandler` pour servir l’UI et `/config.js`
- `ConfigParser` pour `config.ini`
- Expressions régulières (`re`) pour l’extraction des données depuis le log
- Tkinter pour l’overlay (client léger)

Il n’y a pas de base de données. Aucun fichier `.db` n’est requis.

---

## Architecture

- `kill_feed_local.py`
  - Serveur HTTP local (static + `/config.js` dynamique)
  - Serveur WebSocket (diffusion temps réel)
  - Thread de suivi (`tail`) de `Game.log` avec reprise et gestion de rotation/troncature
  - Parsing des lignes via regex et émission d’événements JSON

- `overlay_window.py`
  - Client Tkinter se connectant au WebSocket
  - Affichage d’une liste courte d’événements récents

- Front-end
  - `index.html` et `overlay.html` consomment le flux WS
  - `config.js` généré à la volée pour exposer l’URL WS et le nom du joueur

- Scripts
  - `start.bat` : création d’un venv `.venv`, installation des dépendances (`requirements.txt`), lancement du serveur
  - `stop.bat` : arrêt du serveur
  - `kill_processes.bat` : extinction forcée des processus Python liés

---

## Installation et exécution

Méthode recommandée (Windows) :
1. Double-cliquez `start.bat`
2. Au premier lancement, `.venv` est créé et `websockets` est installé
3. Le serveur démarre puis ouvre l’interface web locale

Méthode manuelle (optionnelle) :
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
.venv\Scripts\python.exe kill_feed_local.py
```

---

## Configuration (`config.ini`)

Exemple :
```ini
[SETTINGS]
GAME_LOG_PATH=F:\StarCitizen\StarCitizen\LIVE

[INTERFACE]
HTTP_PORT=8080
WEBSOCKET_PORT=8765
AUTO_OPEN_BROWSER=true

[PLAYER]
NAME=YourCallsign

[DEBUG]
ENABLED=false
```

Notes :
- Si `GAME_LOG_PATH` est un dossier, `Game.log` est ajouté automatiquement
- Si le log est absent, le serveur continue et réessaie régulièrement
- Les hôtes sont limités au local (127.0.0.1)

---

## Dépendances

- Python 3.8+
- `websockets>=12.0`

Les autres modules utilisés (`asyncio`, `http.server`, `configparser`, `tkinter`, etc.) proviennent de la bibliothèque standard Python.

---

## Structure

```
KillFeedSC/
├─ start.bat
├─ stop.bat
├─ kill_processes.bat
├─ kill_feed_local.py
├─ overlay_window.py
├─ index.html
├─ overlay.html
├─ config.js
├─ config.ini
├─ requirements.txt
└─ README.md
```

---

## Robustesse et sécurité

- Validation de ports et hôtes (localhost)
- Validation des chemins vers `Game.log` (extension `.log`)
- Gestion de la rotation/troncature du log et reprises
- En-têtes HTTP no-cache pour l’interface

---

## Limitations

- Pas de persistance (pas de stockage des événements)
- Parsing basé sur des motifs qui peuvent évoluer avec les versions du jeu

---

## Avertissement

Projet tiers non-officiel. Le programme ne modifie pas le client du jeu et lit uniquement le `Game.log` local.
Respect des conditions d’utilisation de Star Citizen requis.
