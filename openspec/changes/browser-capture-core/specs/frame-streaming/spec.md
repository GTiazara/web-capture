# Spec Delta

## Purpose

Conserve les images récentes en mémoire et les diffuse à des abonnés locaux indépendants via un flux WebSocket, chacun choisissant entre recevoir la dernière image disponible ou toutes les images.

## ADDED Requirements

### Requirement: Buffer circulaire d'images
Le module MUST conserver en mémoire les N dernières images capturées, N étant configurable (60 par défaut) ; l'insertion d'une image lorsque le buffer est plein MUST évincer la plus ancienne.

#### Scenario: Éviction de l'image la plus ancienne
- **WHEN** le buffer a une capacité de 3 et que les images 0 à 3 sont produites
- **THEN** le buffer contient les images 1, 2 et 3

### Requirement: Point d'accès au flux d'images
Le module MUST exposer un point d'accès WebSocket `/frames` sur l'adresse d'écoute configurée, 127.0.0.1 par défaut, auquel plusieurs abonnés peuvent se connecter simultanément.

#### Scenario: Plusieurs abonnés simultanés
- **WHEN** deux clients se connectent à `/frames`
- **THEN** chacun reçoit des images indépendamment de l'autre

#### Scenario: Écoute locale par défaut
- **WHEN** le module est démarré sans adresse d'écoute explicite
- **THEN** le serveur n'est joignable que depuis la machine locale

### Requirement: Format des messages d'image
Chaque image MUST être envoyée dans un message WebSocket binaire composé d'une longueur d'en-tête sur 4 octets (entier non signé big-endian), d'un en-tête JSON UTF-8 de cette longueur, puis des octets JPEG de l'image. L'en-tête MUST contenir les champs `seq`, `ts_mono_ns`, `ts_wall_ms`, `capture_ms`, `tab_id`, `zone`, `dpr`, `scroll`, `size`, `format` et `dropped`.

#### Scenario: Décodage d'un message d'image
- **WHEN** un abonné reçoit un message binaire sur `/frames`
- **THEN** il lit la longueur d'en-tête, décode l'en-tête JSON contenant tous les champs requis et décode le reste comme une image JPEG valide de taille `size`

### Requirement: Mode d'abonnement « latest » par défaut
Un abonné connecté sans paramètre de mode, ou avec `mode=latest`, MUST recevoir uniquement l'image la plus récente disponible lorsqu'il est prêt à recevoir ; les images intermédiaires MUST être sautées sans file d'attente.

#### Scenario: Abonné lent en mode latest
- **WHEN** un abonné en mode latest met 1 seconde à traiter chaque image alors que la capture est à 10 FPS
- **THEN** chaque image reçue est la plus récente au moment de l'envoi, environ 9 images sont sautées entre deux réceptions et la latence ne croît pas dans le temps

### Requirement: Mode d'abonnement « all »
Un abonné connecté avec `mode=all` MUST recevoir les images dans l'ordre de séquence sans en sauter tant qu'il suit le rythme ; s'il prend un retard supérieur à la capacité du buffer, il MUST reprendre à la plus ancienne image disponible et le champ `dropped` de l'image suivante MUST indiquer le nombre d'images perdues.

#### Scenario: Abonné qui suit le rythme
- **WHEN** un abonné en mode all lit plus vite que la capture
- **THEN** il reçoit toutes les images avec des numéros de séquence consécutifs et `dropped` vaut 0

#### Scenario: Abonné trop lent en mode all
- **WHEN** un abonné en mode all prend un retard de 100 images avec un buffer de capacité 60
- **THEN** il reprend à la plus ancienne image du buffer et le champ `dropped` de cette image indique 40

### Requirement: Isolation des abonnés
Un abonné lent ou déconnecté MUST ne ralentir ni la capture ni les autres abonnés.

#### Scenario: Abonné bloqué
- **WHEN** un abonné cesse de lire ses messages
- **THEN** le FPS effectif de capture et la réception des autres abonnés sont inchangés

### Requirement: Contrôle d'origine du flux
Une connexion à `/frames` portant un en-tête `Origin` différent de l'origine du module MUST être refusée ; une connexion sans en-tête `Origin` (client non navigateur) MUST être acceptée.

#### Scenario: Page web tierce
- **WHEN** une page servie par `http://example.com` tente d'ouvrir un WebSocket vers `/frames`
- **THEN** la connexion est refusée

#### Scenario: Client local non navigateur
- **WHEN** un script Python se connecte à `/frames` sans en-tête `Origin`
- **THEN** la connexion est acceptée

### Requirement: Paramètre de mode invalide
Une connexion à `/frames` avec un mode autre que `latest` ou `all` MUST être refusée.

#### Scenario: Mode inconnu
- **WHEN** un client se connecte à `/frames?mode=burst`
- **THEN** la connexion est refusée avec une erreur
