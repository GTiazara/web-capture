# Spec Delta

## Purpose

Fournit un canal de commande local permettant à un client (viewer, module d'analyse, script) de modifier les paramètres de capture et d'enregistrement et d'interroger l'état du module.

## ADDED Requirements

### Requirement: Point d'accès de contrôle
Le module MUST exposer un point d'accès WebSocket `/control` sur la même adresse d'écoute que `/frames`, acceptant des messages texte JSON de la forme `{"id": <any>, "cmd": <string>, ...}` et répondant à chaque message par `{"id": <même id>, "ok": true, ...}` ou `{"id": <même id>, "ok": false, "error": <message>}`.

#### Scenario: Réponse corrélée
- **WHEN** un client envoie `{"id": 7, "cmd": "status"}`
- **THEN** il reçoit une réponse JSON portant `"id": 7` et `"ok": true`

#### Scenario: Commande inconnue ou message mal formé
- **WHEN** un client envoie `{"id": 8, "cmd": "explode"}` ou un texte qui n'est pas du JSON
- **THEN** il reçoit une réponse `"ok": false` avec un message d'erreur et la connexion reste ouverte

### Requirement: Contrôle d'origine du canal de contrôle
Une connexion à `/control` portant un en-tête `Origin` différent de l'origine du module MUST être refusée ; une connexion sans en-tête `Origin` MUST être acceptée.

#### Scenario: Page web tierce
- **WHEN** une page servie par `http://example.com` tente d'ouvrir un WebSocket vers `/control`
- **THEN** la connexion est refusée et aucune commande n'est exécutée

### Requirement: Commande de FPS
La commande `set_fps` avec un champ `fps` MUST appliquer le nouveau FPS selon les règles de la capture et MUST renvoyer une erreur si la valeur est rejetée.

#### Scenario: Changement de FPS
- **WHEN** un client envoie `{"id": 1, "cmd": "set_fps", "fps": 5}`
- **THEN** la réponse est `"ok": true` et la capture passe à 5 FPS

### Requirement: Commande de zone
La commande `set_zone` avec un champ `zone` (rectangle ou `null` pour le viewport complet) MUST appliquer la zone selon les règles de la capture et MUST renvoyer une erreur si la zone est rejetée ou si un enregistrement est en cours.

#### Scenario: Définition d'une zone
- **WHEN** un client envoie `set_zone` avec `{"x": 0, "y": 0, "width": 640, "height": 360}`
- **THEN** la réponse est `"ok": true` et les images suivantes couvrent cette zone

#### Scenario: Zone modifiée pendant un enregistrement
- **WHEN** un client envoie `set_zone` alors qu'un enregistrement est en cours
- **THEN** la réponse est `"ok": false` et la zone est inchangée

### Requirement: Commandes de pause et de reprise
Les commandes `pause` et `resume` MUST respectivement suspendre et reprendre la capture.

#### Scenario: Pause via le contrôle
- **WHEN** un client envoie `{"id": 2, "cmd": "pause"}`
- **THEN** la réponse est `"ok": true` et plus aucune image n'est produite jusqu'à `resume`

### Requirement: Commandes d'enregistrement
Les commandes `start_recording` et `stop_recording` MUST respectivement démarrer et finaliser l'enregistrement MP4 ; la réponse à `start_recording` MUST indiquer le nom du fichier créé et la réponse à `stop_recording` le chemin du fichier finalisé.

#### Scenario: Cycle d'enregistrement
- **WHEN** un client envoie `start_recording`, attend 3 secondes, puis envoie `stop_recording`
- **THEN** les deux réponses sont `"ok": true` et la seconde indique le chemin d'un fichier MP4 existant

#### Scenario: Double démarrage
- **WHEN** un client envoie `start_recording` alors qu'un enregistrement est déjà en cours
- **THEN** la réponse est `"ok": false` et l'enregistrement en cours continue

### Requirement: Commande d'état
La commande `status` MUST renvoyer l'URL courante de l'onglet, l'état de capture (actif ou en pause), le FPS demandé, le FPS effectif, la zone courante, le dernier numéro de séquence, le nombre d'abonnés par mode et l'état d'enregistrement.

#### Scenario: Lecture de l'état
- **WHEN** un client envoie `{"id": 3, "cmd": "status"}` pendant une capture à 10 FPS sans zone
- **THEN** la réponse contient l'état actif, `fps: 10`, un FPS effectif, `zone: null`, le dernier `seq` et l'état d'enregistrement
