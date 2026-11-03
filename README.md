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
- NVIDIA GPU med CUDA 12.x + cuDNN (för GPU-inferens/träning)
- OpenCV med DSHOW (Windows) / V4L2 (Linux)
- Två UVC capture-kort via USB3 (på måldatorn)

## Installation

### Linux (utveckling)

```bash
./setup.sh
source .venv/bin/activate
python main.py
```

### Windows 11 (mål)

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
python main.py
```

Säkerställ att CUDA 12 + cuDNN är installerat systemvänt för GPU-stöd.
UVC-kort används via OpenCV:s DSHOW-backend (väljs automatiskt på Windows).

## Konfiguration

`config.yaml` styr kameror, modeller, trösklar, klasser och träningsdefaults.
Se filen för alla alternativ. Viktigaste:

- `capture.streams` – index/resolution/FPS per capture-kort
- `detection.model_left` / `model_right` – .pt-vikter per ström
- `detection.preprocess` – `auto` (gråskala+CLAHE), `invert`, `none`, `clahe`
- `classes` – initial klasslista

## Användning

| Tangent | Funktion |
|---|---|
| `F` | Fånga bilder från båda strömmarna → annotering |
| `F11` | Fullscreen på/av |
| `1` | Detektionsläge |
| `3` | Träningsläge |
| `Delete` | Ta bort markerad rektangel (i annotering) |

Flöde: **Detektera → Fånga (F) → Annotera → Spara → (Dataset) Exportera YOLO →
Träna → Ladda ny modell → Detektera.**

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
├── requirements.txt
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
