# Spec Delta

## Purpose

Produit périodiquement des images horodatées du rendu de l'onglet cible, à un FPS réglable et optionnellement limitées à une zone, avec les métadonnées géométriques nécessaires à leur exploitation.

## ADDED Requirements

### Requirement: Capture périodique
Tant que la capture est active, le module MUST produire des images JPEG du rendu de l'onglet cible à intervalle régulier égal à 1/FPS.

#### Scenario: Capture à 10 FPS
- **WHEN** la capture est active avec un FPS de 10 pendant 5 secondes sur une page qui peut être capturée en moins de 100 ms
- **THEN** environ 50 images sont produites (tolérance de 10 %)

### Requirement: Réglage du FPS
Le FPS MUST être configurable au démarrage (valeur par défaut 10) et modifiable pendant l'exécution, dans l'intervalle 0,1 à 30 inclus ; toute valeur hors intervalle MUST être rejetée sans modifier le FPS courant.

#### Scenario: Changement de FPS à chaud
- **WHEN** le FPS passe de 10 à 2 pendant la capture
- **THEN** l'intervalle entre images consécutives devient d'environ 500 ms dès l'image suivante

#### Scenario: FPS hors limites
- **WHEN** un FPS de 120 est demandé
- **THEN** la demande est rejetée avec une erreur et le FPS courant est inchangé

### Requirement: Pas de rattrapage en cas de retard
Si une capture dure plus longtemps que l'intervalle cible, le module MUST sauter les échéances manquées plutôt que de produire des images en rafale, et MUST exposer le FPS effectif mesuré.

#### Scenario: Capture plus lente que le FPS demandé
- **WHEN** le FPS demandé est 30 et chaque capture prend 100 ms
- **THEN** les images sont produites à environ 10 par seconde, sans rafale, et le FPS effectif rapporté est d'environ 10

### Requirement: Capture d'une zone
Le module MUST permettre de restreindre la capture à un rectangle `{x, y, width, height}` exprimé en pixels CSS relatifs au viewport ; sans zone, l'image couvre tout le viewport. Une zone qui sort du viewport ou de taille nulle MUST être rejetée.

#### Scenario: Capture d'une zone valide
- **WHEN** la zone `{x: 100, y: 50, width: 400, height: 300}` est définie avec un devicePixelRatio de 1
- **THEN** les images suivantes mesurent 400x300 pixels et représentent ce rectangle du viewport

#### Scenario: La zone suit le viewport lors du scroll
- **WHEN** une zone est définie et la page défile
- **THEN** l'image représente toujours le même rectangle du viewport, et non la même région du document

#### Scenario: Zone invalide
- **WHEN** une zone dont `x + width` dépasse la largeur du viewport est demandée
- **THEN** la demande est rejetée avec une erreur et la zone courante est inchangée

#### Scenario: Retour au viewport complet
- **WHEN** la zone est réinitialisée
- **THEN** les images suivantes couvrent tout le viewport

### Requirement: Horodatage des images
Chaque image MUST porter un numéro de séquence strictement croissant à partir de 0, un horodatage monotone en nanosecondes et un horodatage d'horloge murale en millisecondes Unix, tous deux pris au déclenchement de la capture, ainsi que la durée de la capture en millisecondes.

#### Scenario: Séquence et horodatages cohérents
- **WHEN** deux images consécutives sont produites
- **THEN** la seconde a un numéro de séquence supérieur de 1 et un horodatage monotone strictement supérieur à la première

### Requirement: Métadonnées géométriques
Chaque image MUST porter la zone capturée en pixels CSS du viewport, le devicePixelRatio, la position de scroll de la page en pixels CSS, la taille de l'image en pixels et un identifiant d'onglet.

#### Scenario: Métadonnées d'une image de zone
- **WHEN** une image est capturée avec la zone `{x: 100, y: 50, width: 400, height: 300}` alors que la page a défilé de 200 pixels verticalement
- **THEN** ses métadonnées indiquent `zone = {x:100, y:50, width:400, height:300}`, `scroll = {x:0, y:200}`, le devicePixelRatio courant et la taille de l'image en pixels

### Requirement: Démarrage et arrêt de la capture
Le module MUST démarrer la capture automatiquement au lancement et MUST permettre de la mettre en pause puis de la reprendre sans réinitialiser la numérotation des images.

#### Scenario: Pause puis reprise
- **WHEN** la capture est mise en pause pendant 2 secondes puis reprise
- **THEN** aucune image n'est produite pendant la pause et la première image après reprise porte le numéro de séquence suivant le dernier émis
