# 📋 Documentation Technique - KillFeedSC

## Vue d'ensemble

**KillFeedSC** est une application multi-composants qui affiche en temps réel les événements de kill dans Star Citizen. L'architecture repose sur trois composants principaux communiquant via WebSocket.

---

## 🏗️ Architecture Globale

```
┌─────────────────────┐
│   Star Citizen      │
│   (Game.log)        │
└──────────┬──────────┘
           │ Lecture fichier
           ▼
┌─────────────────────┐
│  Serveur Backend    │
│  (kill_feed_local)  │
│  - Parser logs      │
│  - HTTP Server      │
│  - WebSocket Server │
└──────────┬──────────┘
           │ WebSocket (ws://127.0.0.1:8765)
           ├──────────────┬──────────────┐
           ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Web UI   │   │ Overlay  │   │ Autres   │
    │ (HTML)   │   │ (Tkinter)│   │ Clients  │
    └──────────┘   └──────────┘   └──────────┘
```

---

## 🔧 Composant 1 : Serveur Backend (`kill_feed_local.py`)

### Technologies utilisées

| Technologie | Version | Usage |
|------------|---------|-------|
| **Python** | 3.8+ | Langage principal |
| **asyncio** | stdlib | Gestion asynchrone WebSocket |
| **websockets** | pip | Serveur WebSocket temps réel |
| **http.server** | stdlib | Serveur HTTP pour fichiers statiques |
| **threading** | stdlib | Lecture asynchrone du Game.log |
| **sqlite3** | stdlib | Base de données statistiques |
| **configparser** | stdlib | Lecture configuration INI |
| **pathlib** | stdlib | Manipulation chemins fichiers |
| **re** | stdlib | Parsing regex des logs |

### Responsabilités

#### 1. **Parser de logs** (Thread dédié)
- **Technologie** : `threading.Thread` + lecture fichier
- **Action** : Lecture continue du `Game.log` (tail -f like)
- **Méthode** : 
  - Ouverture fichier en mode lecture
  - Positionnement à la fin (`seek(0, 2)`)
  - Polling périodique des nouvelles lignes
  - Parsing regex pour détecter kills/deaths/suicides

#### 2. **Serveur HTTP** (Thread dédié)
- **Technologie** : `http.server.SimpleHTTPRequestHandler` + `socketserver.TCPServer`
- **Port** : 8080 (configurable)
- **Action** : 
  - Sert les fichiers statiques (`index.html`, `overlay.html`)
  - Génère dynamiquement `config.js` avec les paramètres
- **Sécurité** : 
  - Validation des chemins (anti path-traversal)
  - Restriction localhost uniquement

#### 3. **Serveur WebSocket** (Asyncio)
- **Technologie** : `websockets.serve()` + `asyncio`
- **Port** : 8765 (configurable)
- **Action** :
  - Broadcast des événements à tous les clients connectés
  - Messages JSON : `{type: 'kill', killer: '...', victim: '...', ...}`
  - Gestion connexions multiples simultanées
- **Types de messages** :
  - `hello` : Envoyé à la connexion (nom joueur, config)
  - `kill` : Événement de kill
  - `death` : Mort sans killer identifié
  - `suicide` : Suicide détecté
  - `close_overlay` : Commande de fermeture overlay

#### 4. **Base de données SQLite**
- **Technologie** : `sqlite3`
- **Fichier** : `kill_feed_stats.db`
- **Tables** :
  - `kills` : Historique complet des kills
  - `players` : Statistiques par joueur (K/D ratio)
- **Actions** :
  - Insertion événements
  - Agrégation statistiques
  - Requêtes pour l'interface web

### Patterns de conception

- **Producer-Consumer** : Thread parser → Queue → WebSocket broadcaster
- **Observer Pattern** : WebSocket clients s'abonnent aux événements
- **Singleton** : Instance unique du serveur

---

## 🎨 Composant 2 : Interface Web (`index.html`)

### Technologies utilisées

| Technologie | Version | Usage |
|------------|---------|-------|
| **HTML5** | - | Structure page |
| **CSS3** | - | Styling moderne |
| **JavaScript** | ES6+ | Logique client |
| **WebSocket API** | Native | Communication temps réel |
| **Fetch API** | Native | Requêtes HTTP |
| **Google Fonts** | CDN | Polices Orbitron, Rajdhani |

### Architecture Frontend

#### 1. **WebSocket Client**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8765');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleKillEvent(data);
};
```
- **Reconnexion automatique** : Retry avec backoff exponentiel
- **Heartbeat** : Ping/pong pour maintenir connexion

#### 2. **Gestion des événements**
- **DOM Manipulation** : Création dynamique des éléments kill
- **Animations CSS** : 
  - Fade-in pour nouveaux kills
  - Fade-out après 30 secondes
  - Glow effects sur hover
- **Tri** : Kills affichés du plus récent au plus ancien

#### 3. **Statistiques temps réel**
- **Calcul K/D ratio** : Mise à jour dynamique
- **Graphiques** : Potentiellement Chart.js (si implémenté)
- **Filtres** : Par joueur, par type d'événement

### Design System

#### Palette de couleurs (RSI-inspired)
```css
--bg-primary: #0a1d2a;      /* Navy profond */
--accent-cyan: #22d6ff;     /* Cyan RSI */
--success: #28ffa7;         /* Vert néon (vos kills) */
--danger: #ff6b6b;          /* Rouge (vos morts) */
--text-primary: #d9ecf7;    /* Blanc cassé */
```

#### Typographie
- **Titres** : Orbitron (futuriste, sci-fi)
- **Corps** : Rajdhani (lisible, moderne)

#### Effets visuels
- **Gradients** : Radial et linear pour profondeur
- **Shadows** : Box-shadow multi-couches
- **Animations** : Keyframes CSS pour glow, pulse, fade

---

## 🪟 Composant 3 : Overlay Tkinter (`overlay_window.py`)

### Technologies utilisées

| Technologie | Version | Usage |
|------------|---------|-------|
| **Python** | 3.8+ | Langage principal |
| **Tkinter** | stdlib | Framework GUI |
| **Canvas** | Tkinter | Rendu graphique 2D |
| **websockets** | pip | Client WebSocket |
| **asyncio** | stdlib | Boucle événements async |
| **threading** | stdlib | WebSocket dans thread séparé |

### Architecture Overlay

#### 1. **Fenêtre transparente**
```python
root.overrideredirect(True)           # Sans bordures
root.attributes('-topmost', True)     # Toujours au-dessus
root.attributes('-alpha', 0.7)        # Transparence 70%
root.attributes('-transparentcolor', 'black')  # Noir = transparent
```

**Technologie Windows** : Utilise les APIs Win32 via Tkinter
- `-topmost` : Flag `WS_EX_TOPMOST`
- `-transparentcolor` : Layered window avec clé de couleur

#### 2. **Canvas Tkinter**
- **Rendu** : Dessin 2D avec primitives (texte, rectangles)
- **Refresh** : Boucle `root.after(100ms)` pour redessiner
- **Optimisation** : 
  - Clear canvas complet à chaque frame
  - Pas de double buffering (Tkinter le gère)

#### 3. **Client WebSocket**
```python
async def _websocket_client():
    async with websockets.connect(WS_URL) as ws:
        async for message in ws:
            data = json.loads(message)
            self.add_kill(data)
```
- **Thread séparé** : Évite de bloquer GUI Tkinter
- **Communication** : Queue thread-safe (implicite via `deque`)
- **Reconnexion** : Retry automatique avec `asyncio.sleep(2)`

#### 4. **Interactions utilisateur**

##### Drag & Drop (déplacement fenêtre)
```python
title_bar.bind('<Button-1>', self._start_drag)
title_bar.bind('<B1-Motion>', self._on_drag)
```
- **Technologie** : Event binding Tkinter
- **Calcul** : Delta position souris → nouvelle position fenêtre

##### Resize (redimensionnement)
```python
resize_grip.bind('<Button-1>', self._start_resize)
resize_grip.bind('<B1-Motion>', self._on_resize_drag)
```
- **Contraintes** : Min/max width/height
- **Préservation** : Position X/Y maintenue

##### Raccourcis clavier
- `Escape` : Fermeture
- `Ctrl+Q` : Fermeture
- **Technologie** : `root.bind('<Key>', callback)`

#### 5. **Gestion des kills**

##### Structure de données
```python
class KillEntry:
    text: str       # "⚔️ Killer → Victim"
    color: str      # Hex color (#00ff88, #ff4757, etc.)
    timestamp: float  # time.time()
    alpha: float    # Transparence (fade out)
```

##### Collection
```python
kills: deque[KillEntry] = deque(maxlen=MAX_KILLS_DISPLAY)
```
- **Type** : `collections.deque` (FIFO optimisé)
- **Limite** : 10 kills max affichés
- **Insertion** : `appendleft()` pour ajouter en haut

##### Fade out progressif
```python
age = current_time - kill.timestamp
if age > 25:
    alpha = max(0.0, 1.0 - (age - 25) / 5)  # Fade sur 5s
```
- **Technique** : Interpolation linéaire alpha
- **Rendu** : Mélange couleur avec noir (`_blend_color()`)

#### 6. **Rendu visuel**

##### Polices
```python
font_kill = tkfont.Font(family='Segoe UI', size=11, weight='bold')
font_small = tkfont.Font(family='Segoe UI', size=9)
```

##### Couleurs dynamiques
- **Votre kill** : `#00ff88` (vert néon)
- **Votre mort** : `#ff4757` (rouge vif)
- **Kill normal** : `#00ffff` (cyan électrique)
- **Suicide** : `#ff4757` (rouge)
- **Mort** : `#c8d6e5` (gris clair)

##### Indicateur de connexion
- **Connecté** : Point vert (`#28ffa7`)
- **Déconnecté** : Point orange (`#ffa726`)

---

## 🔄 Flux de données complet

### Scénario : Un kill se produit dans le jeu

```
1. Star Citizen écrit dans Game.log
   ↓
2. Thread parser détecte nouvelle ligne
   ↓ (regex matching)
3. Événement parsé → objet Python
   ↓
4. Insertion dans SQLite (statistiques)
   ↓
5. Broadcast WebSocket à tous les clients
   ↓
   ├─→ 6a. Interface web reçoit message
   │       ↓
   │   7a. DOM update + animation CSS
   │
   └─→ 6b. Overlay Tkinter reçoit message
           ↓
       7b. Ajout dans deque + redraw canvas
```

### Format message WebSocket

```json
{
  "type": "kill",
  "killer": "PlayerName",
  "killer_ship": "Aegis Sabre",
  "victim": "EnemyName",
  "victim_ship": "Drake Cutlass Black",
  "timestamp": "2025-10-24T22:45:12Z",
  "weapon": "Energy weapon"
}
```

---

## 🔒 Sécurité

### Mesures implémentées

#### 1. **Validation des entrées**
```python
def _validate_path(path: str) -> str:
    resolved = Path(path).resolve()
    if ".." in str(resolved):  # Anti path-traversal
        return _default_log_path()
    if resolved.suffix.lower() != ".log":  # Extension valide
        return _default_log_path()
```

#### 2. **Restriction réseau**
```python
def _validate_host(host: str) -> str:
    if host not in ("127.0.0.1", "localhost", "0.0.0.0"):
        return "127.0.0.1"  # Force localhost
```

#### 3. **Validation ports**
```python
def _validate_port(port: int, name: str) -> int:
    if port < 1024 or port > 65535:
        raise ValueError(f"{name} doit être entre 1024 et 65535")
```

#### 4. **Gestion erreurs**
- Try/except sur toutes les opérations I/O
- Logs de sécurité dans stderr
- Fallback sur valeurs par défaut

---

## 📦 Dépendances externes

### Python (pip)
```
websockets==12.0  # Serveur/client WebSocket
```

### Frontend (CDN)
```html
<!-- Polices Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
```

### Bibliothèques standard Python
- `asyncio` : Programmation asynchrone
- `tkinter` : GUI overlay
- `sqlite3` : Base de données
- `threading` : Concurrence
- `http.server` : Serveur HTTP
- `configparser` : Configuration INI
- `pathlib` : Manipulation fichiers
- `re` : Expressions régulières
- `json` : Sérialisation données

---

## 🚀 Performance

### Optimisations

#### Backend
- **Thread dédié** pour lecture logs (non-bloquant)
- **Asyncio** pour WebSocket (gestion milliers de connexions)
- **Deque** pour historique (O(1) insertion/suppression)
- **SQLite** avec index sur colonnes fréquentes

#### Frontend Web
- **CSS animations** (GPU accelerated)
- **Debouncing** sur scroll/resize events
- **Lazy loading** des statistiques

#### Overlay Tkinter
- **Refresh 100ms** (10 FPS, suffisant pour texte)
- **Canvas clear/redraw** optimisé
- **Deque limitée** (10 kills max)
- **Fade out** pour réduire éléments affichés

### Consommation ressources

| Composant | CPU | RAM | Réseau |
|-----------|-----|-----|--------|
| Backend | ~1-2% | ~30 MB | Négligeable |
| Web UI | ~0.5% | ~50 MB | Négligeable |
| Overlay | ~1% | ~20 MB | Négligeable |

---

## 🧪 Tests et Débogage

### Mode debug
```ini
[debug]
debug = true
```
- Active logs verbeux dans console
- Affiche messages WebSocket bruts
- Trace parsing regex

### Logs
- **stdout** : Événements normaux
- **stderr** : Erreurs et sécurité
- **Format** : `[Composant] Message`

---

## 🔮 Extensions possibles

### Technologies candidates

#### Graphiques avancés
- **Chart.js** : Graphiques statistiques
- **D3.js** : Visualisations complexes

#### Notifications
- **Windows Toast** : Notifications système
- **Plyer** : Notifications cross-platform

#### Audio
- **pygame.mixer** : Sons pour kills
- **pydub** : Traitement audio

#### Base de données
- **PostgreSQL** : Si scaling nécessaire
- **Redis** : Cache temps réel

#### Frontend moderne
- **React** : SPA avec composants
- **Vue.js** : Alternative légère
- **Tailwind CSS** : Utility-first CSS

---

## 📚 Références

### Documentation officielle
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [websockets library](https://websockets.readthedocs.io/)
- [Tkinter](https://docs.python.org/3/library/tkinter.html)
- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

### Standards
- [WebSocket Protocol (RFC 6455)](https://datatracker.ietf.org/doc/html/rfc6455)
- [JSON (RFC 8259)](https://datatracker.ietf.org/doc/html/rfc8259)

---

**Version** : 1.0.0  
**Dernière mise à jour** : 2025-10-24  
**Auteur** : KillFeedSC Team
