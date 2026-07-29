# Méthodes d’optimisation du chargement

## Problème traité

Le plancher du véhicule est modélisé comme un conteneur rectangulaire en deux dimensions. Chaque palette ou colis non gerbable devient un rectangle orientable à 0° ou 90°. Le moteur doit placer tous les rectangles sans chevauchement et sans dépasser les dimensions intérieures du véhicule.

Les contraintes opérationnelles sont ensuite appliquées comme contraintes dures:

- passage par l’ouverture arrière;
- hauteur intérieure et charge utile;
- obstacles fixes et zones dédiées;
- marges et distances de séparation;
- compatibilités de marchandises;
- ordre de déchargement LIFO par couloir d’accès;
- contrôle simplifié des réactions d’essieux.

## Portefeuille de méthodes implémenté

### 1. MaxRects

Le moteur maintient une liste de rectangles libres maximaux. Après chaque placement, les zones libres intersectées sont découpées puis les rectangles inclus dans d’autres rectangles libres sont supprimés.

Quatre politiques de score sont exécutées:

- **Best Short Side Fit**: minimise le plus petit résidu latéral;
- **Best Area Fit**: minimise la surface résiduelle du rectangle libre;
- **Bottom-Left**: minimise en priorité la profondeur totale occupée;
- **Balanced**: limite la profondeur tout en rapprochant la charge du centre transversal.

### 2. Points extrêmes et placement bas-gauche

Une seconde famille de stratégies teste les coordonnées produites par les bords des objets déjà placés, les obstacles, les zones, le bord droit et l’axe central du véhicule. Cette famille sert aussi de repli lorsqu’un placement MaxRects est bloqué par une contrainte pratique telle que le LIFO ou une distance de séparation.

### 3. Multi-départs déterministes

Le moteur combine plusieurs tris d’objets:

- surface décroissante;
- largeur décroissante;
- longueur décroissante;
- poids décroissant;
- ordre de livraison prioritaire.

Des variantes déterministes sont produites à partir de la graine fournie. Les résultats restent reproductibles avec la même entrée et la même graine.

### 4. Multi-véhicules

Une borne inférieure est calculée à partir de la surface au sol utile et de la charge utile. Le moteur cherche ensuite le premier nombre de véhicules pour lequel un partitionnement et un placement entièrement valides existent.

## Fonction objectif

Les solutions valides sont classées dans l’ordre suivant:

1. nombre de véhicules;
2. longueur intérieure réellement occupée;
3. métrage linéaire logistique;
4. pénalité de charge d’essieux;
5. équilibre transversal;
6. diversité par rapport aux solutions déjà retenues.

Le métrage linéaire logistique est calculé à partir de la surface au sol divisée par la largeur de référence LDM du véhicule. La longueur occupée dépend réellement du rangement obtenu et constitue donc le critère principal entre deux plans utilisant le même nombre de véhicules.

## Références méthodologiques

- Jukka Jylänki, *A Thousand Ways to Pack the Bin: A Practical Approach to Two-Dimensional Rectangle Bin Packing*, 2010.
- Wenqi Huang, Tao Ye et Duanbing Chen, *Bottom-Left Placement Theorem for Rectangle Packing*, 2011.
- Vinicius Gandra et Tony Wauters, *A heuristic approach to feasibility verification for truck loading*, 2021.
- Silvano Martello et Daniele Vigo, *Exact Solution of the Two-Dimensional Finite Bin Packing Problem*, Management Science, 1998, DOI 10.1287/mnsc.44.3.388.

## Limite assumée

Le problème de packing rectangulaire est combinatoire. Cette version utilise un portefeuille heuristique borné et ne revendique pas une preuve d’optimalité mathématique. En revanche, tout plan retourné est revalidé géométriquement et opérationnellement avant classement.
