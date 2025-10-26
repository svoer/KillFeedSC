```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗  ██╗██╗██╗     ██╗         ███████╗███████╗███████╗██████╗  ║
║   ██║ ██╔╝██║██║     ██║         ██╔════╝██╔════╝██╔════╝██╔══██╗ ║
║   █████╔╝ ██║██║     ██║         █████╗  █████╗  █████╗  ██║  ██║ ║
║   ██╔═██╗ ██║██║     ██║         ██╔══╝  ██╔══╝  ██╔══╝  ██║  ██║ ║
║   ██║  ██╗██║███████╗███████╗    ██║     ███████╗███████╗██████╔╝ ║
║   ╚═╝  ╚═╝╚═╝╚══════╝╚══════╝    ╚═╝     ╚══════╝╚══════╝╚═════╝  ║
║                                                               ║
║              🚀 STAR CITIZEN COMBAT TRACKER 🚀               ║
║                                                               ║
║           "Dans le vide, personne ne vous entendra           ║
║                    compter vos kills..."                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

## 📡 TRANSMISSION REÇUE

Pilote,

Bienvenue à bord du **Kill Feed SC** - votre système de combat personnel embarqué. Cet outil de reconnaissance tactique trace en temps réel chaque victoire, chaque perte, chaque explosion dans le 'verse.

**Version 1.0.0** | *Certifié UEE* | *Opérationnel*

---

## 🎯 DÉPLOIEMENT RAPIDE

### Initialisation du système :

```
1. ► Double-clic sur 'start.bat' 
2. ► Installation automatique des modules (première activation uniquement)
3. ► L'interface tactique s'ouvre automatiquement dans votre navigateur
4. ► Lancez Star Citizen et entrez dans le 'verse
5. ► Vos kills s'affichent en temps réel - Que la chasse commence !
```

**Note :** Aucune configuration requise pour une première mission. Le système détecte automatiquement votre `Game.log`.

---

## 🛡️ ARRÊT D'URGENCE

**Protocole de désengagement :**
- Fermez la console "Kill Feed Server" 
- **OU** lancez `stop.bat` pour un arrêt complet
- **OU** utilisez `kill_processes.bat` pour une extinction forcée

---

## ⚙️ CONFIGURATION DU VAISSEAU

Personnalisez votre système via `config.ini` :

```ini
[SETTINGS]
# Chemin vers vos logs de combat
GAME_LOG_PATH=F:\StarCitizen\StarCitizen\LIVE

[INTERFACE]
# Ports de communication
HTTP_PORT=8080
WEBSOCKET_PORT=8765
AUTO_OPEN_BROWSER=true

[PLAYER]
# Votre callsign dans le 'verse
NAME=YourCallsign

[DEBUG]
# Mode diagnostic (pour les mécaniciens)
ENABLED=false
```

---

## 🎨 SYSTÈMES EMBARQUÉS

### Interface Tactique RSI-Style
- **HUD temps réel** : Chaque kill s'affiche instantanément
- **Reconnaissance vaisseaux** : Affichage des noms complets (Anvil Arrow, Aegis Sabre, etc.)
- **Liens RSI** : Accès direct aux profils des pilotes adverses
- **Classification automatique** :
  - 🔴 **Combat** : Victoire contre un adversaire
  - 🟠 **Suicide** : Collision ou erreur de pilotage
  - ⚪ **Mort** : Cause indéterminée (environnement, bug)
- **Statistiques K/D** : Ratio kill/death en direct
- **Animations fluides** : Parce qu'un bon HUD, ça compte

### Overlay Transparent (Optionnel)
- Affichage par-dessus Star Citizen
- Positionnable et redimensionnable
- Transparence ajustable
- Raccourci clavier : `Ctrl+Alt+O` pour basculer

---

## 🗂️ MANIFESTE

```
KillFeedSC/
├── start.bat              → Lanceur principal (double-clic)
├── stop.bat               → Arrêt du système
├── kill_processes.bat     → Arrêt forcé (urgence)
├── kill_feed_local.py     → Cœur du système (serveur)
├── overlay_window.py      → Module overlay transparent
├── index.html             → Interface web tactique
├── overlay.html           → Interface overlay
├── config.ini             → Configuration personnelle
├── requirements.txt       → Dépendances système
└── README.md              → Ce fichier (vous êtes ici)
```

---

## 🔧 DÉPENDANCES SYSTÈME

**Installation automatique activée** : `start.bat` déploie automatiquement tous les modules requis dans un environnement virtuel isolé.

### Installation manuelle (pour les vétérans) :
```bash
pip install -r requirements.txt
```

### Modules requis :
- `websockets` >= 12.0 (communication temps réel)
- Python 3.8+ (requis)

**Note :** Tous les autres modules sont natifs Python (asyncio, tkinter, json, etc.)

---

## 🔒 PROTOCOLES DE SÉCURITÉ

**Cette version embarque des systèmes de protection UEE :**

- ✅ **Anti-intrusion** : Validation stricte des chemins de fichiers
- ✅ **Ports sécurisés** : Plage validée (1024-65535)
- ✅ **Localhost uniquement** : Pas d'exposition externe
- ✅ **Gestion d'erreurs** : Aucun crash en cas d'anomalie
- ✅ **Logs sécurisés** : Traçabilité complète

---

## 🎖️ SUPPORT & COMMUNAUTÉ

**Problème de connexion au 'verse ?**
- Vérifiez que Star Citizen est lancé
- Vérifiez le chemin `GAME_LOG_PATH` dans `config.ini`
- Consultez la console pour les messages d'erreur

**Bugs ou suggestions ?**
- Créez une issue sur le repository
- Rejoignez la communauté SC pour partager vos mods

---

## 📜 LEGAL

Ce projet est un outil tiers non-officiel. Il ne modifie pas les fichiers du jeu et lit simplement les logs publics de Star Citizen.

**Respect du ToS** : Aucune modification du client, aucun avantage injuste.

---

```
═══════════════════════════════════════════════════════════
         FLY SAFE, SHOOT STRAIGHT, AND WATCH THE 'VERSE
                    o7 Bon vol, Citoyen !
═══════════════════════════════════════════════════════════
```

**Version 1.0.0** | Développé avec ❤️ pour la communauté Star Citizen
