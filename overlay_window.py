# -*- coding: utf-8 -*-
"""
KillFeedSC - Overlay Window
Overlay transparent Tkinter pour afficher le kill feed par-dessus Star Citizen
"""

import tkinter as tk
from tkinter import font as tkfont
import asyncio
import websockets
import json
import threading
import sys
from datetime import datetime
from collections import deque
from typing import Optional, Dict, List
import time

# Configuration
WS_URL = "ws://127.0.0.1:8765"
MAX_KILLS_DISPLAY = 10
OVERLAY_WIDTH = 450
OVERLAY_HEIGHT = 400
FADE_DURATION = 300  # ms

class KillEntry:
    """Représente une entrée de kill dans l'overlay"""
    def __init__(self, text: str, color: str, timestamp: float):
        self.text = text
        self.color = color
        self.timestamp = timestamp
        self.alpha = 1.0

class KillFeedOverlay:
    """Overlay transparent pour afficher le kill feed"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.kills: deque[KillEntry] = deque(maxlen=MAX_KILLS_DISPLAY)
        self.ws = None
        self.running = True
        self.connected = False
        self.player_name = ""
        
        self._setup_window()
        self._setup_canvas()
        self._setup_keybindings()
        
        # Démarrer la boucle WebSocket dans un thread
        self.ws_thread = threading.Thread(target=self._run_websocket_loop, daemon=True)
        self.ws_thread.start()
        
        # Démarrer la mise à jour de l'affichage
        self._update_display()
        
    def _setup_window(self):
        """Configure la fenêtre overlay"""
        # Pas de bordures
        self.root.overrideredirect(True)
        
        # Always on top
        self.root.attributes('-topmost', True)
        
        # Transparence
        self.root.attributes('-alpha', 0.95)
        
        # Fond transparent (noir = transparent)
        self.root.attributes('-transparentcolor', 'black')
        
        # Position (coin supérieur droit)
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - OVERLAY_WIDTH - 20
        y_pos = 20
        self.root.geometry(f'{OVERLAY_WIDTH}x{OVERLAY_HEIGHT}+{x_pos}+{y_pos}')
        
        # Fond noir (sera transparent)
        self.root.configure(bg='black')
        
        # Titre (pour le gestionnaire de tâches)
        self.root.title("KillFeedSC Overlay")
        
    def _setup_canvas(self):
        """Configure le canvas pour dessiner les kills"""
        self.canvas = tk.Canvas(
            self.root,
            bg='black',
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Police
        self.font_kill = tkfont.Font(family='Segoe UI', size=11, weight='bold')
        self.font_small = tkfont.Font(family='Segoe UI', size=9)
        
    def _setup_keybindings(self):
        """Configure les raccourcis clavier"""
        # F12 pour masquer/afficher
        self.root.bind('<F12>', lambda e: self._toggle_visibility())
        
        # Ctrl+Q pour quitter
        self.root.bind('<Control-q>', lambda e: self.quit())
        
        # Escape pour quitter
        self.root.bind('<Escape>', lambda e: self.quit())
        
    def _toggle_visibility(self):
        """Masque/affiche l'overlay"""
        current_alpha = self.root.attributes('-alpha')
        if current_alpha > 0.1:
            self.root.attributes('-alpha', 0.0)
        else:
            self.root.attributes('-alpha', 0.95)
    
    def _format_kill_text(self, evt: Dict) -> tuple[str, str]:
        """Formate le texte d'un kill et retourne (texte, couleur)"""
        evt_type = evt.get('type', 'kill')
        victim = evt.get('victim', 'Unknown')
        killer = evt.get('killer')
        victim_ship = evt.get('victim_ship', '')
        killer_ship = evt.get('killer_ship', '')
        
        # Couleurs selon le type (plus lumineuses et éclatantes)
        if evt_type == 'suicide':
            color = '#ff4757'  # Rouge vif
            if victim_ship:
                text = f"💀 {victim} ({victim_ship}) - Suicide"
            else:
                text = f"💀 {victim} - Suicide"
                
        elif evt_type == 'death':
            color = '#c8d6e5'  # Gris clair lumineux
            if victim_ship:
                text = f"☠️ {victim} ({victim_ship}) - Mort"
            else:
                text = f"☠️ {victim} - Mort"
                
        else:  # kill
            # Vérifier si le joueur local est impliqué
            is_player_kill = (self.player_name and killer and 
                            killer.lower() == self.player_name.lower())
            is_player_death = (self.player_name and victim and 
                             victim.lower() == self.player_name.lower())
            
            if is_player_kill:
                color = '#00ff88'  # Vert néon (votre kill)
            elif is_player_death:
                color = '#ff4757'  # Rouge vif (votre mort)
            else:
                color = '#00ffff'  # Cyan électrique (kill normal)
            
            # Construire le texte
            killer_text = killer or 'Unknown'
            if killer_ship:
                killer_text = f"{killer_text} ({killer_ship})"
            
            victim_text = victim
            if victim_ship:
                victim_text = f"{victim_text} ({victim_ship})"
            
            text = f"⚔️ {killer_text} → {victim_text}"
        
        return text, color
    
    def add_kill(self, evt: Dict):
        """Ajoute un kill à l'overlay"""
        text, color = self._format_kill_text(evt)
        entry = KillEntry(text, color, time.time())
        self.kills.appendleft(entry)  # Ajouter en haut
        
    def _update_display(self):
        """Met à jour l'affichage du canvas"""
        if not self.running:
            return
        
        # Effacer le canvas
        self.canvas.delete('all')
        
        # Nettoyer les kills trop vieux (> 30 secondes)
        current_time = time.time()
        while self.kills and (current_time - self.kills[-1].timestamp) > 30:
            self.kills.pop()  # Supprimer le plus vieux
        
        # Afficher l'indicateur de connexion (très discret)
        if self.connected:
            self.canvas.create_text(
                10, 10,
                text="●",
                fill='#28ffa7',
                font=self.font_small,
                anchor='nw'
            )
        else:
            self.canvas.create_text(
                10, 10,
                text="●",
                fill='#ffa726',
                font=self.font_small,
                anchor='nw'
            )
        
        # Afficher les kills
        y_offset = 40
        line_height = 35
        
        for i, kill in enumerate(self.kills):
            if i >= MAX_KILLS_DISPLAY:
                break
            
            # Fade out progressif pour les kills qui approchent 30 secondes
            age = current_time - kill.timestamp
            if age > 25:
                # Fade out sur les 5 dernières secondes
                alpha = max(0.0, 1.0 - (age - 25) / 5)
            else:
                alpha = 1.0
            
            # Ne pas afficher si complètement transparent
            if alpha < 0.05:
                continue
            
            # Calculer la couleur avec alpha
            color = kill.color
            if alpha < 1.0:
                # Simuler l'alpha en mélangeant avec le noir
                color = self._blend_color(color, alpha)
            
            # Dessiner le texte (sans ombre)
            self.canvas.create_text(
                10, y_offset + (i * line_height),
                text=kill.text,
                fill=color,
                font=self.font_kill,
                anchor='nw'
            )
        
        # Afficher les instructions en bas (très discret) seulement si aucun kill
        if len(self.kills) == 0:
            self.canvas.create_text(
                OVERLAY_WIDTH // 2, OVERLAY_HEIGHT // 2,
                text="En attente de kills...\n\nF12: Masquer/Afficher\nEsc: Quitter",
                fill='#4a5568',
                font=self.font_small,
                anchor='center',
                justify='center'
            )
        
        # Rafraîchir toutes les 100ms
        self.root.after(100, self._update_display)
    
    def _blend_color(self, hex_color: str, alpha: float) -> str:
        """Mélange une couleur avec le noir selon l'alpha"""
        # Convertir hex en RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Mélanger avec noir (0, 0, 0)
        r = int(r * alpha)
        g = int(g * alpha)
        b = int(b * alpha)
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _run_websocket_loop(self):
        """Boucle WebSocket dans un thread séparé"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._websocket_client())
    
    async def _websocket_client(self):
        """Client WebSocket pour recevoir les kills"""
        while self.running:
            try:
                async with websockets.connect(WS_URL) as ws:
                    self.ws = ws
                    self.connected = True
                    print(f"[Overlay] Connecté à {WS_URL}")
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            
                            # Récupérer le nom du joueur depuis le hello
                            if data.get('type') == 'hello':
                                self.player_name = data.get('player_name', '')
                                print(f"[Overlay] Joueur: {self.player_name}")
                            
                            # Traiter les événements de kill
                            elif data.get('type') in ('kill', 'death', 'suicide'):
                                self.add_kill(data)
                                
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            print(f"[Overlay] Erreur traitement message: {e}")
                            
            except Exception as e:
                self.connected = False
                print(f"[Overlay] Erreur WebSocket: {e}")
                await asyncio.sleep(2)  # Attendre avant de reconnecter
    
    def quit(self):
        """Ferme l'overlay proprement"""
        print("[Overlay] Fermeture...")
        self.running = False
        if self.ws:
            try:
                asyncio.run(self.ws.close())
            except:
                pass
        self.root.quit()
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Lance la boucle principale Tkinter"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit()

def main():
    """Point d'entrée principal"""
    print("=" * 50)
    print("KillFeedSC - Overlay Window")
    print("=" * 50)
    print()
    print("Configuration requise:")
    print("  - Star Citizen en mode Borderless Window")
    print("  - Serveur KillFeedSC lancé (kill_feed_local.py)")
    print()
    print("Raccourcis:")
    print("  F12  : Masquer/Afficher l'overlay")
    print("  Esc  : Quitter")
    print()
    print("Démarrage de l'overlay...")
    print()
    
    overlay = KillFeedOverlay()
    overlay.run()

if __name__ == "__main__":
    main()
