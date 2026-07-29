# Pallet Loading Optimizer

V2 exécutable d’un optimiseur de chargement pour palettes et colis. Le système recherche des plans de rangement à l’aide d’un portefeuille **MaxRects + points extrêmes**, minimise d’abord le nombre de véhicules puis la longueur réellement occupée, et applique comme contraintes dures la géométrie, les ouvertures, les obstacles, le poids, les essieux, le LIFO et les incompatibilités.

## Écran 0: catalogue véhicules

L’onglet **0. Véhicules** permet de créer ou modifier les caractéristiques utilisées par le moteur:

- longueur, largeur et hauteur intérieures;
- largeur de référence pour le métrage linéaire;
- charge utile;
- largeur et hauteur de l’ouverture arrière.

Les véhicules sont enregistrés dans l’espace local `demo`. L’interface web ne demande aucune clé API. Chaque modification crée une nouvelle version et les calculs suivants utilisent immédiatement ces dimensions.

## Préparation du chargement

L’onglet **1. Données** permet d’autoriser l’empilage. Lorsque l’option est activée, seules les palettes strictement compatibles — mêmes dimensions, poids, destination, ordre et contraintes — peuvent partager la même emprise au sol. Le moteur conserve toujours la hauteur sur l’axe vertical: les seules rotations possibles sont 0° et 90° sur le plan longueur × largeur.

## Démarrage local

```bash
python -m pip install -e '.[dev]' --no-build-isolation
PLO_DEMO_MODE=1 pallet-optimizer --data-dir data serve --host 127.0.0.1 --port 8000
```

Ouvrir ensuite `http://127.0.0.1:8000`.

## API

La clé API concerne uniquement les intégrations qui appellent l’API publique. Créer une entreprise et une clé, puis appeler l’API:

```bash
pallet-optimizer --data-dir data create-tenant circoe "CIRCOE"
pallet-optimizer --data-dir data issue-api-key circoe --label integration
```

`POST /v1/optimizations` avec l’en-tête `X-API-Key`. L’API retourne uniquement la meilleure solution. L’interface interactive, indépendante de cette clé, peut en présenter jusqu’à cinq.

## Tests

```bash
pytest
PYTHONPATH=src python scripts/smoke_test.py
PYTHONPATH=src python scripts/ui_e2e.py
```

La suite couvre notamment le cas remonté de trois palettes 1200 × 800 mm, la prise en compte d’une largeur véhicule modifiée, les bornes géométriques, le LIFO, les essieux, le multi-véhicules, l’isolation par base, les clés API, les exports, l’empilage et un cas de 100 objets.

## Déploiement

```bash
docker compose up --build
```

Le même conteneur est utilisable en SaaS ou en installation dédiée. Seuls le volume de données, le mode démo et la terminaison TLS changent.

## Limites explicites

- L’empilage est géométrique et limité aux palettes strictement compatibles; il ne modélise pas la charge admissible ni la résistance de la palette inférieure.
- Aucune manipulation manuelle du plan 3D.
- Le modèle d’essieux reste simplifié et doit être validé selon le véhicule réel.
- Recherche heuristique déterministe, sans garantie d’optimalité mathématique.
- Authentification utilisateur disponible dans la couche de données et la CLI; l’interface web livrée reste un démonstrateur local et ne doit pas être exposée telle quelle sur Internet.

Les références et le détail algorithmique sont décrits dans `docs/optimization-methods.md`.
