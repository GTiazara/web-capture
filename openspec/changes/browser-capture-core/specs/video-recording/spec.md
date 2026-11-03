# Spec Delta

## Purpose

Enregistre le flux capturé dans un fichier vidéo MP4 lisible par les lecteurs courants, avec une durée fidèle au temps réel de capture.

## ADDED Requirements

### Requirement: Enregistrement MP4 à cadence constante
Un enregistrement MUST produire un fichier MP4 (H.264) à cadence constante égale au FPS en vigueur au démarrage de l'enregistrement ; à chaque pas de temps, la dernière image capturée MUST être écrite, en dupliquant ou en sautant des images si nécessaire, de sorte que la durée de la vidéo corresponde à la durée réelle d'enregistrement.

#### Scenario: Durée fidèle malgré une capture irrégulière
- **WHEN** un enregistrement dure 10 secondes alors que le FPS effectif de capture fluctue entre 5 et 10 pour un FPS demandé de 10
- **THEN** le fichier MP4 dure environ 10 secondes (tolérance de 5 %) et contient environ 100 images

#### Scenario: Changement de FPS pendant l'enregistrement
- **WHEN** le FPS de capture passe de 10 à 2 pendant un enregistrement démarré à 10 FPS
- **THEN** la vidéo reste à 10 FPS et sa durée reste fidèle au temps réel

### Requirement: Emplacement des fichiers
Les fichiers MUST être écrits uniquement dans le répertoire de sortie configuré (`./recordings` par défaut), sous un nom généré à partir de la date et l'heure de début ; aucun client MUST pouvoir choisir un chemin arbitraire.

#### Scenario: Nom généré
- **WHEN** un enregistrement démarre le 3 novembre 2026 à 14:05:09
- **THEN** le fichier est créé dans le répertoire de sortie sous un nom contenant `20261103-140509` et l'extension `.mp4`

### Requirement: Indépendance vis-à-vis de la capture
L'enregistrement MUST lire les images sans ralentir la capture ni les autres abonnés ; si l'encodage ne suit pas, la perte d'images MUST être comptabilisée et exposée dans l'état d'enregistrement.

#### Scenario: Encodeur lent
- **WHEN** l'encodeur ne parvient pas à suivre le rythme
- **THEN** le FPS effectif de capture est inchangé et le nombre d'images perdues est visible dans l'état d'enregistrement

### Requirement: Finalisation du fichier
L'arrêt d'un enregistrement, l'arrêt du module ou la fin de la session navigateur MUST finaliser le fichier MP4 de sorte qu'il soit lisible.

#### Scenario: Arrêt du module pendant l'enregistrement
- **WHEN** le module est arrêté par Ctrl+C pendant un enregistrement
- **THEN** le fichier MP4 produit est lisible et contient les images enregistrées jusqu'à l'arrêt

### Requirement: Encodeur indisponible
Si l'encodeur vidéo n'est pas disponible sur la machine, le démarrage d'un enregistrement MUST échouer avec une erreur explicite sans affecter la capture.

#### Scenario: ffmpeg absent
- **WHEN** un enregistrement est demandé sur une machine sans ffmpeg
- **THEN** la demande échoue avec un message indiquant que l'encodeur est introuvable et la capture continue
