# X-ray detector

Applikation för detektion, annotering och träning av objektmodeller på två
synkroniserade videoströmmar (t.ex. två UVC capture cards). Se `specs.md` för
kravbilden och `PLAN.md` för implementationsplanen.

## Funktioner

- **Detektionsläge** (standard): två videoströmmar i split screen, boxar med
  klass och sannolikhet, modellväljare och en knapp för att fånga ett bildpar.
- **Annoteringsläge**: frysta bilder från båda strömmarna, automatiska
  detektioner förifyllda, rita/flytta/storleksändra/ta bort boxar och välja
  eller skriva in nya klasser. Spara skapar en ny datasetversion.
- **Träningsläge**: välj datasetversion, basmodell (YOLO eller RF-DETR) och
  träningsparametrar. Träningen körs i en separat process, pausar detektionen
  och sparar vikter med datasetets version.
- **Dataset**: COCO internt, automatisk versionering per sparsession och export
  till COCO och/eller YOLO med manifest (version, datum, antal bilder/objekt).
- **Kiosk/fullscreen** och konfigurerbara videokällor, inklusive videofiler och
  en syntetisk testsignal för utveckling utan kameror.

## Installation (Windows 11)

Krav: Python 3.11/3.12 och [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Installera maskininlärningsberoenden (PyTorch, Ultralytics, RF-DETR):

```powershell
uv sync --extra ml
```

För NVIDIA/CUDA rekommenderas att installera PyTorch mot rätt CUDA-index om
standardhjulet inte matchar drivrutinen, t.ex.:

```powershell
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

Namn på videoenheter på Windows kräver `pygrabber`:

```powershell
uv sync --extra windows
```

## Starta

```powershell
uv run xray-detector
```

Alternativt:

```powershell
uv run python -m xray_detector.main
```

Användbar felsökning utan kameror: öppna **Inställningar → Video**, sätt båda
källorna till `test_pattern` och starta detektionen. Videofiler kan väljas med
typen `file`.

Kioskläge:

```powershell
uv run xray-detector --kiosk
```

Avslutningsgenväg i kiosk är `Ctrl+Shift+Q` som standard.

## Konfiguration

- Standardvärden: `config/default.yaml`
- Modellista: `config/models.yaml`
- Användaröverstyrning sparas i `%APPDATA%\XrayDetector\config.yaml`
  (eller filen som anges med `--config`).

Viktiga inställningar:

- `video.cam0` / `video.cam1`: `device`, `file` eller `test_pattern`, upplösning,
  fps och backend (`dshow`, `msmf`, `auto`).
- `detection`: confidence, IoU, bildstorlek, enhet (`cuda:0`/`cpu`), FP16.
- `dataset`: JPEG-kvalitet, train/val-split och seed.
- `ui`: fullscreen, kiosk, autostart och avslutningsgenväg.

## Data och modeller

Allt runtime-data ligger under `data/` (kan ändras med `app.data_root`):

```text
data/
├── datasets/<namn>/
│   ├── images/                 # bilder lagras en gång
│   ├── annotations/instances.json
│   ├── versions/v000001.json   # oföränderliga snapshots + manifest
│   └── meta.json
├── models/<körning>/<datasetversion>_<timestamp>/
│   ├── best.pt / best.pth
│   └── training_manifest.json
├── exports/
├── training_runs/
└── logs/
```

Tränade modeller hittas automatiskt av modellregistret och blir valbara i
detektionsläget. Datasetversionen i modellens manifest är samma version som
användes vid träningen.

Split mellan train/val görs per bildpar (`pair_id`) för att undvika läckage
mellan närliggande bilder från samma scen.

## Test och kvalitet

```powershell
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
```

Testerna använder syntetiska videokällor och en fejkad detektor, så de kräver
varken GPU eller kameror.

## Bygga exe (valfritt)

```powershell
uv sync --extra ml --extra build
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

PyInstaller bygger en `one-dir`-distribution eftersom PyTorch, PySide6 och
RF-DETR är stora. `data/`, `config/` och modellvikter hålls utanför exe-filen.

## Kända begränsningar

- RF-DETR:s tränings-API varierar mellan versioner; workern skickar bara
  parametrar som den installerade versionen stödjer och rapporterar tydligt om
  träningen inte kan startas.
- Första starten av en YOLO-modell kan ladda ner förtränade vikter.
- Applikationen är utvecklad för Windows 11 med CUDA men kan köras med
  `test_pattern`/videofiler och CPU för utveckling och test.
