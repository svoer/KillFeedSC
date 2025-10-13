# 🚀 Kill Feed Star Citizen

Interface web en temps réel pour suivre les kills dans Star Citizen.

**Version 1.0.0** - Sécurisé et optimisé ✅

## 🎮 Utilisation rapide

1. **Double-clic** sur `start.bat`
2. Le serveur démarre et le navigateur s'ouvre automatiquement
3. Lancez Star Citizen et jouez !
4. Les kills s'affichent en temps réel

## 🛑 Arrêter le serveur

- Fermez la fenêtre "Kill Feed Server"
- OU double-clic sur `stop.bat`

## ⚙️ Configuration

Éditez `config.ini` pour personnaliser :

```ini
[SETTINGS]
GAME_LOG_PATH=F:\StarCitizen\StarCitizen\LIVE

[INTERFACE]
HTTP_PORT=8081
WEBSOCKET_PORT=8765
AUTO_OPEN_BROWSER=true

[PLAYER]
NAME=VotrePseudo

[DEBUG]
ENABLED=false
```

## 🎨 Fonctionnalités

- ✅ Interface moderne et responsive
- ✅ Affichage des noms de vaisseaux complets
- ✅ Liens directs vers les profils RSI
- ✅ Distinction visuelle : Combat / Suicide / Crash
- ✅ Statistiques K/D en temps réel
- ✅ Animations fluides

## 📁 Fichiers

- `start.bat` - Lanceur (double-clic)
- `stop.bat` - Arrêt du serveur
- `kill_feed_local.py` - Serveur Python
- `index.html` - Interface web
- `config.ini` - Configuration

## 🔧 Dépendances

```bash
pip install websockets
```

## 🔒 Sécurité

Version 1.0.0 inclut :
- ✅ Validation des chemins de fichiers (anti path-traversal)
- ✅ Validation des ports (1024-65535)
- ✅ Restriction localhost uniquement
- ✅ Gestion sécurisée des erreurs
- ✅ Logs de sécurité

Voir `SECURITY.md` pour plus de détails.

---

**Bon jeu dans le 'verse ! o7** 🚀
