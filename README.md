# X-ray detector

Applikation för detektion av objekt i video med röntgenbilder. Tre lägen:
**detektion** (live, split screen), **annotering** (skapa träningsdata) och
**träning** (träna modell).

Se `specs.md` för krav och `implementation_plan.md` för arkitektur.

## Funktioner

- **Detektionsläge** – två videoströmmar i split screen med live-detektering
  (rektangel + klass + sannolikhet). Fångaknapp (tangent `F`) tar bild +
  detektioner till annoteringsläget.
- **Annoteringsläge** – rita/redigera rektanglar (kant/hörn), välj eller skapa
  klasser, spara till dataset (COCO).
- **Träningsläge** – välj basmodell + dataset + parametrar, kör träning, spara
  vikter med versionsnummer kopplat till dataset.
- Kioskläge (fullscreen), trådat för ingen väntetid, träning pausar detektion.

## Krav

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (hanterar Python, `.venv` och låsta beroenden)
- NVIDIA GPU med CUDA 12.x + cuDNN (för GPU-inferens/träning)
- OpenCV med DSHOW (Windows) / V4L2 (Linux)
- Två UVC capture-kort via USB3 (på måldatorn)

## Installation

Projektet använder [uv](https://docs.astral.sh/uv/). `uv sync` skapar `.venv`
och installerar exakta versioner från `uv.lock`.

Installera uv om det saknas:

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Linux (utveckling)

```bash
./setup.sh
uv run python main.py
```

### Windows 11 (mål)

```powershell
uv sync
uv run python main.py
```

`uv sync` laddar automatiskt ner den Python-version som `.python-version` anger
(om filen finns) om den inte redan är installerad. Du behöver inte aktivera
`.venv` – `uv run` använder projektets miljö automatiskt.

Säkerställ att CUDA 12 + cuDNN är installerat systemvänt för GPU-stöd.
UVC-kort används via OpenCV:s DSHOW-backend (väljs automatiskt på Windows).

## Beroenden

Beroenden deklareras i `pyproject.toml` och låses i `uv.lock`.

```bash
uv add <paket>            # lägg till ett beroende
uv sync                   # uppdatera .venv från låsfilen
uv lock --upgrade         # uppdatera låsta versioner
uv run python main.py     # kör i projektets miljö
```

### GPU (CUDA)

`pyproject.toml` hämtar CUDA-byggda `torch`/`torchvision` från PyTorchs
`cu130`-index (kräver NVIDIA-drivrutin med CUDA 13.x). Det behövs för RTX
50-serien (sm_120) och annan modern NVIDIA-hårdvara.

Kontrollera efter `uv sync`:

```bash
uv run python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

Vid äldre drivrutin: byt `cu130` mot `cu128` i `pyproject.toml` och kör
`uv lock && uv sync`. Saknas CUDA helt faller appen automatiskt tillbaka på CPU
(och loggar en varning).

## Konfiguration

`config.yaml` styr kameror, modeller, trösklar, klasser och träningsdefaults.
Se filen för alla alternativ. Viktigaste:

- `capture.streams` – index/resolution/FPS per capture-kort
- `detection.model_left` / `model_right` – .pt-vikter per ström
- `detection.device` – GPU-index (`-1` = CPU; faller tillbaka på CPU automatiskt)
- `detection.quantize` – `fp16` (default på GPU) eller `fp32` (tvingas på CPU)
- `detection.preprocess` – `auto` (CLAHE, bevarar färg), `invert`, `none`, `clahe`
- `classes` – initial klasslista

Äldre `detection.half: true/false` fungerar fortfarande och mappas automatiskt
till `quantize: fp16/fp32`.

## Användning

| Tangent | Funktion |
|---|---|
| `F` | Fånga bilder → annotering (fungerar även med bara en ansluten ström) |
| `F11` | Fullscreen på/av |
| `1` | Detektionsläge |
| `3` | Träningsläge |
| `Delete` | Ta bort markerad rektangel (i annotering) |

Flöde: **Detektera → Fånga (F) → Annotera → Spara → (Dataset) Exportera YOLO →
Träna → Ladda ny modell → Detektera.** När annoteringen sparas återgår appen
automatiskt till detektionsläget.

Om bara ett capture-kort är anslutet visas den anslutna strömmen som vanligt
medan den andra visar en svart skärm med texten **Ingen videokälla**.

## Dataset

- Kanoniskt format: **COCO** i `data/datasets/<version>/`
  (`images/`, `annotations.json`, `meta.json`).
- Export till **YOLO** (`labels/` + `data.yaml`) via Dataset-dialogen.
- Versionering: `v1`, `v2`, … med metadata (datum, antal bilder/objekt).

## Projektstruktur

```
xray-detector/
├── main.py                  # Entry point
├── config.yaml              # Konfiguration
├── pyproject.toml           # Projekt + beroenden
├── uv.lock                  # Låsta beroenden
├── setup.sh
├── specs.md
├── implementation_plan.md
└── xray_detector/
    ├── app.py               # MainWindow, orkestrering
    ├── config.py            # Pydantic-config
    ├── capture/             # camera.py, capture_worker.py
    ├── detection/           # model_registry, inference_worker, preprocess
    ├── annotation/          # annotation_canvas, annotation_view
    ├── dataset/             # coco, dataset_manager, yolo_export
    ├── training/            # trainer, training_view
    └── ui/                  # detection_view, dataset_dialog
```
