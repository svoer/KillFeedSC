# 🎮 KillFeedSC - Overlay Mode

## Qu'est-ce que l'overlay ?

L'overlay est une fenêtre transparente qui s'affiche **par-dessus Star Citizen** pendant que vous jouez. Il affiche en temps réel les kills, morts et suicides de tous les joueurs sur le serveur.

## ✨ Caractéristiques

- ✅ **Transparent** - Seules les lignes de kill sont visibles
- ✅ **Always-on-top** - Reste visible par-dessus le jeu
- ✅ **Temps réel** - Affichage instantané via WebSocket
- ✅ **Léger** - Aucun impact sur les performances du jeu
- ✅ **Personnalisable** - Couleurs selon le type d'événement
- ✅ **Discret** - Fade out automatique des vieux kills

## 🎯 Prérequis

### Star Citizen DOIT être en mode Borderless Window

**IMPORTANT** : L'overlay ne fonctionne PAS en mode plein écran exclusif.

**Configuration requise :**

1. Lancer Star Citizen
2. Aller dans **Options > Graphics**
3. Changer **Window Mode** de `Fullscreen` vers `Windowed (Borderless)`
4. Cliquer sur **Apply**
5. Redémarrer le jeu si nécessaire

## 🚀 Lancement

### Méthode 1 : Script automatique (RECOMMANDÉ)

Double-cliquez sur `start_overlay.bat`

Le script va :
1. Lancer le serveur KillFeedSC
2. Attendre 3 secondes
3. Lancer l'overlay transparent

### Méthode 2 : Manuel

```bash
# Terminal 1 - Lancer le serveur
python kill_feed_local.py

# Terminal 2 - Lancer l'overlay
python overlay_window.py
```

## 🎨 Affichage

### Couleurs des événements

- 🟢 **Vert néon** (`#00ff88`) - Vos kills
- 🔴 **Rouge vif** (`#ff4757`) - Vos morts ou suicides
- 🔵 **Cyan électrique** (`#00ffff`) - Kills d'autres joueurs
- ⚪ **Gris lumineux** (`#c8d6e5`) - Morts sans tueur identifié

### Durée d'affichage

- Les kills restent affichés pendant **30 secondes**
- Fade out progressif sur les 5 dernières secondes (25-30s)
- Disparition automatique après 30 secondes

### Format d'affichage

```
⚔️ Killer (Ship) → Victim (Ship)
💀 Player (Ship) - Suicide
☠️ Player (Ship) - Mort
```

### Exemples

```
⚔️ Dash-Hyphen → Temperr (Arrow)
⚔️ Jennesse (Blade) → Slime_Pike (L21 Wolf)
💀 VHALAR (Arrow) - Suicide
```

## ⌨️ Raccourcis clavier

- **F12** - Masquer/Afficher l'overlay
- **Esc** - Quitter l'overlay
- **Ctrl+Q** - Quitter l'overlay

## 🔧 Configuration

Éditez `config.ini` pour personnaliser l'overlay :

```ini
[OVERLAY]
POSITION=top-right        # Position (top-right, top-left, bottom-right, bottom-left)
WIDTH=450                 # Largeur en pixels
HEIGHT=400                # Hauteur en pixels
MAX_KILLS=10              # Nombre maximum de kills affichés
ALPHA=0.95                # Transparence (0.0 = invisible, 1.0 = opaque)
```

## 📍 Position de l'overlay

Par défaut, l'overlay est positionné dans le **coin supérieur droit** de l'écran.

Vous pouvez changer la position en modifiant `POSITION` dans `config.ini` :

- `top-right` - Coin supérieur droit (défaut)
- `top-left` - Coin supérieur gauche
- `bottom-right` - Coin inférieur droit
- `bottom-left` - Coin inférieur gauche

## 🐛 Dépannage

### L'overlay ne s'affiche pas

1. Vérifiez que Star Citizen est en mode **Borderless Window**
2. Vérifiez que le serveur KillFeedSC est lancé
3. Vérifiez que le port WebSocket 8765 n'est pas bloqué

### L'overlay est caché par le jeu

- Star Citizen est probablement en mode **Fullscreen exclusif**
- Changez vers **Borderless Window** dans les options graphiques

### Les kills n'apparaissent pas

1. Vérifiez que le serveur lit bien le fichier `Game.log`
2. Vérifiez le chemin dans `config.ini` : `GAME_LOG_PATH`
3. Regardez les logs du serveur pour voir si les événements sont détectés

### L'overlay est trop transparent/opaque

Modifiez `ALPHA` dans `config.ini` :
- `0.5` - Très transparent
- `0.8` - Transparent moyen
- `0.95` - Presque opaque (défaut)
- `1.0` - Complètement opaque

### Performance / FPS drops

L'overlay est très léger (< 5% CPU, < 50 MB RAM), mais si vous avez des problèmes :

1. Réduisez `MAX_KILLS` dans `config.ini` (ex: 5 au lieu de 10)
2. Augmentez `ALPHA` pour réduire les calculs de transparence
3. Fermez l'overlay avec `F12` pendant les combats intenses

## 💡 Conseils d'utilisation

### Pour les streamers

L'overlay est parfait pour le streaming :
- Transparent et discret
- Affichage en temps réel
- Pas besoin de capture OBS supplémentaire

### Pour le PvP

- Positionnez l'overlay dans un coin non-critique
- Utilisez `F12` pour masquer temporairement
- Réduisez `MAX_KILLS` à 5 pour moins de distraction

### Pour l'immersion

- Réduisez `ALPHA` à 0.7 pour plus de transparence
- Positionnez en `bottom-right` pour être moins visible
- Les kills disparaissent automatiquement après 30 secondes

## 🔄 Mise à jour

Pour mettre à jour l'overlay :

```bash
git pull origin main
```

Puis relancez `start_overlay.bat`

## 📝 Notes techniques

- **Technologie** : Python Tkinter (natif, pas de dépendances lourdes)
- **Communication** : WebSocket (ws://127.0.0.1:8765)
- **Performance** : ~5% CPU, ~50 MB RAM
- **Compatibilité** : Windows 10/11, Python 3.8+

## ❓ FAQ

**Q: L'overlay fonctionne-t-il en plein écran ?**  
R: Non, uniquement en mode Borderless Window.

**Q: Puis-je cliquer à travers l'overlay ?**  
R: Actuellement non, mais c'est prévu dans une future version.

**Q: L'overlay affiche-t-il les kills de tous les joueurs ?**  
R: Oui ! Tous les kills du serveur sont affichés, pas seulement les vôtres.

**Q: Le pseudo dans config.ini filtre-t-il les kills ?**  
R: Non, il sert uniquement à colorer VOS kills en vert et vos morts en rouge.

**Q: Puis-je utiliser l'overlay ET l'interface web ?**  
R: Oui ! Vous pouvez avoir les deux en même temps.

## 🆘 Support

Si vous rencontrez des problèmes :

1. Vérifiez ce README
2. Consultez les issues GitHub
3. Créez une nouvelle issue avec :
   - Votre configuration (Windows version, résolution)
   - Le contenu de `config.ini`
   - Les logs du serveur
   - Une capture d'écran si possible

---

**Bon jeu et bon hunt ! 🎯**
