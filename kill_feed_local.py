# -*- coding: utf-8 -*-
"""
KillFeedSC - serveur local HTTP + WebSocket + parser Game.log (Star Citizen)
- HTTP: sert les fichiers statiques du dossier du script (+ config.js dynamique)
- WS: diffuse les événements parsés aux clients web
- Tail: lit en continu le Game.log (Windows) dans un thread
- Parse: détecte (basique) morts/kill/suicides, avec déduplication

Dépendances:
  pip install websockets

Fichier optionnel: config.ini (dans le même dossier):
  [server]
  http_host = 127.0.0.1
  http_port = 8080
  ws_host   = 127.0.0.1
  ws_port   = 8765

  [ui]
  auto_open_browser = true
  player_name = MonPseudo

  [game]
  log_path = C:\\Users\\XXX\\AppData\\Local\\StarCitizen\\Game.log

  [debug]
  debug = false
"""

from __future__ import annotations
import asyncio
import websockets
import json
import os
import re
import sys
import time
import traceback
import threading
import socketserver
import random
from http.server import SimpleHTTPRequestHandler
from configparser import ConfigParser
from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, Deque, Tuple
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = "1.0.0"

# ===================== CONFIG =====================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def _default_log_path() -> str:
    """Retourne le chemin par défaut du Game.log"""
    local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(local, "StarCitizen", "Game.log")

def _validate_port(port: int, name: str) -> int:
    """Valide qu'un port est dans une plage acceptable"""
    if not isinstance(port, int):
        raise ValueError(f"{name} doit être un entier")
    if port < 1024 or port > 65535:
        raise ValueError(f"{name} doit être entre 1024 et 65535 (reçu: {port})")
    return port

def _validate_path(path: str) -> str:
    """Valide et sécurise un chemin de fichier"""
    if not path:
        return _default_log_path()
    
    # Résoudre le chemin absolu et normaliser
    try:
        resolved = Path(path).resolve()
        
        # Vérifier que le chemin ne contient pas de traversée dangereuse
        if ".." in str(resolved):
            print(f"[SECURITY] Chemin suspect détecté: {path}", file=sys.stderr)
            return _default_log_path()
        
        # Vérifier que c'est un fichier .log
        if resolved.suffix.lower() != ".log":
            print(f"[SECURITY] Extension de fichier invalide: {resolved.suffix}", file=sys.stderr)
            return _default_log_path()
        
        return str(resolved)
    except Exception as e:
        print(f"[SECURITY] Erreur de validation du chemin: {e}", file=sys.stderr)
        return _default_log_path()

def _validate_host(host: str) -> str:
    """Valide que l'hôte est localhost uniquement (sécurité)"""
    if host not in ("127.0.0.1", "localhost", "0.0.0.0"):
        print(f"[SECURITY] Hôte non autorisé: {host}, utilisation de 127.0.0.1", file=sys.stderr)
        return "127.0.0.1"
    return host

# Lecture de la configuration
CFG_PATH = os.path.join(BASE_DIR, "config.ini")
_cfg = ConfigParser()
_cfg.read(CFG_PATH, encoding="utf-8")

# Configuration avec validation de sécurité
try:
    # Ports (INTERFACE section dans le nouveau config.ini)
    HTTP_PORT = _validate_port(
        _cfg.getint("INTERFACE", "HTTP_PORT", fallback=8080),
        "HTTP_PORT"
    )
    WS_PORT = _validate_port(
        _cfg.getint("INTERFACE", "WEBSOCKET_PORT", fallback=8765),
        "WEBSOCKET_PORT"
    )
    
    # Hôtes (toujours localhost pour la sécurité)
    HTTP_HOST = _validate_host("127.0.0.1")
    WS_HOST = _validate_host("127.0.0.1")
    
    # Interface utilisateur
    AUTO_OPEN_BROWSER = _cfg.getboolean("INTERFACE", "AUTO_OPEN_BROWSER", fallback=True)
    PLAYER_NAME = _cfg.get("PLAYER", "NAME", fallback="")
    
    # Chemin du log avec validation
    raw_log_path = _cfg.get("SETTINGS", "GAME_LOG_PATH", fallback="")
    if raw_log_path:
        # Si c'est un dossier, ajouter Game.log
        if os.path.isdir(raw_log_path):
            raw_log_path = os.path.join(raw_log_path, "Game.log")
    LOG_PATH = _validate_path(raw_log_path)
    
    # Debug
    DEBUG = _cfg.getboolean("DEBUG", "ENABLED", fallback=False)
    
except ValueError as e:
    print(f"[ERROR] Configuration invalide: {e}", file=sys.stderr)
    print("[INFO] Utilisation des valeurs par défaut", file=sys.stderr)
    HTTP_HOST = "127.0.0.1"
    HTTP_PORT = 8080
    WS_HOST = "127.0.0.1"
    WS_PORT = 8765
    AUTO_OPEN_BROWSER = True
    PLAYER_NAME = ""
    LOG_PATH = _default_log_path()
    DEBUG = False

# Fallback dynamique de port HTTP
HTTP_PORT_SELECTED: Optional[int] = None
HTTP_READY = threading.Event()

# ===================== ETAT & REGEX =====================

# Map “pilote récent -> vaisseau” (TTL)
@dataclass
class DriverEntry:
    ship: str
    last_seen: float

drivers: Dict[str, DriverEntry] = {}
DRIVER_TTL_SEC = 5 * 60  # on garde 5 minutes

# Déduplication des événements
recent_signatures: Deque[Tuple[str, str, str]] = deque(maxlen=256)
recent_times: Deque[float] = deque(maxlen=256)
DEDUP_WINDOW_SEC = 5.0  # Fenêtre de déduplication en secondes

# Association Destruction -> Corpse pour reconstruire les kills serveur
last_corpse: Optional[Tuple[float, str]] = None
pending_vehicle_kills: Deque[Tuple[float, str, str, str, str]] = deque(maxlen=64)  # (ts, killer, vehicle, damage_type, raw_line)
LINK_WINDOW_SEC = 6.0

# Cache des attaquants récents pour associer attaquant -> vaisseau depuis les hostilités
recent_attackers: Dict[str, Tuple[float, str]] = {}  # {attacker_name: (timestamp, vehicle)}
ATTACKER_CACHE_TTL = 15.0  # 15 secondes

# Clients WebSocket
WS_CLIENTS: "set[websockets.WebSocketServerProtocol]" = set()
WS_LOCK = asyncio.Lock()

# Expressions régulières améliorées pour une meilleure détection
# Variantes de détection pilote->vaisseau
RE_DRIVER_A = re.compile(
    r'\[C\] (?P<driver>[^\s]+) entered entity (?P<ship>[^\s]+) as driver', 
    re.IGNORECASE
)
RE_DRIVER_B = re.compile(
    r'(?P<driver>[^\s]+)\s+entered\s+(?P<ship>[^\s]+)\s+as\s+driver',
    re.IGNORECASE
)
RE_DRIVER_C = re.compile(
    r'Driver:\s*(?P<driver>[^\s]+).*?(?:vehicle|ship):\s*(?P<ship>[^\s]+)',
    re.IGNORECASE
)

# Amélioration de la détection des morts avec plus de contexte
RE_DEATH = re.compile(
    r'(?:death|killed):\s*([^\s]+?)(?:\s*\(\d+\))?\s+died (?:at|in) .*? (?:from|by) ([^\s]+?)(?:\s+in\s+([^\s]+))?',
    re.IGNORECASE
)

# Détection améliorée des corps
RE_CORPSE = re.compile(
    r'Corpse:\s*([^\s]+?)(?:\s*\(\d+\))?\s+was killed by\s+([^\s]+?)(?:\s+using\s+([^\s]+))?',
    re.IGNORECASE
)

# Détection du nom du joueur local
RE_PLAYER = re.compile(
    r'Local player name set to \[([^\]]+)\]',
    re.IGNORECASE
)

# Détection des collisions et dommages
RE_CRASH = re.compile(
    r'\[Physics\] Collision|\[Damage\] (?:Damage|Death)',
    re.IGNORECASE
)

# Amélioration de l'extraction des noms de vaisseaux
RE_VEHICLE = re.compile(
    r'vehicle:\s*([^,\n]+?)(?:,|$)',
    re.IGNORECASE
)

# Détection des événements liés au joueur
RE_PLAYER_DEATH = re.compile(
    r'Local player was killed by ([^\s]+)',
    re.IGNORECASE
)

# Événements système
RE_QUIT = re.compile(r'Client: Quit', re.IGNORECASE)
RE_RESPAWN = re.compile(r'Client: Respawn', re.IGNORECASE)
RE_DISCONNECT = re.compile(r'Client: Disconnected', re.IGNORECASE)
RE_CONNECT = re.compile(r'Client: Connected to', re.IGNORECASE)

# Regex principale pour les morts d'acteurs (compatible avec le code existant)
RE_ACTOR_DEATH = re.compile(
    r'(?P<victim>[^\s]+)\s+(?:died|killed).*?(?:by|from)\s+(?P<killer>[^\s]+)(?:.*?(?P<cause>[^\s]+))?',
    re.IGNORECASE
)

# Regex spécifique pour le format Star Citizen
RE_SC_KILL = re.compile(
    r"<Actor Death>.*?'(?P<victim>[^']+)'.*?in zone '(?P<victim_vehicle>[^']+)'.*?killed by '(?P<killer>[^']+)'.*?using '(?P<weapon>[^']+)'.*?damage type '(?P<damage_type>[^']+)'",
    re.IGNORECASE
)

# Regex pour Vehicle Destruction (pour extraire le vaisseau, le pilote et le tueur)
RE_VEHICLE_DESTRUCTION = re.compile(
    r"<Vehicle Destruction>.*?Vehicle '(?P<vehicle>[^']+)'.*?driven by '(?P<driver>[^']+)'.*?caused by '(?P<causer>[^']+)'.*?with '(?P<damage_type>[^']+)'",
    re.IGNORECASE
)

# Regex pour les événements d'hostilité (capture le nom du pilote dans 'child')
RE_HOSTILITY = re.compile(
    r"<Debug Hostility Events>.*?FROM\s+(?P<attacker>[A-Za-z0-9_\-]+)\s+TO\s+(?P<target_vehicle>[^\s]+).*?child\s+(?P<target_pilot>[A-Za-z0-9_\-]+)",
    re.IGNORECASE
)

# Regex pour capturer les noms de joueurs dans les lignes Corpse
RE_CORPSE_PLAYER = re.compile(
    r"<\[ActorState\] Corpse>.*?Player '(?P<player>[^']+)'",
    re.IGNORECASE
)

# Regex pour détecter les kills avec plus de contexte
RE_KILL_EVENT = re.compile(
    r'<(?P<victim>[^>]+)>.*?killed.*?by.*?<(?P<killer>[^>]+)>',
    re.IGNORECASE
)

# Regex alternative pour les morts
RE_DEATH_ALT = re.compile(
    r'(?P<victim>[a-zA-Z0-9_-]+)\s+(?:was\s+)?killed\s+by\s+(?P<killer>[a-zA-Z0-9_-]+)',
    re.IGNORECASE
)

# Mapping des noms de vaisseaux pour une meilleure lisibilité
SHIP_NAMES = {
    'cutlass': 'Drake Cutlass',
    'arrow': 'Anvil Arrow',
    'gladius': 'Aegis Gladius',
    'titan': 'Aegis Avenger Titan',
    'freelancer': 'MISC Freelancer',
    'prospector': 'MISC Prospector',
    '600i': 'Origin 600i',
    '890j': 'Origin 890 Jump',
    'carrack': 'Anvil Carrack',
    'mole': 'ARGO MOLE',
    'hercules': 'Crusader Hercules',
    'valkyrie': 'Anvil Valkyrie',
    'vanguard': 'Aegis Vanguard',
    'sabre': 'Aegis Sabre',
    'hornet': 'Anvil Hornet',
    'buccaneer': 'Drake Buccaneer',
    'constellation': 'RSI Constellation',
    'caterpillar': 'Drake Caterpillar',
    'mercury': 'Crusader Mercury Star Runner',
    'msr': 'Crusader Mercury Star Runner',
    'nomad': 'Consolidated Outland Nomad',
    'terrapin': 'Anvil Terrapin',
    'reclaimer': 'Aegis Reclaimer',
    'hammerhead': 'Aegis Hammerhead',
    'idris': 'Aegis Idris',
    'javelin': 'Aegis Javelin',
    'retaliator': 'Aegis Retaliator',
    'eclipse': 'Aegis Eclipse',
    'blade': 'Vanduul Blade',
    'glaive': 'Vanduul Glaive',
    'scythe': 'Vanduul Scythe',
    'defender': 'Banu Defender',
    'merchantman': 'Banu Merchantman',
    'kraken': 'Drake Kraken',
    'polaris': 'RSI Polaris',
    'perseus': 'RSI Perseus',
    'cutter': 'Drake Cutter',
    'corsair': 'Drake Corsair',
    'redeemer': 'Aegis Redeemer',
    'inferno': 'Aegis Inferno',
    'ion': 'Aegis Ion',
    'scorpius': 'RSI Scorpius',
    'ares': 'Crusader Ares',
    'spirit': 'Crusader Spirit',
    'c1': 'Crusader C1',
    'a1': 'Crusader A1',
    'c2': 'Crusader C2',
    'm2': 'Crusader M2',
    'a2': 'Crusader A2',
    'raft': 'Argo RAFT',
    'vulture': 'Drake Vulture',
    'reliant': 'MISC Reliant',
    'tana': 'MISC Reliant Tana',
    'kore': 'MISC Reliant Kore',
    'sen': 'MISC Reliant Sen',
    'talon': 'Esperia Talon',
    'shrike': 'Esperia Talon Shrike',
    'prowler': 'Esperia Prowler',
    'khartu': "Xi'an Khartu-al",
    'navigator': 'Banu Merchantman Navigator',
    'bmm': 'Banu Merchantman'
}

def get_ship_display_name(ship_name: str) -> str:
    """Convertit un nom de vaisseau en un format plus lisible et raccourci"""
    if not ship_name:
        return ""
    
    # Nettoyage du nom
    ship_name = ship_name.lower().strip()
    
    # Vérification des correspondances exactes
    for key, display_name in SHIP_NAMES.items():
        if key.lower() in ship_name:
            # Raccourcir le nom (enlever le fabricant)
            parts = display_name.split()
            if len(parts) > 1:
                return ' '.join(parts[1:])  # Enlever le fabricant
            return display_name
    
    # Formatage générique si aucune correspondance trouvée
    formatted = ship_name.title().replace('_', ' ')
    # Limiter à 20 caractères
    if len(formatted) > 20:
        formatted = formatted[:17] + '...'
    return formatted

# ===================== OUTILS =====================

def now_ts() -> float:
    return time.time()

def prune_drivers():
    t = now_ts()
    stale = [k for k, v in drivers.items() if t - v.last_seen > DRIVER_TTL_SEC]
    for k in stale:
        drivers.pop(k, None)

def log_print(*a, **kw):
    print(*a, **kw)
    sys.stdout.flush()

def debug_print(*a, **kw):
    if DEBUG:
        print(*a, **kw, file=sys.stderr)
        sys.stderr.flush()

def make_sentence_fr(evt: dict) -> str:
    """Génère une phrase en français décrivant l'événement de manière plus détaillée et naturelle"""
    event_type = evt.get("type")
    victim = evt.get("victim") or "Inconnu"
    killer = evt.get("killer")
    cause = evt.get("cause", "")
    killer_ship = evt.get("killer_ship")
    victim_ship = evt.get("victim_ship")
    is_crash = evt.get("is_crash", False)
    is_suicide = evt.get("is_suicide", False)
    
    # Liste des phrases possibles pour chaque type d'événement
    phrases = []
    
    # Phrases pour les suicides
    if event_type == "suicide" or is_suicide:
        if is_crash:
            phrases.append(f"{victim} s'est écrasé(e) avec son {victim_ship or 'vaisseau'}")
        elif cause and "suicide" in cause.lower():
            phrases.append(f"{victim} s'est suicidé(e)")
        else:
            phrases.append(f"{victim} est mort(e) dans des circonstances mystérieuses")
    
    # Phrases pour les meurtres
    elif event_type == "kill" and killer:
        # Construction de la partie tueur
        killer_part = killer
        if killer_ship:
            killer_part = f"{killer} ({killer_ship})"
        
        # Construction de la partie victime
        victim_part = victim
        if victim_ship:
            victim_part = f"{victim} ({victim_ship})"
        
        # Phrases de base
        kill_verbs = ["a éliminé", "a vaincu", "a abattu", "a terrassé", "a éliminé"]
        if is_crash:
            kill_verbs = ["a percuté", "est entré en collision avec", "s'est écrasé sur"]
        
        # Sélection aléatoire d'un verbe
        import random
        verb = random.choice(kill_verbs)
        
        # Construction de la phrase
        phrases.append(f"{killer_part} {verb} {victim_part}")
        
        # Ajout de la cause si disponible
        if cause and cause.lower() not in ("unknown", "inconnu", "none"):
            cause_phrases = [
                f"avec {cause}",
                f"en utilisant {cause}",
                f"grâce à {cause}",
                f"par {cause}"
            ]
            phrases.append(random.choice(cause_phrases))
    
    # Phrases pour les morts naturelles
    elif event_type == "death":
        death_phrases = [
            f"{victim} est mort(e)",
            f"{victim} a péri",
            f"{victim} a trouvé la mort"
        ]
        phrases.append(random.choice(death_phrases))
        
        if cause:
            phrases.append(f"à cause de {cause}")
    
    # Fallback générique
    if not phrases:
        return f"Événement inconnu: {event_type} - {victim} par {killer or 'inconnu'}"
    
    # Assemblage de la phrase finale
    sentence = " ".join(phrases) + "."
    
    # Mise en majuscule de la première lettre
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
    
    return sentence
    return evt.get("message") or ""

def sign_evt(evt: dict) -> Tuple[str, str, str]:
    return (
        evt.get("type", ""),
        (evt.get("victim") or "").lower(),
        (evt.get("killer") or "").lower(),
    )

def is_duplicate(sig: Tuple[str, str, str]) -> bool:
    """Vérifie si un événement est un doublon récent"""
    t = now_ts()
    if sig in recent_signatures:
        idxs = [i for i, ss in enumerate(recent_signatures) if ss == sig]
        if idxs and (t - recent_times[idxs[-1]] < DEDUP_WINDOW_SEC):
            return True
    recent_signatures.append(sig)
    recent_times.append(t)
    return False

async def broadcast(evt: dict):
    evt.setdefault("version", VERSION)
    evt.setdefault("ts", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    evt.setdefault("sentence_fr", make_sentence_fr(evt))

    # dédup simple dans une fenêtre de 5s
    s = sign_evt(evt)
    t = now_ts()
    if s in recent_signatures:
        idxs = [i for i, ss in enumerate(recent_signatures) if ss == s]
        if idxs and (t - recent_times[idxs[-1]] < DEDUP_WINDOW_SEC):
            debug_print("[DEDUP] drop:", evt)
            return
    recent_signatures.append(s)
    recent_times.append(t)

    payload = json.dumps(evt, ensure_ascii=False)
    async with WS_LOCK:
        clients = list(WS_CLIENTS)
    if not clients:
        return
    to_drop = []
    for ws in clients:
        try:
            await ws.send(payload)
        except Exception:
            to_drop.append(ws)
    if to_drop:
        async with WS_LOCK:
            for ws in to_drop:
                WS_CLIENTS.discard(ws)

def extract_driver(line: str) -> bool:
    """Capture des associations pilote->vaisseau."""
    for rx in (RE_DRIVER_A, RE_DRIVER_B, RE_DRIVER_C):
        m = rx.search(line)
        if m:
            driver = (m.group("driver") or "").strip()
            ship = (m.group("ship") or "").strip()
            if driver:
                drivers[driver] = DriverEntry(ship=ship, last_seen=now_ts())
                debug_print(f"[Driver] {driver} -> {ship}")
                return True
    return False

def is_entity_id(name: str) -> bool:
    """Détecte si c'est un ID d'entité plutôt qu'un nom de joueur"""
    if not name:
        return True
    # Les IDs d'entités contiennent souvent des underscores et des chiffres longs
    # Ex: ANVL_Arrow_651076209584, AEGS_Gladius_123456
    if '_' in name and any(char.isdigit() for char in name):
        # Vérifier si ça ressemble à un pattern d'entité
        parts = name.split('_')
        if len(parts) >= 2:
            # Si la dernière partie est un long nombre, c'est probablement un ID
            last_part = parts[-1]
            if last_part.isdigit() and len(last_part) > 8:
                return True
    return False

def clean_player_name(name: str) -> str:
    """Nettoie un nom de joueur pour éviter les problèmes avec les liens RSI"""
    if not name:
        return ""
    
    # Filtrer les IDs d'entités
    if is_entity_id(name):
        return ""
    
    # Normaliser les valeurs inconnues
    if name.strip().lower() in ("unknown", "inconnu", "none", "n/a"):
        return ""
    
    # Enlever les apostrophes et guillemets qui cassent les URLs
    name = name.replace("'", "").replace('"', '').replace('`', '')
    # Enlever les espaces en début/fin
    name = name.strip()
    return name

async def handle_actor_death_line(line: str) -> bool:
    # Essayer la regex spécifique Star Citizen en premier
    m = RE_SC_KILL.search(line)
    if m:
        victim_raw = (m.group("victim") or "").strip()
        killer_raw = (m.group("killer") or "").strip()
        victim_vehicle_raw = (m.group("victim_vehicle") or "").strip()
        weapon = (m.group("weapon") or "").strip()
        damage_type = (m.group("damage_type") or "").strip()
        cause = damage_type
        debug_print(f"[Parse SC] victim={victim_raw}, killer={killer_raw}, victim_vehicle={victim_vehicle_raw}, weapon={weapon}, damage={damage_type}")
    else:
        # Essayer les autres regex
        m = RE_KILL_EVENT.search(line)
        if not m:
            m = RE_DEATH_ALT.search(line)
        if not m:
            m = RE_ACTOR_DEATH.search(line)
        if not m:
            return False

        victim_raw = (m.group("victim") or "").strip()
        killer_raw = (m.group("killer") or "").strip() if "killer" in m.groupdict() else ""
        cause = (m.group("cause") or "").strip() if "cause" in m.groupdict() else None
        debug_print(f"[Parse] victim_raw={victim_raw}, killer_raw={killer_raw}")

    victim = clean_player_name(victim_raw)
    killer = clean_player_name(killer_raw) or None

    # Si le victim est filtré (ID d'entité), essayer d'utiliser le mapping drivers
    if not victim and victim_raw:
        debug_print(f"[Parse] Victim is entity ID, searching in drivers...")
        # Peut-être que c'est un ID de vaisseau, chercher le pilote
        for driver_name, entry in drivers.items():
            if entry.ship and victim_raw in entry.ship:
                victim = driver_name
                debug_print(f"[Parse] Found victim driver: {victim}")
                break
    
    # Même chose pour le killer
    if not killer and killer_raw:
        debug_print(f"[Parse] Killer is entity ID, searching in drivers...")
        for driver_name, entry in drivers.items():
            if entry.ship and killer_raw in entry.ship:
                killer = driver_name
                debug_print(f"[Parse] Found killer driver: {killer}")
                break

    debug_print(f"[Parse] Final: victim={victim}, killer={killer}")

    if not victim:
        debug_print(f"[Parse] No valid victim found, skipping event")
        return False

    prune_drivers()

    if killer and victim and killer.lower() == victim.lower():
        evt_type = "suicide"
    elif "suicide" in (cause or "").lower():
        evt_type = "suicide"
    elif not killer:
        # on ne sait pas qui -> "death" neutre
        evt_type = "death"
    else:
        evt_type = "kill"

    killer_ship = None
    victim_ship = None
    
    # Extraire le vaisseau de la victime depuis victim_vehicle_raw si disponible
    if 'victim_vehicle_raw' in locals() and victim_vehicle_raw:
        victim_ship = get_ship_display_name(victim_vehicle_raw)
    elif victim and victim in drivers:
        victim_ship = get_ship_display_name(drivers[victim].ship or "")
    
    # Extraire le vaisseau du tueur depuis weapon si c'est un ID de vaisseau
    if 'weapon' in locals() and weapon and '_' in weapon:
        # L'arme peut contenir l'ID du vaisseau
        killer_ship = get_ship_display_name(weapon)
    elif killer and killer in drivers:
        killer_ship = get_ship_display_name(drivers[killer].ship or "")

    evt = {
        "type": evt_type,
        "victim": victim,
        "killer": killer,
        "killer_ship": killer_ship,
        "victim_ship": victim_ship,
        "cause": cause,
        "raw": line.strip(),
    }
    await broadcast(evt)
    return True

async def handle_corpse_line(line: str) -> bool:
    """Détecte un cadavre et émet un kill si une destruction récente le précède."""
    global last_corpse, pending_vehicle_kills
    
    # Essayer d'abord le format Corpse avec killer
    m = RE_CORPSE.search(line)
    if m:
        victim = clean_player_name(m.group(1) or "")
        if victim:
            # Chercher une destruction récente à associer
            now = now_ts()
            linked = False
            if pending_vehicle_kills:
                # parcourir à rebours
                for i in range(len(pending_vehicle_kills)-1, -1, -1):
                    ts, killer, vehicle, damage_type, raw = pending_vehicle_kills[i]
                    if now - ts <= LINK_WINDOW_SEC:
                        # Déterminer le type d'événement
                        if killer and victim and killer.lower() == victim.lower():
                            evt_type = "suicide"
                        elif not killer:
                            evt_type = "death"
                        else:
                            evt_type = "kill"
                        
                        # Extraire les noms de vaisseaux
                        victim_ship = get_ship_display_name(vehicle)
                        killer_ship = get_killer_ship(killer)
                        
                        # Associer et émettre un kill
                        evt = {
                            "type": evt_type,
                            "victim": victim,
                            "killer": killer or None,
                            "victim_ship": victim_ship,
                            "killer_ship": killer_ship,
                            "cause": damage_type,
                            "raw": raw,
                        }
                        await broadcast(evt)
                        # retirer l'élément utilisé
                        try:
                            pending_vehicle_kills.remove((ts, killer, vehicle, damage_type, raw))
                        except ValueError:
                            pass
                        linked = True
                        debug_print(f"[Link] {victim} <=(destruction)=> {killer}")
                        break

            if not linked:
                # garder en mémoire si besoin pour d'autres formats
                last_corpse = (now, victim)
                debug_print(f"[Corpse] Stored without link: {victim}")
            return True
    
    # Essayer le format ActorState Corpse (pour identifier les victimes)
    m2 = RE_CORPSE_PLAYER.search(line)
    if m2:
        player_name = clean_player_name(m2.group("player") or "")
        if player_name:
            # Chercher une destruction récente à associer
            now = now_ts()
            if pending_vehicle_kills:
                # parcourir à rebours
                for i in range(len(pending_vehicle_kills)-1, -1, -1):
                    ts, killer, vehicle, damage_type, raw = pending_vehicle_kills[i]
                    if now - ts <= LINK_WINDOW_SEC:
                        # Déterminer le type d'événement
                        if killer and player_name and killer.lower() == player_name.lower():
                            evt_type = "suicide"
                        elif not killer:
                            evt_type = "death"
                        else:
                            evt_type = "kill"
                        
                        # Extraire les noms de vaisseaux
                        victim_ship = get_ship_display_name(vehicle)
                        killer_ship = get_killer_ship(killer)
                        
                        # Associer et émettre un kill
                        evt = {
                            "type": evt_type,
                            "victim": player_name,
                            "killer": killer or None,
                            "victim_ship": victim_ship,
                            "killer_ship": killer_ship,
                            "cause": damage_type,
                            "raw": raw,
                        }
                        await broadcast(evt)
                        # retirer l'élément utilisé
                        try:
                            pending_vehicle_kills.remove((ts, killer, vehicle, damage_type, raw))
                        except ValueError:
                            pass
                        debug_print(f"[Link ActorState] {player_name} <=(destruction)=> {killer}")
                        return True
            
            # Stocker pour un lien ultérieur
            last_corpse = (now, player_name)
            debug_print(f"[ActorState Corpse] Stored: {player_name}")
            return True
    
    return False

async def handle_hostility_line(line: str) -> bool:
    """Gère les événements d'hostilité et capture les associations attaquant->vaisseau"""
    global recent_attackers
    m = RE_HOSTILITY.search(line)
    if not m:
        return False
    
    attacker = clean_player_name(m.group("attacker") or "")
    target = clean_player_name(m.group("target_pilot") or "")
    target_vehicle_raw = m.group("target_vehicle") or ""
    
    if not attacker or not target:
        return False
    
    # Stocker l'association target -> vehicle (la cible pilote ce vaisseau)
    if target and target_vehicle_raw:
        drivers[target] = DriverEntry(ship=target_vehicle_raw, last_seen=now_ts())
        debug_print(f"[Hostility] Stored: {target} -> {target_vehicle_raw}")
    
    # Stocker l'attaquant dans le cache (on trouvera son vaisseau plus tard)
    # Quand il détruit un vaisseau, on pourra chercher dans ce cache
    if attacker:
        recent_attackers[attacker] = (now_ts(), "")
        debug_print(f"[Hostility] Attacker cached: {attacker}")

    evt = {
        "type": "hostility",
        "attacker": attacker,
        "target": target,
        "raw": line.strip(),
    }
    await broadcast(evt)
    return True

def get_killer_ship(killer: str) -> Optional[str]:
    """Trouve le vaisseau du tueur en cherchant dans les drivers et les attaquants récents"""
    if not killer:
        return None
    
    # 1. Chercher dans les drivers (associations pilote->vaisseau)
    if killer in drivers:
        return get_ship_display_name(drivers[killer].ship or "")
    
    # 2. Chercher dans les attaquants récents (depuis les hostilités)
    # Si le tueur a été vu récemment en train d'attaquer, on peut déduire son vaisseau
    # en cherchant les hostilités où il était la CIBLE (donc son vaisseau était mentionné)
    # Mais ça nécessiterait de stocker plus d'infos...
    
    # 3. Fallback: chercher dans les événements récents si le tueur a été victime
    # (son vaisseau serait alors connu)
    
    return None

async def handle_vehicle_destruction(line: str) -> bool:
    """Traite les destructions de véhicules et émet des événements de kill."""
    global pending_vehicle_kills, last_corpse, recent_attackers
    m = RE_VEHICLE_DESTRUCTION.search(line)
    if not m:
        return False

    vehicle = m.group("vehicle") or ""
    driver_raw = m.group("driver") or ""
    killer_raw = m.group("causer") or ""
    damage_type = m.group("damage_type") or "Combat"
    
    driver = clean_player_name(driver_raw)
    killer = clean_player_name(killer_raw)
    
    debug_print(f"[Vehicle Destruction] vehicle={vehicle}, driver={driver_raw}, killer={killer_raw}, damage={damage_type}")
    
    # Nettoyer le cache des attaquants (supprimer les entrées trop anciennes)
    now = now_ts()
    expired = [k for k, (ts, _) in recent_attackers.items() if now - ts > ATTACKER_CACHE_TTL]
    for k in expired:
        recent_attackers.pop(k, None)
    
    # Si le pilote est 'unknown', on attend un événement Corpse pour identifier la victime
    if not driver or driver_raw.lower() == 'unknown':
        # Empiler et attendre le corpse
        pending_vehicle_kills.append((now_ts(), killer or "", vehicle, damage_type, line.strip()))
        debug_print(f"[Vehicle Destruction] queued (unknown driver), killer={killer}")
        return True
    
    # Si on a un pilote identifié, émettre directement le kill
    victim = driver
    
    # Déterminer le type d'événement
    if killer and victim and killer.lower() == victim.lower():
        evt_type = "suicide"
    elif not killer:
        evt_type = "death"
    else:
        evt_type = "kill"
    
    # Extraire les noms de vaisseaux
    victim_ship = get_ship_display_name(vehicle)
    killer_ship = get_killer_ship(killer)
    
    evt = {
        "type": evt_type,
        "victim": victim,
        "killer": killer or None,
        "victim_ship": victim_ship,
        "killer_ship": killer_ship,
        "cause": damage_type,
        "raw": line.strip(),
    }
    await broadcast(evt)
    debug_print(f"[Vehicle Destruction] Emitted: {victim} killed by {killer} (killer_ship: {killer_ship})")
    return True

# ===================== TAIL THREAD =====================

class TailThread(threading.Thread):
    def __init__(self, path: str, loop: asyncio.AbstractEventLoop, q: "asyncio.Queue[str]"):
        super().__init__(daemon=True)
        self.path = path
        self.loop = loop
        self.q = q
        self.stop_flag = False
        log_print(f"[Tail] Initialized for path: {self.path}")

    def run(self):
        path = self.path
        last_size = 0
        f = None

        while not self.stop_flag:
            try:
                if not os.path.exists(path):
                    log_print(f"[Tail] ERREUR: Le fichier n'existe pas à l'emplacement: {path}")
                    time.sleep(5.0)
                    if self.stop_flag:
                        return

                if f is None:
                    f = open(path, "r", encoding="utf-8", errors="ignore")
                    # Lire la fin du fichier pour l'historique récent
                    file_size = os.path.getsize(path)
                    read_offset = max(0, file_size - 500 * 1024) # Lire les derniers 500KB
                    f.seek(read_offset)
                    if read_offset > 0:
                        f.readline() # Ignorer la première ligne potentiellement incomplète

                    log_print(f"[Tail] Lecture de l'historique récent ({read_offset} à {file_size} octets)... ")
                    lines_read = 0
                    for line in f:
                        if DEBUG:
                            log_print(f"[Tail History] {line.strip()}")
                        self.loop.call_soon_threadsafe(self.q.put_nowait, line)
                        lines_read += 1
                    log_print(f"[Tail] {lines_read} lignes lues depuis l'historique.")
                    
                    last_size = f.tell()
                    log_print(f"[Tail] Lecture de l'historique terminée. Suivi des nouvelles lignes à partir de {last_size} octets.")

                line = f.readline()
                if line and DEBUG:
                    log_print(f"[Tail New] {line.strip()}")

                if not line:
                    # rotation / troncature ?
                    try:
                        size = os.path.getsize(path)
                    except Exception:
                        size = last_size
                    if size < last_size:
                        debug_print("[Tail] Fichier tronqué/roté, reopen.")
                        f.close()
                        f = None
                        last_size = 0
                        continue
                    time.sleep(0.15)
                    continue

                last_size = f.tell()
                # push dans la queue asyncio
                self.loop.call_soon_threadsafe(self.q.put_nowait, line)
            except Exception as e:
                debug_print("[Tail] erreur:", e)
                time.sleep(0.5)

        try:
            if f:
                f.close()
        except Exception:
            pass

# ===================== HTTP =====================

class NoCacheHandler(SimpleHTTPRequestHandler):
    """Sert les fichiers du dossier courant + /config.js dynamique, sans cache."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        # log plus discret
        if DEBUG:
            sys.stderr.write("[HTTP] " + format % args + "\n")

    def do_GET(self):
        if self.path == "/config.js":
            # config pour le client web
            ws_url = f"ws://{WS_HOST}:{WS_PORT}"
            payload = (
                "window.KF = "
                + json.dumps({
                    "version": VERSION,
                    "ws_url": ws_url,
                    "player_name": PLAYER_NAME,
                }, ensure_ascii=False)
                + ";"
            )
            data = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        return super().do_GET()

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_http_server():
    """Lance le serveur HTTP en essayant plusieurs ports, puis 0 (aléatoire)."""
    global HTTP_PORT_SELECTED
    try:
        os.chdir(BASE_DIR)
    except Exception:
        pass

    candidates = []
    if HTTP_PORT not in (None, 0):
        candidates.append(HTTP_PORT)
    # ports “inoffensifs”
    candidates += [8081, 8888, 8000, 0]  # 0 => OS choisit un port autorisé

    last_err = None
    for p in candidates:
        try:
            with ReusableTCPServer((HTTP_HOST, p), NoCacheHandler) as httpd:
                HTTP_PORT_SELECTED = httpd.server_address[1]
                log_print(f"[HTTP] listening on http://{HTTP_HOST}:{HTTP_PORT_SELECTED}")
                HTTP_READY.set()
                try:
                    httpd.serve_forever()
                finally:
                    httpd.server_close()
                return
        except (PermissionError, OSError) as e:
            last_err = e
            log_print(f"[HTTP] bind failed on {HTTP_HOST}:{p} -> {e}")

    log_print(f"[HTTP] Failed to start HTTP server: {last_err}")
    HTTP_READY.set()  # évite de bloquer l'ouverture du navigateur

# ===================== WEBSOCKET =====================

async def ws_handler(ws):
    """Handler WebSocket compatible avec websockets 15.0+"""
    async with WS_LOCK:
        WS_CLIENTS.add(ws)
    try:
        hello = {
            "type": "hello",
            "version": VERSION,
            "server_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "player_name": PLAYER_NAME or None,
        }
        await ws.send(json.dumps(hello, ensure_ascii=False))

        async for _ in ws:
            # Le client peut ignorer: on ne traite pas de messages entrants
            pass
    except Exception:
        if DEBUG:
            traceback.print_exc()
    finally:
        async with WS_LOCK:
            WS_CLIENTS.discard(ws)

async def ws_server():
    server = await websockets.serve(
        ws_handler, WS_HOST, WS_PORT, ping_interval=20, ping_timeout=20
    )
    log_print(f"[WS] listening on ws://{WS_HOST}:{WS_PORT}")
    await asyncio.Future()  # run forever

# ===================== PARSE LOOP =====================

async def parse_loop(line_q: "asyncio.Queue[str]"):
    while True:
        line = await line_q.get()
        debug_print(f"[Parse] Received line: {line.strip()}")
        try:
            # D'abord, capter les infos conducteur->vaisseau
            if extract_driver(line):
                continue

            # 1) Corpse (stocke la victime potentielle)
            if await handle_corpse_line(line):
                continue

            # 2) Vehicle Destruction (tente de lier à un cadavre)
            if await handle_vehicle_destruction(line):
                continue

            # 3) Actor death (format plus ancien)
            if await handle_actor_death_line(line):
                continue

            # 4) Hostility events
            if await handle_hostility_line(line):
                continue

            # 4) (Optionnel) autres messages "info"
            if DEBUG and ("GET /" in line or "HTTP/1.1" in line):
                await broadcast({
                    "type": "info",
                    "message": line.strip()
                })

        except Exception as e:
            if DEBUG:
                traceback.print_exc()
            else:
                print(f"[Parse] error: {e}", file=sys.stderr)

# ===================== ENTRY =====================

async def main_async():
    # HTTP server (thread)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Files tailer (thread) + parse loop (task)
    line_q: asyncio.Queue[str] = asyncio.Queue(maxsize=4096)
    loop = asyncio.get_running_loop()
    tail = TailThread(LOG_PATH, loop, line_q)
    tail.start()

    # WS server (task)
    ws_task = asyncio.create_task(ws_server())
    parse_task = asyncio.create_task(parse_loop(line_q))

    # Ouvrir navigateur une fois le HTTP prêt (ou après 5s max)
    if AUTO_OPEN_BROWSER:
        def _open():
            try:
                HTTP_READY.wait(5)
                port = HTTP_PORT_SELECTED or HTTP_PORT or 8080
                url = f"http://{HTTP_HOST}:{port}/"
                time.sleep(0.3)
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    log_print(f"[KILLFEED] Log file: {LOG_PATH}")
    log_print("[KILLFEED] Press Ctrl+C to stop.")
    try:
        await asyncio.gather(ws_task, parse_task)
    except asyncio.CancelledError:
        pass
    finally:
        tail.stop_flag = True

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()