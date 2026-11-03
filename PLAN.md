# Implementationsplan – X-ray detector

Baserad på `specs.md` och de vägval som beslutats:

- **GUI/teknik:** Python 3.11+ med PySide6
- **Detektion/träning:** Ultralytics (YOLO) och PyTorch, med pluggbar backend för fler modeller
- **Hårdvara:** Windows 11, två UVC-kameror, NVIDIA GPU (exakt modell ej fastställd)
- **Dataset:** COCO som internt format, export till COCO och YOLO
- **Omfattning v1:** Hela flödet – detektion, annotering, export och träning
- **UI-språk:** Svenska

## 1. Övergripande arkitektur

```
┌──────────────────────────── PySide6 GUI (huvudtråd) ────────────────────────────┐
│  MainWindow                                                                      │
│   ├─ DetectionView   (split screen, overlay, fånga-knapp)                        │
│   ├─ AnnotationView  (två frysta bilder, ritverktyg, klasslista)                 │
│   ├─ TrainingView    (basmodell, dataset, parametrar, progress)                  │
│   └─ SettingsDialog  (kameror, modell, confidence, fullscreen/kiosk)             │
└───────────────▲──────────────────────▲──────────────────────▲───────────────────┘
                │ Qt-signaler          │                      │
┌───────────────┴──────────┐ ┌─────────┴──────────┐ ┌─────────┴──────────────────┐
│ CameraWorker (×2)        │ │ InferenceWorker(×2)│ │ TrainingWorker (QProcess)  │
│ OpenCV/DirectShow/MSMF   │ │ Ultralytics-backend│ │ Ultralytics train → .pt    │
│ senaste bildruta i buffer│ │ throttlad FPS      │ │ pausar detektion           │
└──────────────────────────┘ └────────────────────┘ └────────────────────────────┘
                │                      │                      │
┌───────────────▼──────────────────────▼──────────────────────▼───────────────────┐
│ Kärnmoduler: config, dataset (COCO), export, modellregister, versionshantering   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Principer:

- GUI-tråden gör aldrig kamerainläsning, inferens eller träning.
- Varje kamera har en egen capture-tråd som alltid behåller **senaste bildrutan** (ingen växande kö). Detta ger låg latens och undviker att appen "spolar fram".
- Detektion körs i separata arbetare med konfigurerbar maxfrekvens. Om inferens är långsammare än videon hoppas bildrutor över.
- All kommunikation mellan arbetare och GUI sker via Qt-signaler/slots.
- Modeller nås via ett gemensamt `DetectorBackend`-gränssnitt så att YOLO, RF-DETR och senare ONNX/TensorRT kan bytas utan att ändra GUI:t.

## 2. Föreslagen katalogstruktur

```
xray-detector/
├─ pyproject.toml
├─ README.md
├─ PLAN.md
├─ config/
│  └─ default.toml
├─ src/xray_detector/
│  ├─ __main__.py              # startpunkt
│  ├─ app.py                   # QApplication, tema, felhantering
│  ├─ config.py                # laddning/validering av inställningar
│  ├─ video/
│  │  ├─ camera.py             # en CameraWorker per UVC-enhet
│  │  ├─ frame_buffer.py       # senaste bildruta + capture-grupp
│  │  └─ device_discovery.py   # lista kameror (OpenCV + DirectShow/MSMF)
│  ├─ detection/
│  │  ├─ backend.py            # DetectorBackend-protokoll, Detection-dataclass
│  │  ├─ ultralytics_backend.py
│  │  ├─ rfdetr_backend.py     # fas 2, bakom samma gränssnitt
│  │  ├─ inference_worker.py
│  │  └─ registry.py           # tillgängliga modeller + metadata
│  ├─ dataset/
│  │  ├─ coco.py               # läs/skriv annotations.json, validering
│  │  ├─ store.py              # bilder, capture-grupper, aktiva dataset
│  │  ├─ versioning.py         # datasetversioner och metadata
│  │  └─ export.py             # COCO/YOLO-export + manifest
│  ├─ training/
│  │  ├─ trainer.py            # QProcess mot Ultralytics CLI/script
│  │  ├─ dataset_converter.py  # COCO → YOLO temporärt
│  │  └─ manifest.py           # koppling modell ↔ datasetversion
│  ├─ ui/
│  │  ├─ main_window.py
│  │  ├─ detection_view.py
│  │  ├─ annotation_view.py
│  │  ├─ annotation_scene.py   # QGraphicsScene med flyttbara/resizbara boxar
│  │  ├─ training_view.py
│  │  ├─ settings_dialog.py
│  │  └─ widgets.py
│  └─ util/
│     ├─ geometry.py
│     ├─ logging.py
│     └─ paths.py
├─ tests/
│  ├─ test_coco.py
│  ├─ test_export.py
│  ├─ test_geometry.py
│  └─ test_versioning.py
├─ data/                       # skapas vid första körning, gitignoras
│  ├─ datasets/
│  ├─ models/
│  ├─ exports/
│  └─ pending/
└─ recordings/                 # valfria testvideor, gitignoras
```

## 3. Datamodell och lagring

### Dataset (internt COCO)

```
data/datasets/<dataset_id>/
├─ images/
│  └─ <capture_group>_cam1.jpg
│  └─ <capture_group>_cam2.jpg
├─ annotations.json            # COCO: images, annotations, categories
├─ metadata.json               # version, datum, källor, antal, klasslista
└─ exports/                    # senaste exporter (valfritt)
```

- En **capture-grupp** = de två bildrutor som fångades samtidigt. Grupp-id skrivs i filnamn och i COCO-bildens `capture_group`-fält.
- Klasser lagras i COCO `categories` med stabilt `id`. Nya klasser får nästa lediga id.
- `metadata.json` innehåller minst: `dataset_id`, `version`, `created_at`, `updated_at`, `source`, `image_count`, `annotation_count`, `categories`, `schema_version`.
- **Versionering:** datasetet har en version (`v1`, `v2`, ...). Varje sparat annoteringspass höjer en revisionsräknare; en ny exporterbar version fryses när användaren väljer "Skapa version"/exporterar. Modellvikter namnges med datasetets version, t.ex. `xray-yolo-v3-<run_id>.pt`.
- Alla skrivningar görs atomiskt (temp-fil + replace) för att undvika korrupta annotationer.

### Modeller

```
data/models/<model_id>/
├─ best.pt
└─ metadata.json   # basmodell, dataset_version, datum, parametrar, metrics
```

### Export

```
data/exports/<dataset_id>-<version>-<YYYYMMDD>/
├─ images/
├─ annotations.json        # COCO-export
├─ labels/                 # YOLO-export (txt per bild)
├─ data.yaml               # YOLO-klasslista
└─ manifest.json           # version, datum, antal bilder/annotationer, klasser, hash
```

Exporten zippas valfritt. Manifestet svarar mot kravet att version, datum och antal bildobjekt framgår.

## 4. Detaljerad funktionalitet per läge

### 4.1 Detektionsläge (standard)

- Två kameraströmmar sida vid sida i en `QSplitter`/grid; varje ruta behåller bildförhållandet.
- Overlay ritar rektangel + `klass (sannolikhet)` för varje detektion.
- Konfigurerbart: kameraenheter, upplösning, FPS, confidence-tröskel, NMS/IoU, modell, device (CUDA/CPU).
- Knapp **"Fånga"**:
  1. Plockar senaste bildruta från båda kamerorna så nära samma tidpunkt som möjligt.
  2. Sparar dem i `data/pending/<capture_group>/`.
  3. Skickar med aktuella detektioner för respektive bild.
  4. Byter till annoteringsläge med dessa två bilder.
- Fullscreen/kiosk: `F11` växlar fullscreen, `Esc` lämnar, muspekaren kan döljas och enkel kiosk-inställning finns i config.
- Statusrad visar modell, enhet, FPS per ström och eventuell varning (t.ex. "detektion pausad under träning").

### 4.2 Annoteringsläge

- Två frysta bilder i samma split-layout.
- Befintliga detektioner från capture-tillfället ritas automatiskt in som boxar med klass och confidence.
- Verktyg:
  - Välj klass i lista (befintliga klasser) eller skriv ny klass.
  - Rita ny rektangel genom drag.
  - Markera box; flytta, ändra storlek via kanter/hörn (8 handtag) och ta bort (`Delete`).
  - Dubbelklicka/ändra klass på vald box.
  - Zoom/pan (hjul + mellanknapp) för precision.
- Varje bild har egen annoteringslista; capture-gruppen håller ihop paret.
- **Spara:** validerar boxar (minsta storlek, klass finns), skriver in i aktivt dataset, uppdaterar metadata, rensar pending och återgår till detektionsläge.
- **Avbryt:** frågar om osparade ändringar och återgår utan att skriva dataset.
- Klasslistan är gemensam för datasetet; nya klasser läggs till i COCO-katalogen direkt vid spara.

### 4.3 Träningsläge

- Formulär:
  - Basmodell (filväljare eller modellregister, t.ex. `yolo11n.pt`).
  - Dataset (val av `dataset_id` + version).
  - Parametrar: epochs, image size, batch, learning rate, device, workers, ev. augmentation.
- Start kräver att ingen annan träning pågår. Detektionen **pausas automatiskt** med tydlig indikator; kameraströmmar kan fortsätta visas utan inferens.
- Träning körs som separat process (`QProcess`) för att skydda GUI:t och undvika GIL-blockering. Datasetet konverteras till ett temporärt YOLO-format.
- Progress (epoch, loss, mAP om tillgängligt) läses från processens output och visas i GUI:t.
- Vid lyckat avslut:
  - `best.pt` kopieras till `data/models/<model_id>/`.
  - `metadata.json` skriver datasetversion, datum, basmodell, parametrar och metrics.
  - Modellens versionssträng matchar datasetets version.
- Vid fel: logg sparas, tydligt felmeddelande och detektionen återupptas.
- Möjlighet att stoppa träningen.
- Schemaläggning/nattkörning är inte v1-krav; träning startas manuellt men kan köras under inaktivitet.

## 5. Modellabstraktion

```python
class DetectorBackend(Protocol):
    def load(self, model_path: str, device: str) -> None: ...
    def detect(self, frame, conf: float, classes: list[int] | None) -> list[Detection]: ...
    def class_names(self) -> dict[int, str]: ...
```

- `Detection`: `xyxy`, `class_id`, `class_name`, `confidence`.
- `UltralyticsDetectorBackend` implementeras i v1.
- `rfdetr_backend.py` förbereds men kan ligga efter v1; GUI:t ska inte behöva ändras när den aktiveras.
- Modellregister (`registry.py`) beskriver tillgängliga modeller, filnamn och vilken backend de använder.
- Device väljs automatiskt: CUDA om tillgängligt, annars CPU, med manuell override.

## 6. Trådning och prestanda

- En `CameraWorker` per kamera (egen `QThread`), OpenCV VideoCapture med DirectShow eller MSMF som konfigurerbart backendläge.
- Bildrutor levereras som `QImage`/numpy med minimal kopiering; senaste-ruta-buffer används av GUI och inferens.
- En `InferenceWorker` per ström i v1. Modellinstanser hålls separata för att undvika trådproblem i Ultralytics; delad modell kan införas senare om GPU-minnet är begränsande.
- Inferens throttle: `detection_fps` konfigurerbart (t.ex. 5–15 fps), oberoende av visnings-FPS.
- Halvprecision (`half=True`) på CUDA när modellen stödjer det.
- Vid träning stoppas inferensarbetarna; capture-trådar kan leva vidare för preview.
- Långa operationer (dataset-scan, export) körs i arbetstråd med progressdialog.
- Målvärden: UI ska förbli responsivt (<100 ms) och preview ska flyta; faktisk detektionsfps beror på GPU/modell och loggas.

## 7. Konfiguration

`config/default.toml` med användaroverride i `%APPDATA%/xray-detector/config.toml`:

```toml
[app]
language = "sv"
fullscreen = false
kiosk = false
data_dir = "data"

[video]
backend = "dshow"          # dshow | msmf
width = 1920
height = 1080
fps = 30
camera_left = 0
camera_right = 1
preview_fps = 30

[detection]
model = "yolo11n.pt"
device = "auto"
confidence = 0.25
iou = 0.45
detection_fps = 10
class_filter = []

[training]
default_base_model = "yolo11n.pt"
epochs = 100
imgsz = 640
batch = 8
workers = 4
```

Hemligheter och maskinspecifika sökvägar ska inte checkas in.

## 8. Implementationsfaser

### Fas 0 – Projektgrund
- `pyproject.toml` med beroenden: PySide6, opencv-python, ultralytics, numpy, tomli/tomllib, pytest, pyinstaller.
- Startpunkt, loggning, config-laddning, katalogskapande, felhantering.
- Grundläggande `MainWindow` med lägesväxling och meny/knappar.
- **Klart när:** appen startar, skapar datakataloger och visar tomt skal.

### Fas 1 – Video och detektionsvy
- Kameraenumerering och två `CameraWorker`.
- Split screen med korrekt skalning, FPS-status, fullscreen/kiosk.
- Robust hantering av kamera frånkopplad/upptagen.
- **Klart när:** två USB-kameror visas samtidigt i Windows utan att GUI hackar.

### Fas 2 – Detektion
- `DetectorBackend` + Ultralytics-implementation.
- Inferensarbetare, overlay med box/klass/sannolikhet, confidence-inställning.
- Modellval och device-val i inställningar.
- **Klart när:** en vald YOLO-modell detekterar i båda strömmarna och resultatet ritas korrekt.

### Fas 3 – Fångst och annotering
- Fånga-knapp som fryser båda bildrutorna och skickar med detektioner.
- COCO-lagring, pending-grupper, klasshantering.
- Annotationsscen med rita, markera, flytta, storleksändra och klassbyte.
- Spara/avbryt med validering och återgång till detektionsläge.
- **Klart när:** ett capture-par kan annoteras med nya och befintliga boxar och sparas i datasetet.

### Fas 4 – Dataset, versionering och export
- Metadata, versioner och revisionshantering.
- COCO-export, YOLO-export, `data.yaml`, manifest med version/datum/antal.
- Enkel datasetöversikt (antal bilder, annotationer, klasser, version).
- **Klart när:** exporterat dataset kan öppnas av Ultralytics och innehåller korrekt manifest.

### Fas 5 – Träning
- Träningsformulär, validering, COCO→YOLO-konvertering.
- `QProcess`-baserad träning, progress, stopp och felloggning.
- Automatisk paus av detektion, återupptagning efter avslut.
- Modellsparning med datasetversion i metadata och namn.
- **Klart när:** en träning kan startas från GUI, pausar detektionen och producerar vikter kopplade till rätt datasetversion.

### Fas 6 – Hårdning och leverans
- Enhetstester för COCO, export, geometri och versionering.
- Integrationstest med inspelade videor/bilder (utan fysisk kamera).
- Prestandamätning på målhårdvara, justering av buffrar och trådar.
- PyInstaller-paketering för Windows, startskript och användardokumentation.
- Loggrotation och tydliga feltexter på svenska.
- **Klart när:** installationsbar Windows-build kör hela flödet på målmaskinen.

### Fas 7 – Utökning (efter v1)
- RF-DETR-backend.
- Fler exportformat (t.ex. Pascal VOC) vid behov.
- Schemalagd träning nattetid och resursstyrning.
- Modelljämförelse och metricsöversikt i GUI.

## 9. Teststrategi

- **Enhetstester:** COCO-läs/skriv, klass-id-konsistens, boxgeometri (resize/handtag), versionering, exportmanifest, COCO→YOLO-konvertering.
- **Integrationstester:** capture-par → annotering → spara → export → konvertering, med temporära kataloger och testbilder.
- **Manuella tester på Windows:** två UVC-kameror samtidigt, frånkoppling, fullscreen, lång körtid, träning som pausar detektion.
- **Prestandatest:** mät preview-FPS, inferenslatens och GPU-minne med vald modell.

## 10. Risker och motåtgärder

| Risk | Åtgärd |
|---|---|
| Två UVC-kameror på samma USB-kontroller ger bandbreddsproblem | Konfigurerbar upplösning/FPS, MJPG där det stöds, tydlig feltext, möjlighet att använda olika backend (DShow/MSMF) |
| Ultralytics-modeller är inte trådsäkra | Separata modellinstanser per ström i v1; utvärdera delning senare |
| GPU-minne tar slut med två modeller | Konfigurerbar modellstorlek, halvprecision, möjlighet att köra en gemensam modell med lås |
| PyInstaller + PyTorch + PySide6 blir stor/complex build | Tidig paketeringstest i fas 6, dokumenterad build-miljö |
| Licensvillkor för YOLO/Ultralytics och RF-DETR | Utred innan kommersiell distribution; håll backend pluggbar |
| Klass-id divergerar mellan dataset och tränad modell | Klasslistan ägs av datasetet; modellmetadata sparar exakt klassmappning |
| Dataset-version och modellversion hamnar ur synk | Versionssträng skrivs i både datasetmetadata och modellmanifest; validering vid träning |
| Kamerabilder och detektioner hinner inte vara synkade vid fångst | Capture-grupp med tidsstämpel; tolerans dokumenteras och visas vid behov |
| Osparade annotationer förloras | Dirty-flagga, bekräftelsedialog och atomisk sparning |

## 11. Acceptanskriterier för v1

1. Applikationen startar på Windows 11 och visar två kameraströmmar i split screen med overlay för klass och sannolikhet.
2. Fånga-knappen fryser båda strömmarna, öppnar annoteringsläget och visar befintliga detektioner automatiskt.
3. Boxar kan skapas, flyttas, storleksändras via kant/hörn och tilldelas befintlig eller ny klass.
4. Spara lägger till capture-paret i aktivt dataset och återgår till detektionsläget.
5. Dataset kan exporteras till COCO och YOLO med versionsnummer, datum och antal bildobjekt i manifest.
6. Träning kan startas manuellt med vald basmodell, dataset och parametrar; detektionen pausas under träningen.
7. Efter träning finns modellvikter med metadata som kopplar dem till använd datasetversion.
8. Fullscreen/kioskläge fungerar och GUI förblir responsivt under video, inferens och träning.

## 12. Kvarstående frågor att besluta senare

- Exakt NVIDIA-modell och GPU-minne (påverkar standardmodell, batchstorlek och om två modellinstanser får plats).
- Kamerornas upplösning, FPS och om MJPG krävs för två samtidiga strömmar.
- Ska detektionens klasser alltid vara identiska med datasetets klasser, eller behövs separat klassmappning?
- Ska varje sparat annoteringspass automatiskt skapa en ny datasetversion, eller räknas versionen först vid export? Planen antar senare.
- Behövs RF-DETR redan i v1 eller räcker det med förberedd backend och YOLO i första leveransen?
- Ska applikationen kunna spela in video, eller bara enskilda bildrutor?
- Önskas schemalagd träning nattetid redan i v1?
