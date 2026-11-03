# Proposal

## Why

Il faut un module indépendant capable de récupérer en continu le rendu visuel d'une page web, à une fréquence maîtrisée, et de le mettre à disposition en direct d'un humain (visualisation) et d'un autre processus (analyse d'image/vidéo). Ce premier change pose le socle de capture et de distribution ; la rétroaction sur la page (actions) viendra dans un change ultérieur et s'appuiera sur les métadonnées définies ici.

## What Changes

- Lancement par le module de son propre navigateur Chromium et ouverture d'un onglet sur une URL donnée.
- Capture périodique de l'onglet à un FPS réglable, y compris pendant l'exécution.
- Capture optionnelle d'une zone précise de la page plutôt que du viewport complet.
- Horodatage de chaque image et métadonnées géométriques (zone, devicePixelRatio, scroll, taille) préparant la future conversion de coordonnées pour les actions.
- Buffer circulaire d'images en mémoire, distribuant les images à plusieurs abonnés indépendants, en mode « dernière image » (par défaut) ou « toutes les images ».
- Serveur WebSocket local exposant un flux d'images et un canal de contrôle (FPS, zone, enregistrement, état).
- Page de visualisation en direct servie par le module.
- Enregistrement du flux en MP4.
- Configuration du module par fichier YAML et surcharges en ligne de commande, validée au démarrage.
- Socle de projet professionnel : packaging Poetry, architecture hexagonale (ports & adapters), outillage qualité.

Hors périmètre : actions sur la page (click, saisie, scroll), capture de plusieurs onglets, source screencast, rattachement à un onglet du navigateur de l'utilisateur (extension).

## Capabilities

### New Capabilities

- `browser-session`: lancement et cycle de vie du navigateur et de l'onglet cible piloté par le module.
- `frame-capture`: production périodique d'images horodatées de l'onglet (FPS, zone, métadonnées).
- `frame-streaming`: mise en mémoire tampon et diffusion des images aux abonnés locaux via le flux d'images, avec politique « latest » / « all ».
- `capture-control`: canal de contrôle permettant de modifier les paramètres de capture et d'interroger l'état du module.
- `live-viewer`: page web de visualisation en direct du flux capturé.
- `video-recording`: enregistrement du flux capturé dans un fichier MP4.
- `runtime-configuration`: chargement, fusion et validation de la configuration du module (valeurs par défaut, fichier YAML, surcharges en ligne de commande).

### Modified Capabilities

Aucune (projet vierge).

## Impact

- Nouveau paquet Python (projet vierge) géré avec Poetry, avec un point d'entrée en ligne de commande.
- Nouvelles dépendances : Playwright (et son Chromium), un serveur HTTP/WebSocket asyncio, OmegaConf, ffmpeg (binaire système, avec repli sur le binaire fourni par `imageio-ffmpeg`) pour l'encodage MP4 ; outillage de développement (pytest, ruff, mypy).
- Nouvelle interface réseau locale (HTTP + WebSocket sur 127.0.0.1) qui devient le contrat avec les modules d'analyse externes.
