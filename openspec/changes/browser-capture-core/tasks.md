# Tasks

## 1. Socle du projet (Poetry, outillage, arborescence)

- [x] 1.1 Initialiser `pyproject.toml` (PEP 621, backend `poetry-core>=2`, Python >=3.11, dépendances `playwright`, `aiohttp`, `omegaconf`, `imageio-ffmpeg`, groupe `dev` `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, script `web-capture = web_capture.entrypoints.cli:main`) et générer `poetry.lock` ; vérifier que `poetry install` et `poetry check` réussissent
- [x] 1.2 Ajouter `poetry.toml` (`[virtualenvs] in-project = true`) et `.gitignore` (`.venv/`, caches Python et outils, `recordings/`) ; vérifier que `poetry env info --path` renvoie `<racine du projet>/.venv` et que `git status` n'affiche pas `.venv/`
- [x] 1.3 Créer l'arborescence hexagonale de D13 (`domain/`, `application/`, `adapters/`, `entrypoints/`, `tests/unit`, `tests/integration`, `tests/fakes`) avec des `__init__.py` et un marqueur `py.typed` ; configurer ruff, mypy strict sur `src/` et les marqueurs pytest `integration` et `ffmpeg` ; vérifier que `poetry run ruff check`, `poetry run mypy src` et `poetry run pytest` passent sur le squelette
- [x] 1.4 Installer Chromium (`poetry run playwright install chromium`) et ajouter `tests/assets/grid.html` (repères colorés à positions connues, page plus haute que le viewport) ; vérifier qu'elle s'ouvre dans un navigateur

## 2. Domaine

- [x] 2.1 Implémenter `domain/frame.py` (`Frame`, `FrameMetadata`, `Zone`, `Size`, `Point` en dataclasses figées) et `domain/errors.py` (hiérarchie `WebCaptureError`) ; vérifier par des tests unitaires de construction et d'immutabilité
- [x] 2.2 Implémenter `domain/rules.py` (bornes du FPS de 0,1 à 30, zone non vide et contenue dans le viewport, qualité JPEG de 1 à 100) ; vérifier par des tests unitaires couvrant valeurs limites, taille nulle et débordement

## 3. Configuration (OmegaConf)

- [x] 3.1 Implémenter `adapters/config/schema.py` (dataclasses `AppConfig` de D11 avec `browser.url = MISSING`) et `adapters/config/omegaconf_loader.py` (défauts → YAML → dotlist → `to_object` → `validate` via les règles du domaine, erreurs converties en `ConfigError` avec le chemin de la clé) ; vérifier par des tests unitaires couvrant chaque scénario de la spec `runtime-configuration` (priorités, clé inconnue `capture.fsp`, `capture.fps=120`, URL manquante)
- [x] 3.2 Ajouter `configs/default.yaml` commenté, reflétant toutes les clés ; vérifier par un test qu'il se charge sans erreur et ne contient que des clés du schéma

## 4. Ports applicatifs et adapters navigateur/CDP

- [x] 4.1 Définir `application/ports.py` (`CdpChannel`, `FrameSource`, `Clock`, `VideoEncoder`, `BrowserSession` en `typing.Protocol`) et les faux de `tests/fakes/` (`FakeClock`, `FakeFrameSource`, `FakeEncoder`) ; vérifier que `mypy` valide la conformité des faux aux ports
- [x] 4.2 Implémenter `adapters/browser/playwright_cdp.py` (`PlaywrightCdpChannel`) et `adapters/clock.py` (`SystemClock`) ; vérifier par un test d'intégration qui envoie `Page.getLayoutMetrics` à un Chromium headless
- [x] 4.3 Implémenter `adapters/browser/playwright_session.py` (lancement visible ou headless, viewport, navigation, `NavigationError` si l'URL est injoignable, événement de fin de session sur fermeture de l'onglet ou du navigateur) ; vérifier par des tests d'intégration (URL valide, URL injoignable, fermeture de l'onglet détectée)

## 5. Capture

- [x] 5.1 Implémenter `application/capture_service.py` (ordonnanceur à échéances absolues sans rattrapage, FPS et zone modifiables à chaud via les règles du domaine, FPS effectif sur une fenêtre glissante, pause/reprise, `seq` continu) ; vérifier par des tests unitaires avec `FakeClock`/`FakeFrameSource` (environ 50 images en 5 s à 10 FPS, capture lente → environ 10 FPS sans rafale, changement de FPS à chaud, FPS hors bornes rejeté, pause/reprise)
- [x] 5.2 Implémenter `adapters/capture/cdp_frame_source.py` (`getLayoutMetrics` pour scroll et DPR, `captureScreenshot` JPEG avec `clip` = zone + scroll, construction de `FrameMetadata`) ; vérifier par des tests d'intégration sur `grid.html` (taille de l'image d'une zone, repère attendu, zone fixe par rapport au viewport après scroll, métadonnées `scroll`/`dpr`/`size`, `seq` continu après navigation)

## 6. Bus d'images et flux `/frames`

- [x] 6.1 Implémenter `application/frame_bus.py` et `application/delivery.py` (Strategy `LatestPolicy`/`AllPolicy`, calcul de `dropped`) ; vérifier par des tests unitaires (éviction 0..3 → 1,2,3 ; un lecteur latest lent reçoit la plus récente ; un lecteur all en retard de 100 avec capacité 60 → `dropped = 40` ; le producteur ne bloque jamais)
- [x] 6.2 Implémenter `adapters/http/codec.py` (message `[uint32 BE][JSON][JPEG]`) et `adapters/http/origin.py` (contrôle d'origine, équivalence `127.0.0.1`/`localhost`) ; vérifier par des tests unitaires (aller-retour du codec, champ requis manquant, Origin tiers refusé, absence d'Origin acceptée)
- [x] 6.3 Implémenter `adapters/http/app.py` et `adapters/http/frames_ws.py` (`/frames?mode=latest|all`, une tâche par abonné, délai d'envoi) ; vérifier par des tests d'intégration aiohttp (deux abonnés simultanés, mode inconnu refusé, Origin tiers refusé, abonné bloqué sans impact sur les autres ni sur le FPS effectif)

## 7. Canal de contrôle

- [x] 7.1 Implémenter `application/control/` (commandes typées `SetFps`, `SetZone`, `Pause`, `Resume`, `GetStatus`, `CommandRegistry`, `ControlService.execute` qui convertit les `WebCaptureError` en réponses d'erreur) ; vérifier par des tests unitaires couvrant chaque scénario de `capture-control` hors enregistrement
- [x] 7.2 Implémenter `adapters/http/control_ws.py` (`/control`, corrélation par `id`, JSON invalide, contrôle d'origine) ; vérifier par des tests d'intégration aiohttp (réponse corrélée, commande inconnue, connexion maintenue après erreur, Origin tiers refusé)

## 8. Enregistrement MP4

- [x] 8.1 Implémenter `application/recording_service.py` (machine à états Idle/Recording/Finalizing, tick CFR au FPS figé, file bornée avec comptage des pertes, nom de fichier généré dans `recording.output_dir`) ; vérifier par des tests unitaires avec `FakeEncoder` et `FakeClock` (environ 100 écritures en 10 s quel que soit le FPS de capture, double démarrage refusé, encodeur lent → pertes comptées, finalisation sur arrêt)
- [x] 8.2 Implémenter `adapters/recording/ffmpeg_encoder.py` (résolution de ffmpeg : PATH puis `imageio-ffmpeg`, commande de D9, fermeture propre) ; vérifier par des tests `ffmpeg` (MP4 de 10 s → durée mesurée par `count_frames_and_secs` de 10 s ±5 % ; dimensions impaires acceptées ; ffmpeg absent simulé → `EncoderUnavailableError`)
- [x] 8.3 Ajouter les commandes `StartRecording`/`StopRecording` au registre, le refus de `SetZone` pendant un enregistrement et l'état d'enregistrement dans `GetStatus` ; vérifier par des tests (cycle démarrage/arrêt → fichier existant, `set_zone` refusé pendant l'enregistrement, `status` reflète l'enregistrement)

## 9. Viewer

- [x] 9.1 Créer `adapters/http/static/viewer.html` servi sur `/` (canvas alimenté par `/frames` en latest, seq, horodatage, FPS de réception et latence, contrôles FPS, pause/reprise et enregistrement, erreurs affichées, reconnexion avec backoff) ; vérifier par un test d'intégration Playwright sur le viewer (une image s'affiche, `seq` progresse, un FPS de 120 affiche une erreur)

## 10. Composition root et cycle de vie

- [x] 10.1 Implémenter `entrypoints/cli.py` (`--config`, `--print-config`, dotlist, codes de sortie 0/1/2) et `entrypoints/bootstrap.py` (construction du graphe d'objets, `TaskGroup`, événement d'arrêt unique sur SIGINT/SIGTERM ou fin de session, arrêt dans l'ordre inverse, avertissement si l'hôte n'est pas local) ; vérifier par des tests d'intégration (`--print-config` affiche le YAML fusionné, clé inconnue → code 2 sans navigateur, SIGINT pendant un enregistrement → MP4 lisible, fermeture de l'onglet → arrêt du module)
- [x] 10.2 Rédiger `README.md` (prérequis Poetry, Chromium et ffmpeg ; lancement avec un fichier de configuration et des surcharges ; architecture résumée avec renvoi aux diagrammes du design ; protocole `/frames` et `/control` ; client Python minimal abonné en latest) ; vérifier en exécutant tel quel l'exemple de client contre un module lancé

## 11. Vérification d'ensemble

- [x] 11.1 Scénario de bout en bout : `poetry run web-capture browser.url=<page> capture.fps=10`, viewer ouvert, client d'exemple en latest et client en all connectés, changements de FPS et de zone, enregistrement de 10 s ; vérifier la cohérence des images reçues, la lisibilité du MP4, puis que `poetry run ruff check`, `poetry run mypy src`, `poetry run pytest` et `openspec validate browser-capture-core --strict` passent
