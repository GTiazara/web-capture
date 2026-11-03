# Spec Delta

## Purpose

Offre une page web servie par le module pour visualiser en direct le flux capturé et piloter les réglages essentiels sans outil externe.

## ADDED Requirements

### Requirement: Page de visualisation
Le module MUST servir à la racine `/` de son adresse d'écoute une page web qui s'abonne à `/frames` en mode latest et affiche chaque image reçue.

#### Scenario: Ouverture du viewer
- **WHEN** un utilisateur ouvre `http://127.0.0.1:<port>/` dans un navigateur pendant la capture
- **THEN** la page affiche le flux capturé, mis à jour au fil des images

### Requirement: Informations affichées
Le viewer MUST afficher pour l'image courante son numéro de séquence, son horodatage d'horloge murale, le FPS de réception mesuré côté viewer et la latence entre l'horodatage de capture et l'affichage.

#### Scenario: Affichage des informations
- **WHEN** le viewer affiche une image
- **THEN** son numéro de séquence, son horodatage, le FPS de réception et la latence sont visibles

### Requirement: Contrôles du viewer
Le viewer MUST permettre de modifier le FPS, de mettre en pause et reprendre la capture et de démarrer et arrêter l'enregistrement, via `/control`, et MUST afficher les erreurs renvoyées.

#### Scenario: Changement de FPS depuis le viewer
- **WHEN** l'utilisateur saisit 2 dans le contrôle de FPS du viewer et valide
- **THEN** la capture passe à 2 FPS et l'affichage se met à jour environ toutes les 500 ms

#### Scenario: Erreur affichée
- **WHEN** l'utilisateur saisit un FPS de 120
- **THEN** le viewer affiche l'erreur renvoyée et le FPS courant est inchangé

### Requirement: Reconnexion du viewer
Le viewer MUST signaler la perte de connexion avec le module et MUST tenter de se reconnecter périodiquement.

#### Scenario: Redémarrage du module
- **WHEN** le module est arrêté puis relancé sur le même port alors que le viewer est ouvert
- **THEN** le viewer indique la déconnexion puis reprend l'affichage du flux après reconnexion
