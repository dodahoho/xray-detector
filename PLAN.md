# Implementationsplan – X-ray detector

Planen utgår från `specs.md` samt de vägval som bekräftats:

- **Stack:** Python + PySide6/Qt, paketerat med `uv`.
- **Modeller:** både Ultralytics YOLO och RF-DETR från start, via ett gemensamt detektor-API.
- **Hårdvara:** NVIDIA GPU med CUDA för inferens och träning, med CPU-fallback.
- **Dataset:** COCO som internt format, export till YOLO (och COCO).
- **Videokällor:** auto-detektering av UVC-enheter, 1080p/30 fps som standard. Webkamera och videofiler ska kunna användas för test.
- **Två strömmar:** bilderna är ett par från samma scen/objekt i två vinklar.
- **Versionering:** dataset får automatiskt ny version vid varje sparsession; tränade modeller ärver datasetets version.
- **Distribution:** primärt Python-miljö med `uv`; fristående `.exe` via PyInstaller är en senare möjlighet.

---

## 1. Antaganden

1. Applikationen körs lokalt på en Windows 11-dator utan server/backend.
2. En användare/operatör åt gången.
3. Endast axis-aligned rektanglar (inte polygoner/segmentation).
4. Flera dataset ska stödjas, men `default` används initialt.
5. Klasslistan byggs som union av modellens klasser, datasetets kategorier och fritext som användaren skriver in.
6. Borttagning av annoteringar ingår även om det inte explicit står i specen.
7. Träning körs i separat process för att skydda GUI:t och frigöra GPU-minne.
8. UI-strängar hålls centraliserade så att svenska/engelska kan väljas senare; initialt svenska.
9. Inga molntjänster eller nätverksberoenden krävs vid drift.

---

## 2. Arkitektur

```
┌─────────────────────────────────────────────────────────────┐
│                         UI (Qt)                             │
│  MainWindow → DetectionView | AnnotationView | TrainingView │
│  SettingsDialog, VideoPanel, AnnotationCanvas, BBoxItem     │
└───────────────────────────┬─────────────────────────────────┘
                            │ signaler/slots
┌───────────────────────────▼─────────────────────────────────┐
│                    Application services                     │
│  DetectionService, AnnotationService, DatasetService,       │
│  TrainingService, ModelRegistry, AppConfig                  │
└───────────────┬──────────────────────────┬──────────────────┘
                │                          │
┌───────────────▼──────────────┐  ┌────────▼──────────────────┐
│       Domänmodell            │  │      Infrastruktur        │
│ Detection, BBox, Annotation, │  │ Video, Detectors,         │
│ Dataset, DatasetVersion,     │  │ COCO-store, Export,       │
│ ModelArtifact, TrainingJob   │  │ Training runners          │
└──────────────────────────────┘  └───────────────────────────┘
```

### Trådning

- **GUI-tråd:** endast rendering och användarinteraktion.
- **CaptureWorker (QThread) per videokälla:** läser frames, håller senaste frame, hanterar återanslutning.
- **InferenceWorker (QThread):** en GPU-arbetare som betjänar båda strömmarna, droppar inaktuella frames och publicerar detektioner med frame-ID.
- **TrainingRunner (separat process via `QProcess`):** isolerar träning, möjliggör avbrott och undviker att GUI/GPU kraschar.
- **FrameBuffer:** trådsäker "latest frame + sekvensnummer" per källa. Capture-knappen hämtar atomiskt senaste frame + senaste detektioner.

Viktigt: varje detektionsresultat taggas med frame-ID så att UI aldrig ritar boxar på fel bildruta.

---

## 3. Föreslagen katalogstruktur

```
xray-detector/
├── pyproject.toml
├── uv.lock
├── README.md
├── PLAN.md
├── config/
│   ├── default.yaml
│   └── models.yaml
├── src/xray_detector/
│   ├── main.py
│   ├── app.py
│   ├── config.py
│   ├── domain/
│   │   ├── detection.py
│   │   ├── annotation.py
│   │   ├── dataset.py
│   │   ├── model_artifact.py
│   │   └── training.py
│   ├── application/
│   │   ├── detection_service.py
│   │   ├── annotation_service.py
│   │   ├── dataset_service.py
│   │   ├── training_service.py
│   │   └── model_registry.py
│   ├── infrastructure/
│   │   ├── video/
│   │   │   ├── source.py
│   │   │   ├── opencv_source.py
│   │   │   ├── device_discovery.py
│   │   │   └── frame_buffer.py
│   │   ├── detectors/
│   │   │   ├── base.py
│   │   │   ├── ultralytics_yolo.py
│   │   │   ├── rfdetr_detector.py
│   │   │   └── registry.py
│   │   ├── dataset_store/
│   │   │   ├── coco_store.py
│   │   │   ├── versioning.py
│   │   │   ├── yolo_export.py
│   │   │   └── coco_export.py
│   │   └── training/
│   │       ├── runner.py
│   │       ├── yolo_train.py
│   │       └── rfdetr_train.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── views/
│   │   │   ├── detection_view.py
│   │   │   ├── annotation_view.py
│   │   │   └── training_view.py
│   │   ├── dialogs/settings_dialog.py
│   │   ├── widgets/
│   │   │   ├── video_panel.py
│   │   │   ├── annotation_canvas.py
│   │   │   ├── bbox_item.py
│   │   │   └── class_selector.py
│   │   └── theme.py
│   └── resources/
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
│   └── build_exe.ps1
└── data/                    # gitignored
    ├── datasets/
    ├── models/
    ├── exports/
    ├── training_runs/
    └── logs/
```

---

## 4. Domänmodell och datasetlagring

### 4.1 Datasetlayout

```
data/datasets/<dataset_name>/
├── meta.json                     # namn, skapad, senaste version, nästa version
├── images/
│   ├── <pair_id>_cam0.jpg
│   └── <pair_id>_cam1.jpg
├── annotations/
│   └── instances.json            # aktuell COCO-annotering
├── versions/
│   ├── v000001.json              # fryst annoteringssnapshot + metadata
│   └── v000002.json
└── exports/                      # valfritt, eller centralt under data/exports
```

- Bilderna lagras en gång och delas mellan versioner.
- Varje version är en **oföränderlig snapshot** av annoteringarna.
- `versions/vNNNNNN.json` innehåller: version, datum/tid, antal bilder, antal bildpar, antal annoteringar, antal per klass, lista med bild-ID:n och en hash av annoteringsfilen.
- Varje sparsession i annoteringsläget skapar exakt en ny version.
- COCO utökas med anpassade fält på bildnivå: `pair_id`, `camera_role` (`cam0`/`cam1`), `source` och `captured_at`. Detta påverkar inte standard-COCO-läsare.

### 4.2 Klasshantering

- Kategorier har stabila ID:n och unika namn.
- Nya klasser läggs till i datasetets kategorilista när användaren skriver in dem.
- Automatiska detektioner mappas till datasetkategorier via klassnamn; saknad klass skapas automatiskt eller visas med varning.

### 4.3 Versionering av modeller

```
data/models/<run_name>/
└── v<dataset_version>_<timestamp>/
    ├── best.pt / best.pth
    ├── last.pt
    └── training_manifest.json
```

`training_manifest.json` innehåller minst: datasetnamn, datasetversion, basmodell, träningsparametrar, datum, metrics och eventuell git-commit. Modellens versionssiffra kopplas alltså alltid till datasetversionen.

### 4.4 Export

- **COCO-export:** `annotations.json` + bilder + `manifest.json` med version, datum och antal bildobjekt.
- **YOLO-export:** `images/{train,val}`, `labels/{train,val}`, `data.yaml` + `manifest.json`.
- Train/val-split görs **per bildpar** (`pair_id`), inte per bild, för att undvika läckage mellan träning och validering.
- Splitkvot görs konfigurerbar med deterministisk seed; standard t.ex. 80/20 eller 80/10/10.
- Exporten får aldrig ändra datasetets aktuella version.

---

## 5. Videopipeline

### 5.1 Källor

- `VideoSource`-abstraktion med implementationer för:
  - UVC-enhet via OpenCV (`CAP_DSHOW` i första hand, `CAP_MSMF` som fallback).
  - Webkamera (samma mekanism, annan enhet).
  - Videofil (loopbar eller fryst sista frame).
- `device_discovery` listar tillgängliga enheter med namn/index på Windows.
- Standard: 1920×1080, 30 fps, men upplösning, fps och backend ska vara konfigurerbart per källa.
- Källor konfigureras som `cam0` och `cam1`; varje källa kan vara enhet eller fil.

### 5.2 Capture

- En `CaptureWorker` per källa.
- Läser frames i egen tråd, tidsstämplar dem och lägger dem i en `FrameBuffer`.
- Vid fel: exponentiell backoff och återanslutning; status visas i UI.
- Preview throttlas till skärmens behov (max ~30 fps) medan inferens kan köras på senaste tillgängliga frame.

### 5.3 Inferens

- Gemensamt `Detector`-interface:

```python
class Detector(Protocol):
    def load(self, model_path: Path, device: str) -> None: ...
    def predict(self, frame_bgr: np.ndarray) -> list[Detection]: ...
    @property
    def classes(self) -> dict[int, str]: ...
    @property
    def metadata(self) -> ModelMetadata: ...
```

- `Detection` innehåller `bbox_xyxy`, `score`, `class_id`, `class_name`.
- Adaptrar:
  - `UltralyticsYoloDetector` – laddar YOLO-modell, stödjer YOLO26 när vikter finns tillgängliga, annars befintliga YOLO-modeller.
  - `RfDetrDetector` – anpassad till RF-DETR:s API; håller API-skillnader isolerade.
- En `InferenceWorker` ansvarar för båda strömmarna och kör dem sekventiellt på GPU:n. Detta undviker konkurrens om CUDA-minne och ger förutsägbart beteende.
- Parametrar: `conf`, `iou`, `imgsz`, `device` (standard `cuda:0` med fallback till `cpu`), half precision där modellen stödjer det.
- Modellen laddas en gång och värms upp vid start/byte.
- Prestandamätning: FPS per ström, inferenslatens, antal droppade frames; loggas och visas diskret i UI.

### 5.4 Paus vid annotering och träning

- När annoteringsläget öppnas pausas inferensen och capture-trådarna kan pausas för att spara resurser.
- När träningsläget startar stoppas hela detektionspipelines och CUDA-minne frigörs innan träningsprocessen startar (konfigurerbart).
- Efter avslutad annotering/träning återstartas pipelinen automatiskt.

---

## 6. Detektionsläge (standard)

- Split screen med två videopaneler, en per ström.
- Varje panel visar:
  - video i realtid,
  - rektanglar med klassnamn och sannolikhet,
  - status (FPS, enhet, modell).
- Modell väljs från `ModelRegistry` (förtränade och tränade modeller).
- Knapp **"Fånga"**:
  1. Hämtar atomiskt senaste frame och senaste detektioner från båda strömmarna.
  2. Skapar ett bildpar med gemensamt `pair_id`.
  3. Byter till annoteringsläget med båda bilderna och detektionerna förifyllda.
- Om en ström saknar frame vid fångst: visa tydligt fel och avbryt.
- Fullscreen/kiosk: `F11` växlar, `Esc` lämnar fullscreen i normalläge.

---

## 7. Annoteringsläge

### 7.1 Vy

- Två frysta bilder sida vid sida i var sin `AnnotationCanvas`.
- Varje canvas: zoom/pan, "fit to window", bakgrundsbild i rätt bildkoordinatsystem.
- Verktyg: markera/flytta, rita ny rektangel, ändra storlek, ta bort.
- Rektangelobjekt (`BBoxItem`) har 8 handtag (hörn + sidor) och tydlig markeringsfeedback.
- Klassväljare: redigerbar combobox med befintliga klasser; val av klass gäller markerad box eller nästa nya box.
- Lista över annoteringar per bild med möjlighet att markera, byta klass och ta bort.
- Klassfärger hålls konsekventa mellan bilderna.

### 7.2 Automatiska detektioner

- Vid inträde ritas alla detektioner från fångsttillfället in som vanliga, redigerbara boxar.
- Klass och score bevaras som metadata men score visas inte som obligatoriskt fält i datasetet.
- Automatiska boxar kan flyttas, storleksändras, byta klass och tas bort precis som manuella.

### 7.3 Spara

- Validering: minsta boxstorlek, box inom bilden, klass angiven.
- Båda bilderna och alla annoteringar sparas som **ett bildpar** och en ny datasetversion skapas automatiskt.
- Därefter återgår applikationen till detektionsläget och återstartar videopipelinen.
- **Avbryt** kastar ändringarna och återgår utan att skapa version.
- Valfri draft/autosave till `data/tmp` för att undvika dataförlust vid krasch (fas 7).

### 7.4 Genvägar

- `Del` tar bort markerad box.
- `Esc` avbryter/avmarkerar.
- `Ctrl+S` sparar.
- Siffertangenter kan välja klass 1–9.

---

## 8. Träningsläge

### 8.1 Formulär

- Dataset (namn + version).
- Basmodell från `ModelRegistry` eller fil.
- Träningstyp/familj: YOLO eller RF-DETR.
- Parametrar: epochs, batch, imgsz, learning rate, patience, augmentation, device, workers.
- Utdata: namn på körning samt förväntad modellversion (datasetets version).
- Validering av diskutrymme, GPU-minne och att valt dataset har tillräckligt många bilder/klasser.

### 8.2 Körning

- Träning startas manuellt.
- Innan start: varna och pausa detektionen (standardval) så att GPU-resurser frigörs.
- Datasetet exporteras till ett temporärt träningsarbetsområde i rätt format:
  - YOLO-format för Ultralytics.
  - COCO-format för RF-DETR (om dess tränings-API kräver det).
- Träningen körs i separat process. `TrainingService` skickar JSON-konfiguration och strömmar logg till UI:t.
- Avbrott ska vara möjligt; processen ska då avslutas kontrollerat och inte lämna korrupta modellfiler.
- Förlopp och metrics visas i en loggpanel; där API:t tillåter parsas epoch/val-metrics.

### 8.3 Efter avslut

- Bästa vikter sparas under `data/models/<run_name>/v<dataset_version>_<timestamp>/`.
- `training_manifest.json` skrivs med dataset, version, parametrar, datum, metrics och basmodell.
- `ModelRegistry` uppdateras och modellen blir valbar i detektionsläget.
- Vid fel sparas logg och ett tydligt felmeddelande visas; inga halvfärdiga modeller markeras som giltiga.

### 8.4 Schemaläggning

- Manuell start är grundkravet.
- Som tillägg: "starta vid angiven tid" och/eller "vänta tills datorn varit inaktiv i N minuter".
- Vid schemalagd start pausas detektionen automatiskt och användaren informeras.

---

## 9. Inställningar, konfiguration och kioskläge

- `config/default.yaml` med rimliga standardvärden checkas in.
- Användaröverstyrning sparas i `%APPDATA%/XrayDetector/config.yaml`.
- Inställningsdialog:
  - videokällor (enhet/fil, upplösning, fps, backend),
  - standardmodell och trösklar,
  - dataset- och modellmappar,
  - GPU/CPU,
  - fullscreen/kiosk, avslutningsgenväg, gömd muspekare,
  - autostart av detektion.
- Kioskläge:
  - startar i fullscreen,
  - döljer menyrad/verktygsfält,
  - avslutas endast med konfigurerad kombination (t.ex. `Ctrl+Shift+Q`),
  - kommer ihåg vald layout.

---

## 10. Beroenden och miljö

- Python 3.11/3.12 med `uv` (`pyproject.toml` + `uv.lock`).
- Kärnberoenden:
  - `PySide6`
  - `opencv-python`
  - `numpy`
  - `torch`/`torchvision` med CUDA-index
  - `ultralytics`
  - `rfdetr`
  - `Pillow`, `PyYAML`
  - `pygrabber` (Windows-enhetsnamn, valfritt)
- Utvecklingsberoenden: `pytest`, `pytest-qt`, `ruff`, eventuellt `mypy`/`pyright`.
- `uv sync` för utveckling; separat grupp/extra för CUDA.
- Dokumentera Windows-setup: NVIDIA-drivrutin, CUDA-kompatibel PyTorch, USB3-bandbredd och kamerainställningar.

### Framtida exe

- PyInstaller **one-dir** (inte one-file) eftersom torch, PySide6 och modeller är stora.
- Modeller, dataset, config och loggar ligger utanför exe-filen.
- `scripts/build_exe.ps1` med nödvändiga `collect`-regler för PySide6, Ultralytics och RF-DETR.
- Detta är en fas 8-leverans och ska inte blockera övrig utveckling.

---

## 11. Test och kvalitetssäkring

### Enhetstester

- COCO-store: lägg till/ändra/ta bort bilder, par och annoteringar.
- Versionering: ny version per sparsession, oföränderliga snapshots, korrekta räknare.
- Export: COCO- och YOLO-konvertering, split per `pair_id`, manifestinnehåll.
- Klassmappning och fritextklasser.
- BBox-geometri: resize via hörn/kant, validering, koordinatkonvertering.
- Detektor-adapter med mockad modell.

### Integrationstester

- Videofil som källa + fejkad detektor → capture → annotering → spara → ny version.
- Träningsrunner med mock/lightweight modell (eller torrkörning) för att verifiera konfiguration, logg och manifest.
- Qt-tester med `pytest-qt` för lägesväxling och capture-flöde.

### Manuell testmatris på Windows

- Två UVC-enheter i 1080p/30 fps samtidigt.
- Webkamera + videofil som testkällor.
- Långköring: minne, FPS, återanslutning vid avbrott.
- Annotering med mus: rita, flytta, ändra storlek, byta klass, ta bort, spara.
- Fullscreen/kiosk och avslutningsgenväg.
- Träning med YOLO och RF-DETR, inklusive avbrott och efterföljande modellval.

### CI

- Linux-CI för lint, typer och enhetstester utan GPU (mockade modeller).
- Valfri Windows-runner för Qt- och integrationsrök tester.

---

## 12. Genomförandefaser

| Fas | Innehåll | Leverans |
|-----|----------|----------|
| 0 | Repo/uv, `pyproject.toml`, katalogstruktur, config, logging, lint/test-uppsättning | Körbar skelettapp |
| 1 | Domänmodell, COCO-store, versionering, COCO/YOLO-export + tester | Dataset kan skapas och versionshanteras |
| 2 | Videoabstraktion, enhetsdetektering, capture-trådar, split screen-preview, fil/webkamera | Livevy med två källor |
| 3 | Detektor-interface, YOLO-adapter, inferensarbetare, overlay, capture-knapp | Fungerande detektionsläge med YOLO |
| 4 | Annoteringsvy, boxredigering, klasshantering, spara till dataset | Komplett annoteringsflöde |
| 5 | RF-DETR-adapter och modellval i UI | Två modellfamiljer stödda |
| 6 | Träningsvy, separat träningsprocess, YOLO- och RF-DETR-träning, modellversionering | Fungerande träningsläge |
| 7 | Inställningar, kiosk/fullscreen, paus vid träning, prestandamätning, autosave-draft | Driftsatt applikation |
| 8 | Paketering, Windows-dokumentation, exe-skript, härdning | Installationsbar leverans |

Rekommenderad ordning är fas 0–4 först för en komplett detektions- och annoteringsloop, därefter 5–6 för modellbredd och träning.

---

## 13. Risker och motåtgärder

| Risk | Påverkan | Motåtgärd |
|------|----------|-----------|
| RF-DETR fungerar dåligt med Windows/CUDA eller har instabilt API | Träning/inferens | Isolera i adapter, versionslås `rfdetr`, testa tidigt i fas 5, fallback till YOLO |
| Två UVC-enheter ger USB-bandbreddsproblem | Droppade frames | Konfigurerbar upplösning/fps, statusvarning, rekommendation om separata USB-kontroller |
| GPU-minne tar slut vid träning | Krasch | Separat process, förkontroll av VRAM, pausad detektion, tydliga fel |
| OpenCV-backend (DSHOW/MSMF) strular | Ingen video | Väljbar backend, enhetsdiagnostik, filkällor för test |
| Annoterings-UI blir oprecis/långsam | Dålig användarupplevelse | QGraphicsView med handtag, zoom, fit-to-window, test med mus tidigt |
| Versioner/annotationer blir inkonsekventa | Förlorad data | Oföränderliga snapshots, hash, validering före skrivning, atomiska filbyten |
| PyInstaller får problem med torch/rfdetr | Distribution | Skjut upp exe till fas 8; primärt stöd är uv-miljö |
| Träning konkurrerar med detektion | Låg FPS | Automatisk paus, schemaläggning nattetid/inaktivitet |

---

## 14. Öppna frågor att bekräfta under respektive fas

1. **UI-språk:** svenska som standard, eller engelska? Planen utgår från svenska men med centraliserade strängar.
2. **Train/val-split:** standardkvot för YOLO-export (förslag 80/20 per bildpar).
3. **YOLO26:** vilka exakta vikter/modellstorlekar ska vara standard när implementationen börjar?
4. **RF-DETR:** vilken storlek/variant ska vara standard (Base/Large) med hänsyn till GPU-minne?
5. **Flera objekt per bild:** tillåts flera boxar per bild och klass? Planen utgår från ja.
6. **Annotering i endast en av bilderna:** tillåts spara om bara ena vyn har boxar? Planen utgår från ja.
7. **Kiosk-avslut:** vilken tangentkombination ska krävas?
8. **Schemalagd träning:** räcker manuell start med automatisk paus i första versionen, eller krävs tidsstyrning direkt?

---

## 15. Definition av klar (per huvudfunktion)

- **Detektion:** två strömmar visas samtidigt, boxar/klass/sannolikhet ritas korrekt, capture skapar ett bildpar utan märkbar fördröjning.
- **Annotering:** alla detektioner är redigerbara, boxar kan skapas/flyttas/storleksändras/raderas, klass kan väljas eller skrivas in, spara skapar ny datasetversion och återgår till detektion.
- **Export:** COCO och YOLO kan exporteras med version, datum och antal bildobjekt i manifest.
- **Träning:** vald basmodell och datasetversion tränas, vikter sparas med matchande version, modellen blir valbar och detektionen pausas under träning.
- **Drift:** applikationen startar i fullscreen/kiosk, videopipelinen återhämtar sig efter avbrott och loggar prestanda.
