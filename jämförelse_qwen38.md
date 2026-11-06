# Jämförelse av de fem implementationerna

Jämförelse av de fem brancherna med alternativa implementationer av applikationen
(se `specs.md`): `antigravity`, `opencode-bigpickle`, `opencode-deepseek-flash`,
`vibe-glm53` och `vscode-qwen38`.

## Gemensamt

Alla fem använder **PySide6 (Qt 6)** – ingen skillnad i GUI-ramverk. Skillnaderna
ligger i arkitektur, trådar, dataset-hantering, tester och detaljer.

## Det som är bättre i andra brancher

### `opencode-bigpickle` – bäst arkitektur totalt

- **Hexagonal/clean architecture** (`domain/` → `application/` → `infrastructure/`
  → `ui/`) – mest disciplinerad struktur av alla. Domain-lagern är rena dataclasser
  utan Qt/IO.
- **Träning i separat OS-process** (`QProcess`) – undviker GIL och skyddar GUI:t.
  `vscode-qwen38` (och `antigravity`/`vibe-glm53`) kör träning i `QThread`, vilket
  delar GIL med inference och gör stopp knappt pålitligt.
- **Crash-säkert dataset**: atomära JSON-skrivningar (temp + `os.replace`),
  **immutable versions-snapshots med sha256**, och train/val-split **per
  capture-pair** (seedad shuffle) – undviker leakage mellan de två kameravinklarna
  av samma scen. Ingen annan branch har pair-aware split.
- **Riktiga tester**: 7 testfiler (unit + UI-smoke) som körs utan hårdvara
  (`FakeDetector`, syntetisk videosource).
- **Ramverkshygiene**: riktig entry point (`xray-detector` console script),
  `opencv-python-headless`, extras (`ml`/`windows`/`build`), ruff + pyright,
  frame-sekvensnummer så boxar aldrig ritas på föråldrade frames.
- Kiosk med exit-shortcut + dold cursor, kameradetection, videosource, testpattern.

### `opencode-deepseek-flash` – bäst dataset-versionering + tester

- **Semver-versionering med revision + "freeze"** (export/träning fryser
  versionen automatiskt) – snyggare semantik än `v1, v2, ...`.
- Atomära skrivningar med `fsync`, transaktionell export (rmtree vid fel),
  global `excepthook` med felruta.
- **8 testfiler** (~394 rader) som täcker COCO, export, geometri, config,
  träning – bäst logiktäckning.
- Graceful degradation utan ultralytics (valfritt extra).
- Svaghet: ingen RF-DETR-backend alls, och `yolo11n.pt` (5,6 MB) är committad
  i repo:t.

### `antigravity` – unika funktioner

- **Schemalagd träning** (nattfönstret 23–05 + inaktivitetsdetektering via
  global event-filter) – **enligt specen** ("träning endast nattetid eller under
  inaktivitet"). Ingen annan branch implementerar detta.
- **Syntetisk kamerafallback** (animerad röntgen-band) – hela appen går att köra
  utan hårdvara.
- Bäst annoteringscanvas: 8 resize-handles med riktig hit-testing, min-storlek,
  hover-cursors.
- **Men**: träningen är en **simulering** (dummy-nätverk på `torch.randn`,
  uppfunna mAP-värden) och tränade vikter kan aldrig användas för inference –
  största bristen i branchen.

### `vibe-glm53` – UX-bonus

- **Dataset-flik med thumbnails**, om-annotering av sparade captures
  (dubbelklick), radering – enda branchen med detta.
- Temasystem (ljus/mörk/system, följer OS), fönstergeometri persisteras via
  `QSettings`.
- **Men**: inga tester, RF-DETR erbjuds i träning UI:t men stöds inte,
  `hash(class)` ger färg som byter vid varje start, träningsprocessen orphanas
  vid avstängning.

## `vscode-qwen38` – vad som är bra här

- **Pydantic v2**-config med validering + legacy-migration – bäst
  config-hantering av alla.
- **loguru** med filrotation – enda branchen med riktig loggning.
- Drop-oldest-inference, per-stream fel-UI med "Försök igen"-knapp, CPU-fallback.
- Notera: `quantize=`-kwargen i `predict()` är **faktiskt giltig** i
  ultralytics 8.4.123 (verifierat mot `QUANTIZE_ALIASES` – `fp16`/`fp32` stöds),
  så det är inget fel där.

## `vscode-qwen38` – verkliga brister (vs specen)

1. **Ingen resize av rektanglar** – specen kräver det uttryckligen ("trycka och
   dra i en rektangels kant eller hörn"), men `RectItem` saknar
   `ItemIsResizable` (docstringen påstår att det fungerar – det gör den inte).
2. **Träningsavbrytande är no-op** – `TrainingWorker.run()` kollar aldrig `_stop`.
3. **Kiosk är config-stub** – `app.kiosk` läses aldrig.
4. **Tränade vikter registreras inte** i modellväljaren.
5. **Inga tester**, ingen train/val-split.

## Rekommendation

Bygg vidare på **`opencode-bigpickle`** som bas (arkitektur, process-isolerad
träning, crash-säkert dataset, tester) och plocka över:

- **Schemalagrad träning** (natt/inaktivitet) från `antigravity`
- **Dataset-bläsrar/om-annotering** från `vibe-glm53`
- **Pydantic-config + loguru + per-stream retry-UI** från `vscode-qwen38`
- **Semver/freeze-versionering** från `opencode-deepseek-flash` om man föredrar
  den semantiken
