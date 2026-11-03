# web-capture

Module Python autonome qui lance Chromium, capture périodiquement un onglet à FPS réglable, diffuse les images en direct par WebSocket et peut les enregistrer en MP4.

## Prérequis

- Python 3.11 ou supérieur
- Poetry 2.x
- ffmpeg système (prioritaire) ou le binaire fourni par `imageio-ffmpeg`
- Pour le mode visible, un serveur graphique Linux ; sinon activer `browser.headless=true`

```sh
poetry install
poetry run playwright install chromium
poetry run web-capture --print-config
```

Poetry crée le venv du projet dans `.venv/`. Le répertoire est ignoré par git et VS Code peut le sélectionner comme interpréteur Python.

## Lancer

Démarrer sur une page locale de test, en mode headless :

```sh
poetry run web-capture \
  browser.url=file:///chemin/absolu/vers/page.html \
  browser.headless=true \
  capture.fps=10
```

Un fichier YAML peut définir les options persistantes. Les valeurs sont fusionnées dans l'ordre : défauts intégrés, fichier `--config`, puis overrides `section.clé=valeur`.

```sh
poetry run web-capture --config configs/default.yaml \
  browser.url=https://example.com \
  browser.headless=true \
  capture.fps=15 \
  capture.zone='{x: 100, y: 50, width: 640, height: 360}' \
  recording.output_dir=./recordings
```

`--print-config` affiche la configuration fusionnée sans lancer Chromium. Une mauvaise clé, une valeur invalide ou l'absence de `browser.url` renvoie un code 2. Le serveur écoute par défaut sur `127.0.0.1:8765` ; `/` ouvre le viewer. La capture débute automatiquement. Le viewer permet le réglage de FPS, la pause/reprise et l'enregistrement.

Les changements de zone sont refusés pendant un enregistrement afin de garder une dimension vidéo constante. Les fichiers sont générés sous `recording.output_dir` ; le client ne transmet jamais de chemin.

## Architecture

Le cœur suit une architecture hexagonale :

- `domain/` : valeurs métier immuables et règles pures
- `application/` : capture, bus de frames, politiques de livraison, commandes et enregistrement
- `adapters/` : configuration OmegaConf, Chromium/Playwright et CDP, HTTP/WebSocket aiohttp, ffmpeg
- `entrypoints/` : CLI et composition root

Les ports sont définis dans `application/ports.py`. Playwright lance le navigateur ; la capture utilise CDP derrière `CdpChannel`, pour permettre ultérieurement un autre transport sans modifier les services applicatifs. Les diagrammes UML et les décisions d'architecture sont dans [le design du change](openspec/changes/browser-capture-core/design.md).

## WebSocket `/frames`

Connexion : `ws://127.0.0.1:8765/frames?mode=latest` ou `?mode=all`. Le mode par défaut est `latest`.

Chaque message binaire est composé de `[uint32 big-endian: longueur JSON][en-tête JSON UTF-8][octets JPEG]`. L'en-tête comprend `seq`, `ts_mono_ns`, `ts_wall_ms`, `capture_ms`, `tab_id`, `zone`, `dpr`, `scroll`, `size`, `format` et `dropped`.

- `latest` ne met pas les images en attente : un abonné lent reçoit la plus récente lorsqu'il est prêt.
- `all` conserve l'ordre tant que le lecteur suit le rythme ; si le buffer circulaire est dépassé, `dropped` indique le nombre d'images sautées.

Exemple de client Python minimal en mode `latest` :

```python
import asyncio
import json
import struct

from aiohttp import ClientSession


async def main() -> None:
    async with ClientSession() as session:
        async with session.ws_connect("ws://127.0.0.1:8765/frames?mode=latest") as ws:
            async for message in ws:
                if message.type.name != "BINARY":
                    continue
                (header_size,) = struct.unpack_from(">I", message.data)
                start = 4 + header_size
                header = json.loads(message.data[4:start])
                jpeg = message.data[start:]
                print(header["seq"], header["ts_wall_ms"], len(jpeg))


asyncio.run(main())
```

## WebSocket `/control`

Le client envoie un message JSON texte `{ "id": 1, "cmd": "status" }`. La réponse reprend `id` et contient `ok` ainsi que le résultat ou une chaîne `error`.

Commandes disponibles : `status`, `set_fps` (`fps`), `set_zone` (`zone` objet ou `null`), `pause`, `resume`, `start_recording`, `stop_recording`. Le port HTTP et les WebSockets n'acceptent que l'origine du module ; les clients non navigateurs sans en-tête `Origin` sont acceptés. Garder l'écoute sur loopback sauf besoin explicite.

## Développement

```sh
poetry run ruff check
poetry run ruff format --check
poetry run mypy src
poetry run pytest -m "not integration"
poetry run pytest -m integration
poetry run pytest -m ffmpeg
```

Les tests CDP requièrent Chromium. Les tests d'encodage utilisent ffmpeg système ou `imageio-ffmpeg` et vérifient les vidéos avec `count_frames_and_secs`.
