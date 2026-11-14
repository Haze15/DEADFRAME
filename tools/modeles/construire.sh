#!/bin/sh
# Régénère tous les modèles de décor et la carte « Front » (assets/fr_*). À lancer depuis la racine du dépôt.
# Dépendances : python3, numpy, pillow, scipy. Les .glb intermédiaires restent dans tools/modeles/.
set -e
for s in make_table make_meubles make_trench make_intersection make_arbres make_terrain make_ruine make_front; do
  echo "== $s"; python3 tools/modeles/$s.py
done
python3 src/build.py
