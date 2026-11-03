# Spec Delta

## Purpose

Définit comment le module obtient sa configuration au démarrage : valeurs par défaut, fichier YAML et surcharges en ligne de commande, fusionnés puis validés avant tout lancement.

## ADDED Requirements

### Requirement: Sources et priorité de configuration
Le module MUST construire sa configuration en fusionnant, par priorité croissante, les valeurs par défaut intégrées, un fichier YAML optionnel désigné en ligne de commande, puis des surcharges en ligne de commande de la forme `section.clé=valeur`.

#### Scenario: Valeurs par défaut seules
- **WHEN** le module est démarré avec uniquement `browser.url=http://127.0.0.1:8000/`
- **THEN** il utilise les valeurs par défaut pour tous les autres paramètres (FPS 10, viewport 1280x720, hôte 127.0.0.1, port 8765)

#### Scenario: Surcharge d'un fichier par la ligne de commande
- **WHEN** le fichier YAML fourni définit `capture.fps: 5` et que la ligne de commande contient `capture.fps=15`
- **THEN** le FPS de démarrage est 15

### Requirement: Validation avant démarrage
La configuration fusionnée MUST être entièrement validée (clés connues, types, bornes, cohérence de la zone avec le viewport) avant le lancement du navigateur ; en cas d'erreur, le module MUST afficher un message désignant la clé fautive et s'arrêter avec un code de sortie non nul.

#### Scenario: Clé inconnue
- **WHEN** la ligne de commande contient `capture.fsp=15`
- **THEN** le module affiche une erreur mentionnant `capture.fsp`, ne lance pas de navigateur et s'arrête avec un code non nul

#### Scenario: Valeur hors bornes
- **WHEN** la configuration contient `capture.fps=120`
- **THEN** le module affiche une erreur mentionnant `capture.fps` et s'arrête avec un code non nul

#### Scenario: URL manquante
- **WHEN** aucune valeur n'est fournie pour `browser.url`
- **THEN** le module affiche une erreur mentionnant `browser.url` et s'arrête avec un code non nul

### Requirement: Affichage de la configuration effective
Le module MUST proposer une option affichant la configuration effective fusionnée au format YAML puis s'arrêtant sans lancer de navigateur.

#### Scenario: Inspection de la configuration
- **WHEN** le module est lancé avec l'option d'affichage de la configuration et `capture.fps=15`
- **THEN** il affiche le YAML complet avec `fps: 15` et s'arrête avec un code 0
