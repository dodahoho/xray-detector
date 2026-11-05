# Implementationsplan – X-ray detector

> Baserad på `specs.md`. Beslut fattade 2026-11-03:
> **GUI:** PySide6 (Qt) · **GPU:** NVIDIA/CUDA · **Klasser:** cigaretter, cannabis, kniv, handgranat · **Dataset:** COCO internt + YOLO-export · **Deploy:** utvecklas på Linux, körs på Windows 11 (två UVC capture cards via USB3)

---

## 1. Mål

Desktopapplikation (PySide6) med tre lägen:

1. **Detektionsläge** (default) – split screen av två videoströmmar med live-detektering, fånga-knapp.
2. **Annoteringsläge** – frysta bilder, rita/redigera rektanglar, välja/skapa klasser, spara till dataset.
3. **Träningsläge** – välj basmodell + dataset + parametrar, kör träning, spara vikter med versionsnummer.

Krav: kioskläge (fullscreen), ingen upplevd väntetid (trådat), träning pausar detektion.

---

## 2. Tech stack

| Område | Val | Motivering |
|---|---|---|
| GUI | **PySide6** (Qt 6) | Nativt fullscreen/kioskläge, låg latens, Canvas-widget för annotation |
| Video | **OpenCV** (`cv2.VideoCapture`) | DSHOW-backend på Windows, V4L2 på Linux – samma kod |
| Detektion | **Ultralytics** (YOLO26, RF-DETR) | En API för flera modeller, GPU-stöd, inbyggd träning |
| Dataset | **COCO-format** (JSON + bilder) | Uttrycksfullt, enkelt att versionera; YOLO-export är trivial |
| Konfiguration | **Pydantic + YAML** | Validerad config, lätt att redigera |
| Logging | **loguru** | Enkel, strukturerad loggning |
| Packning (Windows) | **PyInstaller** (senare fas) | Exe för kioskdatorn |

Python 3.10+. CUDA 12.x + cuDNN på måldatorn.

---

## 3. Arkitektur

### 3.1 Trådmodell (Qt)

```
┌─────────────────────────────────────────────────────────────┐
│ GUI-tråd (Qt main thread)                                    │
│  MainWindow → DetectionView / AnnotationView / TrainingView  │
└──────────────▲──────────────────────────────▲───────────────┘
               │ signals (frames, results)    │ signals (progress)
┌──────────────┴───────────┐   ┌──────────────┴───────────────┐
│ CaptureWorker (QThread)  │   │ InferenceWorker (QThread)     │
│  ×2, en per stream       │   │  tar nyaste frame per stream  │
│  cv2.VideoCapture loop   │──▶│  kör modell, skickar results  │
└──────────────────────────┘   └───────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ TrainingWorker (QProcess/QThread) – separat, pausar detek-  │
│ tionen via signal när den startar                            │
└─────────────────────────────────────────────────────────────┘
```

**Principer:**
- Varje capture-kort har egen `QThread` som läser frames i en loop (fast FPS, t.ex. 30).
- `InferenceWorker` hämtar **nyaste** frame per stream (drop-oldest-mönster) – gamla frames kasseras så detektion aldrig "hänger efter".
- Frames/results överförs till GUI via Qt-signaler (thread-safe).
- Annotation och träning körs aldrig i GUI-tråden.
- Vid träning: `TrainingWorker` sänder `training_started` → detektion pausas (capture kan fortsätta men inference stängs av, eller capture pausas helt för att frigöra USB/CPU).

### 3.2 Modulstruktur

```
xray-detector/
├── main.py                     # Entry point, startar QApplication
├── pyproject.toml              # Projekt + beroenden (uv)
├── uv.lock                     # Låsta beroenden
├── setup.sh
├── config.yaml                 # kameror, modeller, dataset-path, klasser
├── specs.md
├── implementation_plan.md
├── xray_detector/
│   ├── __init__.py
│   ├── config.py               # Pydantic-config, laddar config.yaml
│   ├── app.py                  # MainWindow, lägesväxling, fullscreen/kiosk
│   ├── capture/
│   │   ├── camera.py           # CameraSource: backend-val (DSHOW/V4L2), open/close
│   │   └── capture_worker.py   # QThread: read-loop, signal frame_ready(idx, frame)
│   ├── detection/
│   │   ├── model_registry.py   # abstrakt BaseModel + YOLO26/RF-DETR-adaptrar
│   │   └── inference_worker.py # QThread: inferens, signal detections_ready(idx, dets)
│   ├── annotation/
│   │   ├── annotation_canvas.py# QWidget: rita/dra rektanglar (kant/hörn), klass-tagg
│   │   └── annotation_view.py  # två canvases + klasslista + spara-knapp
│   ├── dataset/
│   │   ├── coco.py             # COCO read/write (images, annotations, categories)
│   │   ├── dataset_manager.py  # versionering, metadata, tillägg av bilder
│   │   └── yolo_export.py      # COCO → YOLO (labels + data.yaml)
│   ├── training/
│   │   ├── trainer.py          # QProcess/QThread: ultralytics train, progress-parsning
│   │   └── training_view.py    # UI: modell, dataset, parametrar, logg, status
│   └── ui/
│       ├── detection_view.py   # split screen, overlay, fånga-knapp
│       └── widgets.py          # delade widgets (statusbar, klasslista m.m.)
├── data/
│   └── datasets/               # COCO-dataset (v1/, v2/, ...)
├── models/                     # nedladdade basmodeller + tränade vikter
└── runs/                       # träningsloggar/artefakter
```

### 3.3 Nyckelklasser (skiss)

```python
# model_registry.py
class BaseModel(ABC):
    def load(self, path: str) -> None: ...
    def predict(self, frame: np.ndarray) -> list[Detection]: ...
    @property
    def classes(self) -> list[str]: ...

class YOLO26Model(BaseModel): ...   # ultralytics.YOLO
class RFDETRModel(BaseModel): ...   # ultralytics.YOLO (rfdetr-*.pt)

# dataset_manager.py
class DatasetManager:
    def create_version(self, base: str) -> str          # "v3"
    def add_images(self, images: list[np.ndarray],
                   annotations: list[Annotation]) -> None
    def metadata(self) -> dict                          # version, datum, antal bilder/objekt
    def export_yolo(self, out_dir: Path) -> None

# trainer.py
class TrainingWorker(QThread):
    progress = Signal(str)          # logglinje
    finished_ok = Signal(str)       # path till sparade vikter
    def run(self): ...              # model.train(...), rename till <modell>_<datasetversion>.pt
```

---

## 4. Lägen i detalj

### 4.1 Detektionsläge
- `DetectionView`: två `QLabel`/`QGraphicsView` i split screen (vänster/höger).
- Varje frame renderas med overlay: rektangel + `klass: 0.87` (OpenCV `putText` eller Qt-paint).
- **Fångaknapp** (tangent `F` + knapp): tar nyaste frame från båda strömmarna **samt** detektionerna som fanns på just den runden → byter till annoteringsläge med förinritade rektanglar.
- Statusbar: FPS per stream, modellnamn, GPU-användning (valfritt).
- Konfiguration: vilken modell per stream (kan skilja sig), conf/IoU-trösklar.

### 4.2 Annoteringsläge
- `AnnotationView`: två `AnnotationCanvas` (frysta bilder) + klasspanel.
- `AnnotationCanvas` (QGraphicsView-baserad):
  - **Ny rektangel:** dra med vänster musknapp.
  - **Redigera:** dra i kant (flytta/ändra storlek) eller hörn (resiz) – standard QGraphicsItem-interaktion med `ChangeBoundingRect`/`ChangeGeometry`.
  - **Ta bort:** markera + Delete.
  - Varje rektangel har klass-attribut; klick på rektangel + välj klass i listan (eller skriv ny klass i fält → läggs till i kategorilistan).
- **Spara:** skapar/tillägger i aktuella dataset-version (COCO), återgår till detektionsläge.
- **Avbryt:** kassera, återgå utan att spara.

### 4.3 Träningsläge
- `TrainingView`:
  - Basmodell: dropdown (yolo26n/s/l, rfdetr-l m.fl. – från `models/`).
  - Dataset: dropdown över tillgängliga versioner (visar version, datum, antal bilder/objekt).
  - Parametrar: epochs, imgsz, batch, lr, device (GPU/CPU) – med rimliga defaults.
  - Start/Avbryt-knappar, live-logg (parsar ultralytics-utmatning), progress.
- Vid slutförande: vikter sparas som `models/<basmodell>_<datasetversion>_<datum>.pt` och registreras i model_registry så de kan väljas i detektionsläget.
- Under pågående träning: detektion pausad (signal), GUI visar "Träning pågår".

---

## 5. Dataset & versionering

- **Kanoniskt format: COCO** i `data/datasets/<version>/`:
  ```
  v3/
  ├── images/          # 000001.jpg, ...
  ├── annotations.json # COCO: images, annotations, categories
  └── meta.json        # {version, created, base_model?, num_images, num_objects, source}
  ```
- Varje "spara" i annoteringsläget lägger till i **aktuella** versionen; ny version skapas explicit (t.ex. "Ny version" i dataset-vy eller automatiskt vid export).
- **Export till YOLO:** `yolo_export.py` genererar `labels/*.txt` + `data.yaml` (class_names från COCO categories) i `data/datasets/<version>/yolo/`.
- Klasslista (categories) är global per dataset-version; nya klasser i annoteringsläget läggs till i kategorilistan.
- Initial klasslista: `cigaretter, cannabis, kniv, handgranat` (i `config.yaml`).

---

## 6. Fasplan

### Fas 1 – Grundstruktur (dag 1)
- [ ] `pyproject.toml` + `uv.lock` (PySide6, opencv-python, ultralytics, pydantic, loguru, numpy) hanteras med uv
- [ ] `config.yaml` + `config.py` (Pydantic): kameraindex, backend, klasser, paths, trösklar
- [ ] `main.py` + `app.py`: MainWindow med lägesväxling (stacked widget), fullscreen-toggle (F11), kiosk-läge
- [ ] Projektstruktur enligt §3.2, `.gitignore` uppdaterad (data/, models/, runs/)

### Fas 2 – Video capture (dag 1–2)
- [ ] `camera.py`: öppna `cv2.VideoCapture(index, backend)` – DSHOW på Windows, V4L2 på Linux; resolution/FPS-config
- [ ] `capture_worker.py`: QThread per stream, read-loop, `frame_ready` signal, drop-oldest
- [ ] Test: visa råa strömmar i två QLabels (split screen) utan detektion
- [ ] Hantera: kort saknas, USB-disconnect, omstart av capture

### Fas 3 – Detektionsläge (dag 2–4)
- [ ] `model_registry.py`: BaseModel + YOLO26 + RF-DETR (ultralytics), ladda från `models/`
- [ ] `inference_worker.py`: QThread, nyaste frame per stream, `detections_ready` signal
- [ ] `detection_view.py`: overlay (box + klass + conf), split screen, statusbar (FPS)
- [ ] Fångaknapp + tangent `F`: spara frame + detektioner → byt till annoteringsläge
- [ ] Modellval per stream i config/UI

### Fas 4 – Dataset (dag 4–5)
- [ ] `coco.py`: lägg till bilder + annotations, läsa/skriva COCO JSON
- [ ] `dataset_manager.py`: versioner, meta.json, antal bilder/objekt
- [ ] `yolo_export.py`: COCO → YOLO labels + data.yaml
- [ ] Enkel dataset-vy i GUI (lista över versioner, export-knapp)

### Fas 5 – Annoteringsläge (dag 5–8)
- [ ] `annotation_canvas.py`: rita rektangel, dra i kant/hörn, ta bort, klass per rektangel
- [ ] Förinritning av befintliga detektioner (från fånga)
- [ ] Klasspanel: dropdown + "ny klass"-fält
- [ ] `annotation_view.py`: två canvases, Spara (→ dataset) / Avbryt
- [ ] Test: spara → verifiera COCO JSON + YOLO-export

### Fas 6 – Träningsläge (dag 8–10)
- [ ] `trainer.py`: QProcess/QThread som kör `model.train(...)`, parsar progress/logg
- [ ] `training_view.py`: dropdowns (modell, dataset), parametrar, start/avbryt, loggvy
- [ ] Pausa detektion under träning (signal), återuppta efter
- [ ] Spara vikter med versionsnamn + registrera i model_registry
- [ ] Test: träna kort (få epochs) på litet dataset, ladda resultatet i detektionsläge

### Fas 7 – Kiosk & prestanda (dag 10–11)
- [ ] Fullscreen/kioskläge: auto-start, ingen taskbar, tangentbordsflöde (F=fånga, F11=fullscreen, Esc=avbryt annotation)
- [ ] Prestanda: mät FPS + inferenslatens, optimera (GPU half-precision, `quantize="fp16"`, batch=1, `device=0`)
- [ ] Träningsplanering: "köra träning nattetid" – enkel tidsplanerare (t.ex. starta kl X om ingen aktivitet) eller dokumenterad manuell start
- [ ] Robusthet: auto-restart av capture vid fel, loggning, crash-säkerhet

### Fas 8 – Windows-deploy (dag 11–12)
- [ ] Testa på Windows 11: DSHOW-backend, USB3-bandbredd för två strömmar, CUDA
- [ ] `setup.sh` → `setup.ps1`/`setup.bat` för Windows (Python, CUDA, `uv sync`)
- [ ] PyInstaller-spec för exe (inkl. CUDA-libs – kan kräva att CUDA finns installerat systemvänt)
- [ ] README: installation, konfiguration, drift

---

## 7. Konfiguration (config.yaml – skiss)

```yaml
app:
  fullscreen: true
  kiosk: false
capture:
  backend: auto            # auto | dshow | v4l2
  streams:
    - index: 0
      width: 1920
      height: 1080
      fps: 30
    - index: 1
      width: 1920
      height: 1080
      fps: 30
detection:
  model_left: models/yolo26n_v1_20261103.pt
  model_right: models/yolo26n_v1_20261103.pt
  conf: 0.4
  iou: 0.5
  device: 0                # GPU
  quantize: fp16
classes:
  - cigaretter
  - cannabis
  - kniv
  - handgranat
dataset:
  root: data/datasets
training:
  default_epochs: 100
  default_imgsz: 640
  default_batch: 16
  runs_dir: runs
```

---

## 8. Risker & mitigering

| Risk | Påverkan | Mitigering |
|---|---|---|
| USB3-bandbredd räcker inte för två strömmar | Bildförlust/lag | Lägre resolution/FPS per stream, testa tidigt (Fas 2) |
| UVC-kort har hög latens | "Live" känns seg | Mät i Fas 2; välj lägst latens-backend; drop-oldest |
| RF-DETR-stöd i ultralytics varierar | Modell saknas | YOLO26 som primär; RF-DETR som valfri (testa tidigt i Fas 3) |
| PyInstaller + CUDA är klumpigt | Deploy svårt | Alternativ: portabel Python + startskript istället för exe |
| Röntgenbilder kan kräva förbehandling (invertering/kontrast) | Dålig detektion | Konfigurerbar preprocessor per stream (gråskala, invertera, CLAHE) – lägg in i Fas 3 om behövs |
| Träning på samma maskin som detektion | Resurskonflikt | Detektion pausas under träning (spec); GPU-memori: `batch`-val i träning |

---

## 9. Öppna frågor (att bekräfta under utveckling)

1. **Capture-kortens spec:** vilken resolution/FPS stödjer de? (påverkar config defaults)
2. **Röntgenbildens utseende:** är bilderna gråskala/inverterade? Behövs förbehandling?
3. **Träningsplanering:** ska "nattetid" vara en inbyggd tidsplanerare eller räcker manuell start + paus?
4. **Flera klasser per objekt:** kan samma bild ha t.ex. både kniv och cigaretter? (Antas ja – COCO hanterar det.)
5. **Kioskdatorn:** finns den tillgänglig för test under utvecklingen, eller testas Windows-delen först i Fas 8?

---

## 10. Definition of done

- [ ] Alla tre lägen fungerar end-to-end: detektera → fånga → annotera → spara → exportera → träna → ladda ny modell → detektera
- [ ] Fullscreen/kioskläge fungerar utan väntetid
- [ ] Dataset i COCO med korrekt versionering + YOLO-export
- [ ] Tränade vikter sparas med versionsnummer kopplat till dataset
- [ ] Kör på Windows 11 med två UVC-kort + NVIDIA GPU
- [ ] README med installation & drift
