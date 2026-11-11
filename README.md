# DEADFRAME

![DEADFRAME](logo/DEADFRAME-logo.png)

FPS « bodycam » : caméra de poitrine fisheye, visée libre sans viseur, drone de reconnaissance, bots, multijoueur LAN. Prototype sans moteur externe (WebGL2 + Go).

## Jouer
- **Dans le navigateur (solo contre les bots)** : GitHub Pages sert `index.html` à la racine du dépôt.
- **Multijoueur** : télécharger [`download/DEADFRAME.exe`](download/DEADFRAME.exe) (Windows 64 bits). Il démarre un serveur sur le port 7777, ouvre le jeu et affiche l'adresse à donner aux amis du même réseau (ex. `http://192.168.1.20:7777`). Eux n'ont besoin que d'un navigateur.
  - Premier lancement : autoriser le pare-feu ; SmartScreen peut avertir (exe non signé) → « Informations complémentaires » → « Exécuter quand même ».
  - Options : `DEADFRAME.exe -port 9000 -noopen` (serveur dédié).

## Cartes
Dépôt industriel · Hôpital abandonné · Tranchées · Hôtel — choix dans le menu (en multijoueur, c'est l'hôte qui choisit).

## Commandes (clavier AZERTY)
ZQSD déplacement · Maj sprint · Espace saut · C accroupi · A/E se pencher · clic gauche tir · clic droit visée · R recharger · 1–4 arme (HK416, AKS-74, AKM, P43) · V inspecter l'arme · F lampe · G drone · Tab scores · Échap menu.

**Drone FPV** (physique de quadricoptère) : Z/S tangage · Q/D roulis · A/E ou souris lacet · Espace/C gaz · T bascule ASSISTÉ (stabilisé, maintien d'altitude) / ACRO (taux purs, gaz manuels) · G rendre la main · F rappel. Un choc à plus de ~30 km/h détruit le drone.

**Manette** (Xbox / PlayStation, disposition standard) : stick gauche bouger · stick droit viser · RT tir · LT visée · A saut · B accroupi · X recharger · Y arme suivante (mode de vol en drone) · LB/RB se pencher · L3 sprint · R3 inspecter · croix ↑ drone, ↓ lampe, ←/→ arme · Start menu · Select scores. En drone : mode 2 (gaz/lacet à gauche, tangage/roulis à droite).

Le point rouge à l'écran montre où pointe réellement le canon (désactivable dans le menu : « Point de visée »).

## Connexion Discord
Le menu « Opérateur » propose « Se connecter avec Discord » (OAuth2 *implicit grant*, scope `identify` : pseudo et avatar, aucun secret dans le jeu).
1. Créer une application sur https://discord.com/developers/applications.
2. Dans OAuth2 → Redirects, ajouter l'adresse exacte du jeu : `https://haze15.github.io/DEADFRAME/` et/ou `http://localhost:7777/`.
3. Coller l'ID d'application (Client ID) dans le menu, ou le mettre dans la constante `DISCORD_CLIENT_ID` de `src/game.html` pour que tous les joueurs l'aient.
Limites : le pseudo n'est pas vérifié par le serveur de jeu (un joueur peut toujours taper un autre indicatif) ; ne fonctionne pas dans une page intégrée (iframe).

## Performances
Qualité « Automatique » : la résolution interne s'ajuste pour viser 60 i/s (affichée en haut à droite avec les i/s). Seules les lumières proches de la caméra sont calculées, les personnages lointains passent sur un modèle allégé, ceux hors champ ne sont pas dessinés.

## Modèles libres repérés pour une future refonte (à télécharger puis à fournir, ils ne sont pas dans le dépôt)
- Quaternius — Universal Animation Library (CC0, glTF, locomotion 8 directions, sprint, morts…) : https://quaternius.com/packs/universalanimationlibrary.html
- Styloo — Guns Asset Pack (CC0, glTF) : https://styloo.itch.io/guns-asset-pack
- Poly Pizza — FPS pack (bras FPS riggés et animés) : https://poly.pizza/bundle/FPS-pack-QKgLgzmIZ2
- Kenney — Building Kit et Modular Buildings (CC0, glTF) : https://kenney-assets.itch.io/building-kit · https://kenney-assets.itch.io/modular-buildings

## Structure
| Chemin | Rôle |
|---|---|
| `index.html` | Le jeu, généré depuis `src/game.html` par `src/build.py` |
| `assets/` | Modèles `.dfm` + textures, générés par `tools/convert.py` depuis les `.glb` d'origine |
| `src/game.html` | Tout le jeu : moteur WebGL2, shaders, IA, audio, réseau |
| `main.go` | Serveur HTTP + relais WebSocket (bibliothèque standard), embarque `index.html` et `assets/` |
| `tools/convert.py` | Convertisseur glTF → `.dfm` (décimation, squelette, animations) |
| `logo/` | Logo et icône |

## Compiler
```
python3 src/build.py
GOOS=windows GOARCH=amd64 go build -trimpath -ldflags "-s -w" -o download/DEADFRAME.exe .
```

## Limites connues
- Rendu stylisé (décors en blocs, textures procédurales, pas d'ombres portées).
- Le soldat n'a pas de squelette d'origine : un squelette de 11 os est généré automatiquement (`tools/convert.py`) et animé par le jeu (marche, visée, accroupi) ; les épaules se déforment un peu.
- AKM : seul le fusil est utilisé (les bras du fichier d'origine sont inexploitables) ; l'AKS-74 a ses bras et animations d'origine.
- Réseau : relais simple, dégâts déclarés par le tireur (pas d'anti-triche). Par Internet : rediriger le port 7777 ou VPN type LAN.

## Crédits
Modèles 3D sous licence CC BY 4.0 — voir [CREDITS.md](CREDITS.md).
