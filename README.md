# DEADFRAME

![DEADFRAME](logo/DEADFRAME-logo.png)

FPS « bodycam » : caméra de poitrine fisheye, visée libre sans viseur, drone de reconnaissance, bots, multijoueur LAN. Prototype sans moteur externe (WebGL2 + Go).

## Jouer
- **Dans le navigateur (solo contre les bots)** : GitHub Pages sert `index.html` à la racine du dépôt.
- **Multijoueur** : télécharger [`download/DEADFRAME.exe`](download/DEADFRAME.exe) (Windows 64 bits). Il démarre un serveur sur le port 7777, ouvre le jeu et affiche l'adresse à donner aux amis du même réseau (ex. `http://192.168.1.20:7777`). Eux n'ont besoin que d'un navigateur.
  - Premier lancement : autoriser le pare-feu ; SmartScreen peut avertir (exe non signé) → « Informations complémentaires » → « Exécuter quand même ».
  - Options : `DEADFRAME.exe -port 9000 -noopen` (serveur dédié).

## Menu principal
- **DEPLOY** : zone d'opération (la scène en arrière-plan suit la carte choisie), nombre d'hostiles, adresse réseau à donner aux amis, bouton Déployer (ou Entrée).
- **LOADOUT** : arme en main à chaque insertion (les quatre restent accessibles en jeu avec 1–4) et dotation fixe.
- **OPERATORS** : indicatif, niveau, grade, états de service, connexion Discord.
- **MISSIONS** : 12 contrats permanents suivis sur toutes les parties (éliminations par arme, par carte, tirs à la tête, série, temps de vol du drone), chacun récompensé en XP.
- **SETTINGS** : affichage, contrôles, audio, touches, crédits.
- **QUIT** : en partie, « Quitter la partie » ramène au menu ; « Quitter le jeu » ferme la fenêtre et, avec `DEADFRAME.exe`, arrête aussi le serveur (uniquement depuis le PC qui l'héberge).
- Progression : 100 XP par élimination, +50 à la tête, plus les contrats. Grades de Recrue (niv. 1) à Major (niv. 42). Enregistrée dans le navigateur (localStorage) : elle ne suit pas d'un navigateur ou d'un PC à l'autre.
- Navigation : souris, ↑/↓ + Entrée, ou croix de la manette + A.

## Cartes
Dépôt industriel · Hôpital abandonné · Tranchées · Hôtel — choix dans le menu (en multijoueur, c'est l'hôte qui choisit).

## Commandes (clavier AZERTY)
ZQSD déplacement · Maj sprint · Espace saut · C accroupi · A/E se pencher · clic gauche tir · clic droit visée · R recharger · 1–4 arme (HK416, AKS-74, AKM, P43) · V inspecter l'arme · F lampe · G drone · Tab scores · Échap menu.

**Munitions** : aucun compteur à l'écran. R bref = recharger ; R maintenu = l'arme se penche et le compte s'affiche à côté d'elle (X maintenu à la manette). Aucun viseur ni point de visée : seuls les organes de visée comptent.

**Drone de reconnaissance « CORBEAU-1 »** (physique : inertie, accélération limitée, traînée, vent, effet de sol, châssis qui s'incline pour accélérer ; caméra sur nacelle stabilisée) :
- G : lancer le drone depuis la main, puis prendre ou rendre le contrôle (le drone tient sa position).
- ZQSD déplacement · Espace monter · Ctrl (ou C) descendre · Maj accélérer · souris : cap et inclinaison de la caméra · molette ou +/− : zoom ×1 à ×8 · F : rappel automatique · Échap : quitter le mode drone (un clic reprend).
- Télémétrie : identité, état, structure, cap, altitude (et hauteur sol), vitesse, batterie (tension, autonomie estimée), liaison (qualité, RSSI, distance, vue directe), caméra (EO, zoom, inclinaison, REC), cibles visibles.
- Liaison : elle baisse avec la distance et les obstacles ; perdue, le drone revient seul vers l'opérateur. Batterie critique : atterrissage automatique.
- Dégâts : tirs des joueurs et des bots (qui repèrent et entendent les drones), chocs contre le décor. À 0 % le drone part en chute, puis explose à l'impact (flash, boule de feu, fumée, éclats, débris, onde de choc, brûlure, feu résiduel, son retardé selon la distance, secousse si l'opérateur est proche). Délai de 20 s avant un nouveau drone.
- L'explosion est un effet visuel et sonore : elle n'inflige aucun dégât.
- Clavier QWERTY : utilise C plutôt que Ctrl pour descendre (Ctrl+W ferme l'onglet et le navigateur ne permet pas de l'empêcher).

**Manette** (Xbox / PlayStation, disposition standard) : stick gauche bouger · stick droit viser · RT tir · LT visée · A saut · B accroupi · X recharger (maintenu : chargeur) · Y arme suivante · LB/RB se pencher · L3 sprint · R3 inspecter · croix ↑ drone, ↓ lampe, ←/→ arme · Start menu · Select scores. En drone : stick gauche déplacement · stick droit caméra · RT/LT monter/descendre · L3 accélérer · croix ←/→ zoom · ↓ rappel · B quitter.

## Connexion Discord
Le menu « Opérateur » propose « Se connecter avec Discord » (OAuth2 *implicit grant*, scope `identify` : pseudo et avatar, aucun secret dans le jeu).
1. Créer une application sur https://discord.com/developers/applications.
2. Dans OAuth2 → Redirects, ajouter l'adresse exacte du jeu : `https://haze15.github.io/DEADFRAME/` et/ou `http://localhost:7777/`.
3. Coller l'ID d'application (Client ID) dans le menu, ou le mettre dans la constante `DISCORD_CLIENT_ID` de `src/game.html` pour que tous les joueurs l'aient.
Limites : le pseudo n'est pas vérifié par le serveur de jeu (un joueur peut toujours taper un autre indicatif) ; ne fonctionne pas dans une page intégrée (iframe).

## Performances
Qualité « Automatique » : la résolution interne s'ajuste pour viser 60 i/s.

**Champ de vision** : seul ce que la caméra voit est dessiné. La carte est découpée en secteurs de 12 m (les très grands blocs — sol, murs d'enceinte, toits — forment leur propre secteur) ; à chaque image, la pyramide de vision exacte de la caméra (champ, inclinaison, roulis, fisheye compris) est comparée aux boîtes des secteurs et des objets : personnages, drones, débris, particules, impacts, traçantes. Ce qui est hors champ n'est ni envoyé ni calculé par la carte graphique. Le pourcentage de carte dessiné s'affiche dans le coin de la caméra (« CHAMP »).
- Les lumières ne sont pas filtrées ainsi : une lampe hors champ éclaire encore ce qui est visible. Elles sont limitées aux plus proches de la caméra.
- Les textures restent chargées : les retirer et les recharger à chaque mouvement de tête provoquerait des saccades ; le gain vient de ne pas dessiner.


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
