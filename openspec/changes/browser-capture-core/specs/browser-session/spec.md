# Spec Delta

## Purpose

Permet au module de lancer et de piloter son propre navigateur Chromium et l'onglet cible dont le rendu sera capturé.

## ADDED Requirements

### Requirement: Lancement du navigateur et de l'onglet cible
Au démarrage, le module MUST lancer une instance Chromium dédiée et ouvrir un unique onglet cible sur l'URL fournie en configuration.

#### Scenario: Démarrage avec une URL valide
- **WHEN** le module est démarré avec l'URL `http://127.0.0.1:8000/page.html`
- **THEN** une instance Chromium est lancée et l'onglet cible affiche cette URL

#### Scenario: URL injoignable
- **WHEN** le module est démarré avec une URL qui ne répond pas
- **THEN** le module signale l'erreur de navigation et s'arrête avec un code de sortie non nul

### Requirement: Mode visible ou headless
Le module MUST lancer le navigateur en mode visible par défaut et MUST permettre de le lancer en mode headless via la configuration.

#### Scenario: Mode par défaut
- **WHEN** le module est démarré sans option de mode
- **THEN** la fenêtre du navigateur est visible à l'écran

#### Scenario: Mode headless
- **WHEN** le module est démarré avec l'option headless
- **THEN** aucune fenêtre n'est affichée et la capture fonctionne

### Requirement: Taille du viewport
Le module MUST appliquer la taille de viewport (largeur, hauteur en pixels CSS) fournie en configuration, avec une valeur par défaut de 1280x720.

#### Scenario: Viewport configuré
- **WHEN** le module est démarré avec un viewport de 1920x1080
- **THEN** les images capturées sans zone ont une taille correspondant à 1920x1080 pixels CSS multipliés par le devicePixelRatio

### Requirement: Navigation dans l'onglet
Le module MUST continuer à capturer l'onglet cible lorsque la page navigue vers une autre URL ou se recharge.

#### Scenario: Navigation pendant la capture
- **WHEN** la page cible navigue vers une autre URL pendant la capture
- **THEN** la capture continue sans interruption de la numérotation des images

### Requirement: Fin de session navigateur
Lorsque l'onglet cible est fermé ou que le navigateur se termine, le module MUST arrêter la capture, finaliser un éventuel enregistrement en cours, fermer les connexions des abonnés et s'arrêter.

#### Scenario: Fermeture de l'onglet par l'utilisateur
- **WHEN** l'utilisateur ferme l'onglet cible
- **THEN** l'enregistrement en cours est finalisé en un fichier MP4 lisible, les abonnés sont déconnectés et le module s'arrête

#### Scenario: Arrêt demandé du module
- **WHEN** le module reçoit un signal d'arrêt (Ctrl+C)
- **THEN** il finalise l'enregistrement en cours, ferme le navigateur et s'arrête proprement
