# Utvärdering av X-ray Detector (`utvärdering_argon.md`)

**Datum:** 2026-11-17  
**Omfattning:** Helhetsutvärdering av kodbas (`xray_detector/`), tester (`tests/`), arkitektur, ramverksval, GUI/UX samt dokumentation och verktyg (`README.md`, `specs.md`, `groma/`, `backlog/`).

---

## 1. Sammanfattande helhetsbedömning

**X-ray Detector** är en välfungerande och genomtänkt skrivbordsapplikation med många goda tekniska kvaliteter:
- **Tydlig grundarkitektur:** Koden är sedan TASK-22 uppdelad i fyra lager (`domain`, `application`, `infrastructure`, `ui`) med korta, fokuserade moduler och konsekvent namngivning.
- **God responsivitet och driftsäkerhet:** Träning körs i en separat OS-process via `QProcess` (vilket frigör VRAM/CUDA-kontext efter avslut), tidskrävande GUI-operationer är utflyttade till `BackgroundTask` med en fördröjd `BusyIndicator` (150 ms), JSON-skrivningar sker atomärt via tempfil + `os.replace`, och bildfångster säkras direkt på disk i en `pending/`-kö.
- **Omfattande testsvit:** 72 testfiler som kan köras utan fysiska kameror eller GPU tack vare `FakeDetector` och syntetiska videoströmmar.
- **Domänanpassade val:** Stratifierad train/val/test-delning per fångstgrupp (så att vyer och syntetiska variationer från samma fångstögonblick aldrig läcker mellan splits), domänanpassade hyperparametrar för röntgenbilder, samt en utvärderingsmodul i ren NumPy som mäter mAP per vy och falsklarm vid 95 % recall.

Samtidigt märks det att projektet har vuxit fram inkrementellt genom ~120 separata tasks med olika AI-agenter. Det har lämnat efter sig **parallella implementationer av samma logik**, **gränsöverskridelser mellan arkitekturlagren**, **onödiga prestandaflaskhalsar vid växande dataset**, **viss död/migrerande kod**, samt **dokumentation och arkitekturfiler (Groma) som delvis har glidit isär från koden**.

Nedan följer en detaljerad genomgång per område samt en prioriterad åtgärdsplan.

---

## 2. Död kod, kvarlevor och föråldrade konstruktioner

### 2.1 Oanvända funktioner i produktionskoden
| Funktion / Fält | Plats | Problem & Förslag |
| :--- | :--- | :--- |
| `load_config()` | `xray_detector/domain/config.py:55-58` | Anropas aldrig i produktionskoden (ersatt av `load_config_with_yaml()` i `application/app_config.py:103`). Har dessutom sidoeffekten `ensure_dirs()` mitt i domänlagret. **Ta bort.** |
| `_parse_scalar()` | `xray_detector/application/app_config.py:45-56` | Helt oanvänd hjälpfunktion (anropas varken i `app_config.py` eller i testerna). **Ta bort.** |
| `spec_by_key()` | `xray_detector/application/model_registry.py:224-228` | Slår enbart upp mot den hårdkodade listan `MODEL_SPECS` (ignorerar både `models.json` och `models/trained/`). Används inte längre i produktionskoden, bara i ett äldre test (`tests/test_detector_settings.py`). **Ta bort.** |
| `device_is_available()` | `xray_detector/infrastructure/video/devices.py:78-85` | Används aldrig i produktionskoden (endast i `tests/test_devices.py`). **Ta bort eller flytta till test/diagnostik.** |
| `AppConfig.classes` | `xray_detector/domain/config.py:21-23`, `application/app_config.py:86-87, 125` | Kvarleva från innan TASK-52 och TASK-61. Idag kommer detektionens klasser från modellvikterna och annoteringens/datasetets klasser från `datasets/data.yaml`. `config.classes` (`["cigaretter", "cannabis", "kniv", "pistol"]`) läses inte längre av någon vy eller tjänst i applikationen, men parsas fortfarande från `config.yaml`, loggas vid uppstart och beskrivs i `README.md`. **Ta bort fältet helt** för att undvika förvirring kring vad som är master för klasslistan. |

### 2.2 Prototyper och skräpfiler i repot
- **`tests/prototype/annotation_scene.py` och `tests/prototype/test_prototype_annotation_scene.py`:** Utvärderingsspiken från TASK-21 ligger kvar inuti `tests/`. Den körs vid varje `pytest`-körning trots att den inte testar produktionskod, muterar `sys.path.insert(0, ...)` globalt på rad 12 och definierar en klass `AnnotationView` som delar namn med produktionsklassen. Antingen bör portningen till `QGraphicsScene` genomföras på riktigt (se avsnitt 6.1) eller så bör prototypen tas bort / flyttas ut ur `tests/`.
- **Saknad beslutsfil från TASK-21:** `backlog/tasks/task-21 - ...md` anger i `modified_files` och i sin slutrapport att rekommendationen sparades i `docs/decision-annotation-canvas.md`, men katalogen `docs/` finns inte i repot.
- **Incheckade körningsartefakter i `runs/`:** Katalogen `runs/detect/runs/probe/` (`args.yaml` och `results.csv`) ligger i versionshanteringen med en hårdkodad absolut sökväg (`save_dir: C:\Users\Ai1\repo\xray-detector\runs\detect\runs\probe` i `args.yaml:115`). Ta bort `runs/` ur git och lägg till `runs/` samt `exports/` i `.gitignore`.

### 2.3 Automatiska engångsmigreringar vid varje uppstart
Koden innehåller flera migreringsfunktioner för format som byttes ut under tidig utveckling:
1. `_migrate_versions()` i `infrastructure/dataset_store/store.py:35-58` (flyttar upp `datasets/v1..vN` till `datasets/`, TASK-57).
2. `_migrate_coco()` i `infrastructure/dataset_store/store.py:61-106` (konverterar gammal COCO-`dataset.json` till YOLO-filer, TASK-78).
3. `_warn_about_legacy_models()` i `app.py:48-60` (varnar om `~/.xray-detector/models/`, TASK-50).
4. Bakåtkompatibilitet för manifest före TASK-48/TASK-108 i `application/model_registry.py:264-270` och viktfilsnamn i `ui/training_view.py:317-318`.

`_migrate_versions()` och `_migrate_coco()` körs i `DatasetStore.__init__()` varje gång en `DatasetStore` skapas. Om inga gamla installationer med `v1/`-mappar eller COCO-internt format längre behöver stödjas i fält bör dessa ~85 rader migreringskod (och tillhörande migreringstester) städas bort.

---

## 3. Duplicering och parallella implementationer

Detta är det område där kodbasen kan förenklas allra mest.

### 3.1 Tre handskrivna YAML-tolkare istället för `PyYAML`
Projektet undviker att importera `yaml` och har istället **tre separata, handskrivna YAML-tolkare** (samt en handskriven YAML-skrivare):
1. **`application/app_config.py:59-100` (`apply_yaml_overrides`)**: Parsar `config.yaml` rad för rad med `line.partition(":")`. Klarar bara listor på en rad (`classes: [a, b]`) och misslyckas tyst om en användare skriver standard-YAML med `- item` på egna rader eller har kommentarer i slutet av en rad (`confidence_threshold: 0.5 # kommentar`).
2. **`infrastructure/dataset_store/yolo.py:19-63` (`read_classes`, `_parse_names`, `_parse_indented_names`)**: Parsar `data.yaml` med `ast.literal_eval` och egen indenteringsparsning.
3. **`infrastructure/training/train_task.py:69-90` (`_read_data_classes`)**: Duplicerar parsningen av `data.yaml` med `ast.literal_eval`, men **saknar** stöd för flerradig dict-form (`_parse_indented_names`) som `yolo.py` hanterar!

**Förslag:** `PyYAML` finns *redan* i `uv.lock` som ett obligatoriskt beroende via `ultralytics`. Lägg till `pyyaml` explicit i `pyproject.toml`, använd `yaml.safe_load` / `yaml.safe_dump` i `app_config.py` och `yolo.py`, och låt `train_task.py` anropa `read_classes()` från `yolo.py`. Det ersätter ~100 rader skör strängparsning med ~15 rader standardkod.

### 3.2 Fyra parallella implementationer av fångstgrupper (bildpar)
Begreppet "fångstgrupp" (ett bildpar från vänster/höger kamera samt dess syntetiska variationer) är ett av projektets viktigaste domänbegrepp, men logiken `image.get("group") or image["id"]` och gruppering/par-räkning är duplicerad på **fyra** ställen med små variationer:
- `infrastructure/dataset_store/export.py:16-48, 213-219` (`_group_key`, `_root_image`, `_groups`, `group_count`)
- `infrastructure/dataset_store/store.py:30-32, 355-357, 433-444` (`_pair_count`, gruppering i `add_variations`, `dataset_counts`)
- `application/evaluation.py:68-82` (`view_labels`)
- `ui/dataset_view.py:650-667, 692-695` (`_original_pairs`, `_synthetic_pairs`, `_pair_count`, samt gruppering i `_build`)

Notera särskilt att `DatasetView._original_pairs()` och `_synthetic_pairs()` (`dataset_view.py:650-667`) räknar exakt samma sak som `DatasetStore.dataset_counts()` (`store.py:433-444`)!

**Förslag:** Lyft in bildpars-/fångstgrupp-logiken i en gemensam domänmodell (t.ex. `CaptureGroup` / hjälpfunktioner i `domain/dataset.py`) och återanvänd `dataset_counts()` i `DatasetView`.

### 3.3 Dubbel inläsning och parsning av `training_manifest.json`
- `application/model_registry.py:244-279` (`trained_models`) och `application/training_history.py:116-158` (`training_runs` / `_read_run`) gör båda `trained_dir.rglob("training_manifest.json")`, öppnar JSON-filen, bygger sökvägen `weights_relative`, kontrollerar att viktfilen existerar, räknar ut `run_id` via `relative_to(trained_dir).as_posix()` och läser ut `family`, `base_weights` och `classes`.
- **Förslag:** Låt `training_history.py` (eller en gemensam manifest-modul) vara den enda som läser `training_manifest.json`, och låt `trained_models()` bygga `ModelSpec` direkt från `TrainingRun` (om ` TrainingRun` utökas med `name` och `base_model_name`).

### 3.4 Dubbel borttagningslogik för egentränade modeller (med en bugg!)
Både `ui/model_settings.py:235-265` (`ModelSection._on_remove`) och `ui/training_history.py:295-311` (`TrainingHistoryView._on_delete`) frågar användaren och anropar `delete_run(self.trained_dir, run_id)`.
- **Buggrisk:** `TrainingHistoryView` kontrollerar via `_delete_enabled()` (`training_history.py:175-180`) att man inte raderar en träningskörning som pågår just nu (`active_run_dir`). `ModelSection` i fliken *Inställningar* saknar denna kontroll! Om en träning redan har hunnit skriva sitt manifest efter epok 1 kan användaren gå till fliken *Inställningar -> Modeller* och ta bort den pågående träningens katalog medan träningsprocessen skriver i den.
- **Förslag:** Samla borttagningskontrollen och bekräftelsedialogen på ett ställe.

### 3.5 Ytterligare dupliceringar att slå ihop
1. **Två funktioner för CUDA-enhetsstatus:**
   - `device_status()` i `application/model_registry.py:303-312` returnerar `("Enhet: CUDA (...)", "#2a8")` eller `("Enhet: CPU (CUDA ej tillgänglig)", "#c33")`.
   - `cuda_device_label()` i `infrastructure/detectors/base.py:23-33` gör exakt samma `torch.cuda.is_available()` och `torch.cuda.get_device_name(0)`-uppslag och returnerar `"CUDA (...)"` eller `"CPU (CUDA ej tillgänglig)"`.
   - När `DetectionView._on_model_loaded()` (`detection_view.py:852-854`) skriver över `self.device_label` med detektorns `device_label` tappas dessutom färgkodningen om enheten ändrats (t.ex. fallback till CPU). Ha *en* funktion på ett ställe.
2. **Två identiska metoder för att stänga av RF-DETR i QComboBox:**
   - `DetectionView._disable_unavailable_models()` (`ui/detection_view.py:642-654`) och `TrainingView._disable_missing_rfdetr()` (`ui/training_view.py:142-156`) innehåller samma `importlib.util.find_spec("rfdetr")`-kontroll och loop över `QComboBox.model()`. Bryt ut till en gemensam hjälpfunktion (t.ex. `populate_model_combo()`).
3. **Tre varianter av BGR-`np.ndarray` till `QImage`:**
   - `AnnotationCanvas.load_frame` (`ui/annotation_view.py:80-85`): `np.ascontiguousarray(frame[:, :, ::-1])` + `.copy()`
   - `DatasetView._add_pending_section` (`ui/dataset_view.py:962-964`): `frame[:, :, ::-1].copy()` + `.copy()`
   - `StreamPanel._to_qimage` (`ui/detection_view.py:479-484`): `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)` *utan* `.copy()` på `QImage` (vilket är farligt i PySide6 om `rgb`-arrayen frigörs medan `QImage` lever kvar!).
   - **Förslag:** Skapa en gemensam `bgr_to_qimage(frame: np.ndarray) -> QImage` som alltid gör `cv2.cvtColor` och returnerar en ägd kopia (`.copy()`).
4. **Två IoU-beräkningar:**
   - `infrastructure/detectors/smoothing.py:111-122` (`_iou`) och `infrastructure/training/metrics.py:52-69` (`iou_matrix`).
5. **Duplicerat kortbyggande i `DatasetView`:**
   - `_add_capture_card` (`ui/dataset_view.py:864-912`) och `_add_pending_section` (`ui/dataset_view.py:937-981`) bygger nästintill identiska `CaptureCard`-widgets med rubrik, klassmärken och `Thumbnail`-rader.

---

## 4. Arkitektur, lagerindelning och datamodeller

### 4.1 Gränsöverskridelser i den lagerindelade arkitekturen
Projektet är indelat i `domain`, `application`, `infrastructure` och `ui`, men beroenderiktningen bryts på flera ställen:
1. **`ui` importerar direkt från `infrastructure`:**
   - `ui/detection_view.py:27-29` importerar `BaseDetector`, `ResourceMonitor`, `ResourceUsage` och `list_device_modes` direkt från `infrastructure.*`. Notera att `VideoService` i `application/video_service.py` redan är tänkt som fasad för video, men exponerar bara `list_devices()` och har glömt `list_device_modes()`.
   - `ui/dataset_view.py:27` och `ui/variation_dialog.py:24` importerar `describe`, `MIN_SCALE` och `MAX_SCALE` direkt från `infrastructure.dataset_store.augment`. `MIN_SCALE` och `MAX_SCALE` är domänkonstanter som hör hemma i `domain/dataset.py` bredvid `VariationSettings`.
2. **`application` är hårt kopplat till PySide6 (`QtCore`), medan Qt-workers ligger i `infrastructure`:**
   - `application/background_task.py` och `application/training_service.py` är byggda på `QObject`, `Signal`, `QTimer` och `QThreadPool`.
   - Samtidigt ligger `TrainingWorker(QObject)` i `infrastructure/training/trainer.py` och `StreamWorker(QThread)` i `infrastructure/video/camera_service.py`.
3. **Tunna "pass-through"-fasader utan egen logik:**
   - `DatasetService` (`application/dataset_service.py`, 150 rader) har 22 metoder varav 19 är rena enradsdelegeringar till `DatasetStore`, `export.py` eller `pending.py`.
   - `VideoService` (`application/video_service.py`, 42 rader) delegerar nästan 1-till-1 till `CameraService`.
   - **Förslag:** Antingen låter man `DatasetService` och `VideoService` faktiskt kapsla in hela sitt underliggande `infrastructure`-paket (så `ui` aldrig importerar `infrastructure`), eller så slår man ihop de tunna mellanhänderna så man slipper redigera både `store.py` och `dataset_service.py` vid varje ny funktion.

### 4.2 Otypad `dict`-baserad läsmodell och tre olika bbox-format
I `DatasetStore.load_dataset()` (`store.py:482-507`) returneras hela datasetet som en otypad `dict` med nästlade listor av `dict`:ar (`image["annotations"] = [{"class_name": ..., "bbox": [x, y, w, h]}]`). Detta skapar friktion i hela kodbasen:
- Tre olika koordinatformat används för rektanglar:
  1. `Detection` (`domain/detection.py`): `x1, y1, x2, y2` i pixlar.
  2. Annoteringar i `dict` (`store.py`, `augment.py`, `export.py`, `evaluation.py`): `[x, y, w, h]` i pixlar.
  3. YOLO-rader (`yolo.py`): `(class_idx, cx, cy, w, h)` normaliserat 0–1.
- I `DatasetView._on_thumb_double_clicked` (`ui/dataset_view.py:1072-1082`) måste vyn manuellt packa om sparade annoterings-`dict`:ar till falska `Detection(..., confidence=1.0)`-objekt inuti ett `StreamFrame`-objekt bara för att `AnnotationView.load_captures()` tar emot `StreamFrame`!

**Förslag:** Inför tydliga domändataklasser i `domain/dataset.py`, t.ex. `BoundingBox` (med properties för både `xywh`, `xyxy` och `yolo`), `DatasetImage` och `Dataset`, så att kompilator/IDE/typkontroll kan fånga fel och vyerna slipper konvertera mellan `dict` och `Detection`.

### 4.3 Splittrad konfigurations- och katalogstruktur (`PROJECT_ROOT` vs `~/.xray-detector`)
Applikationen sprider idag sin data och sina inställningar över två helt skilda platser och tre filformat:
- **`~/.xray-detector/`:** `datasets/`, `pending/`, `exports/` och `settings.ini` (`QSettings`).
- **`PROJECT_ROOT` (`Path(__file__).resolve().parents[2]`):** `models/`, `models/models.json`, `models/trained/` och `logs/`.
- **Arbetskatalog eller `config_dir`:** `config.yaml`.

**Risk vid distribution:** `PROJECT_ROOT = Path(__file__).resolve().parents[2]` i `domain/config.py:7` förutsätter att applikationen alltid körs direkt ur en klonad git-katalog. Om paketet installeras med `pip`/`uv` i en miljö eller paketeras med PyInstaller kommer `parents[2]` att peka in i `.venv/Lib/site-packages/` eller en skrivskyddad programmapp.
- **Förslag:** Samla alla`QSettings`-nycklar i en central typad klass (`AppSettings` runt `QSettings`) istället för råa strängliteraler utspridda i 8 UI-filer, och låt standardkatalogerna falla tillbaka på en skrivbar användarkatalog om `PROJECT_ROOT` inte är en git-/arbetskatalog.

---

## 5. Prestanda, trådsäkerhet och resursanvändning

### 5.1 Kritisk minnes- och I/O-flaskhals i `DatasetView._load()`
I `ui/dataset_view.py:498-511` görs följande vid **varje** `refresh()`:
```python
decoded = {
    image["id"]: QImage(str(images_dir / image["file_name"]))
    for image in dataset["images"]
}
return {"dataset": dataset, "images": decoded, "pending": pending}
```
Och därefter i `_build()` på GUI-tråden (`dataset_view.py:289-291, 904`):
```python
pixmap = QPixmap.fromImage(image).scaledToHeight(
    THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation
)
```
**Problem:**
1. Arbetstråden läser in **varenda bild i datasetet i full upplösning (t.ex. 1920×1080)** till okomprimerade `QImage`-objekt i RAM samtidigt, och skickar hela denna dict (`self._data`) till GUI-tråden där den dessutom sparas kvar i minnet (`self._data = data` på rad 671) för att kunna filtrera!
2. En enda 1920×1080-bild i `QImage` tar ~6–8 MB RAM. Med 100 ursprungliga bildpar (200 bilder) + 4 syntetiska variationer per par (= 1 000 bilder) håller `self._data["images"]` **6–8 GB RAM** i okomprimerade fullstorleksbilder, bara för att visa 170 px höga tumnaglar!
3. Dessutom läses alla bilder om från disk varje gång en annotering sparas, ett bildpar tas bort eller sorteringsordningen ändras.

**Förslag:**
- Skala ner `QImage` till `THUMB_HEIGHT` (170 px) och rita in annoteringsrutorna **redan i arbetstråden** (`QImage` och `QPainter` på `QImage` är helt trådsäkra i Qt – endast `QPixmap` måste skapas i GUI-tråden!). En 170 px hög `QImage` tar ~150 kB istället för 8 MB (ca **50× mindre RAM**).
- Ännu bättre: cacha de nedskalade tumnaglarna i minnet (indexerat på `(image_id, mtime, annotations)`) eller på disk under `datasets/.thumbs/`, så att `refresh()` efter en sparad annotering bara behöver avkoda de 2 nya bilderna istället för alla 1 000.

### 5.2 Trådsäkerhetsrisk: Två `StreamWorker`-trådar delar samma `BaseDetector`-instans
I `ui/detection_view.py:774` och `infrastructure/video/camera_service.py:125-127` skickas **samma** `BaseDetector`-instans (`self.detector`) till både vänster och höger `StreamWorker` (`QThread`). Båda trådarna anropar `detector.detect(frame)` parallellt utan synkronisering (`camera_service.py:90`).
- **Problem:** Ultralytics `YOLO.predict()` är **inte trådsäkert** när det anropas samtidigt på samma `YOLO`-instans från två trådar (den muterar `self.predictor` och dess interna state under inferens). Även `detector.enabled_classes` och `detector.confidence_threshold` muteras från GUI-tråden medan kameratrådarna läser dem.
- **Förslag:** Lägg ett `threading.Lock()` i `BaseDetector` (eller i `YoloDetector`/`RfDetrDetector`) runt `detect()`-anropet. Eftersom GPU-inferensen ändå serialiseras på CUDA-strömmen tappar man ingen genomströmning på GPU, men slipper race conditions och sporadiska krascher i Ultralytics predictor.

### 5.3 Blockerande I/O på GUI-tråden vid träningsstart och i `DatasetView`
Trots det fina arbetet i TASK-40 med `BackgroundTask` finns tre tunga synkrona I/O-operationer kvar på GUI-tråden:
1. **Export vid träningsstart (`ui/training_view.py:407-412`):** När användaren klickar *Starta träning* (eller *Schemalägg träning*!) körs `export_rfdetr()` eller `export_yolo()` **synkront i GUI-tråden**, vilket raderar `exports/` och kopierar samtliga bildfiler i datasetet med `shutil.copy2` innan `TrainingWorker` startar.
   - *Sidoproblem 1:* Om man väljer *Schemalägg träning* exporteras datasetet vid klickögonblicket istället för när det schemalagda jobbet faktiskt startar (så bilder som annoteras under dagen före nattkörningen kommer inte med!).
   - *Sidoproblem 2:* För YOLO behöver bilder inte ens kopieras vid träning! Ultralytics stödjer att `train:` och `val:` i `data.yaml` pekar på textfiler (`train.txt`, `val.txt`) med sökvägar till bilderna i `datasets/images/`. Då tar YOLO-exporten för träning < 5 ms och noll extra diskutrymme.
2. **Öppning av sparat bildpar (`ui/dataset_view.py:1068`):** `_on_thumb_double_clicked` kör `cv2.imread` synkront i GUI-tråden.
3. **Uppräkning av UVC-lägen (`ui/detection_view.py:272`):** `_populate_modes` anropar `list_device_modes(device_index)` synkront i GUI-tråden, vilket bygger en DirectShow `FilterGraph` och öppnar kameradrivrutinen (kan ta 200–1 000 ms).

### 5.4 Onödig omskrivning av PNG-filer vid redigering av annoteringar
När ett redan sparat bildpar öppnas från `DatasetView` till `AnnotationView` och sparas:
1. `AnnotationCanvas.load_frame()` konverterar `np.ndarray` (BGR) $\rightarrow$ `QImage` (RGB).
2. `AnnotationCanvas.result()` (`ui/annotation_view.py:99-108`) packar upp `QImage`-bufferten tillbaka till `np.ndarray` (BGR).
3. `DatasetStore.replace_samples()` (`infrastructure/dataset_store/store.py:315`) skriver alltid om PNG-filerna på disk med `cv2.imwrite()`, även fast användaren bara kan redigera *rektanglar och klasser* i `AnnotationView` (aldrig själva bildpixlarna!).
- **Förslag:** Behåll original-`frame` på `AnnotationCanvas` och låt `replace_samples()` (eller en `update_annotations(image_ids, annotations)`) enbart skriva om `.txt`-labelfilerna i `labels/` och `dataset.json`. Det gör sparning vid redigering ~50× snabbare och undviker onödig disk-I/O.

### 5.5 Träningsvyns basmodellväljare kan inte välja egentränade modeller
`README.md:57` och `README.md:132` samt `TrainConfig.base_name` (TASK-108) är byggda för att man ska kunna vidareträna en egen tränad modell (t.ex. en RF-DETR-snapshot `.pth` eller YOLO `.pt`). Men i `ui/training_view.py:127, 133` anropar `TrainingView.refresh_models()` `base_models(self.config.models_dir)` istället för `available_models(self.config.models_dir, self.config.trained_dir)`!
- **Konsekvens:** Egentränade modeller under `models/trained/` dyker upp i detektionsvyn och i inställningsfliken, men **aldrig** i träningsvyns basmodellväljare.
- **Förslag:** Använd `available_models(self.config.models_dir, self.config.trained_dir)` även i `TrainingView.refresh_models()`.

### 5.6 Mindre buggar i livscykel och felhantering
- **Saknade inväntningar i `MainWindow.closeEvent` (`ui/main_window.py:271-275`):** `closeEvent` väntar in arbetstrådarna i `annotation_view`, `dataset_view` och `detection_view`, men glömmer `self.training_view.history.wait_for_evaluation()` och `self.settings_view.model_section.wait_for_download()`.
- **Dubbel dialog vid stängning med osparade tomma annoteringar (`ui/main_window.py:254-255`):** Om användaren stänger appen med osparade ändringar på en tom bild och klickar *Spara* i `"Det finns osparade annoteringar. Spara dem?"`, anropas `self.annotation_view._on_save()` som i sin tur öppnar ännu en frågedialog (`"Inga objekt är markerade. Spara bilderna som negativa exempel?"`). Om användaren klickar *Nej* där avbryts sparningen men fönstret stängs ändå och ändringarna går förlorade.
- **Oändlig `source_lost`-signalering i `StreamWorker` (`infrastructure/video/camera_service.py:66-73`):** När `self.source.read()` returnerar `None` emittar `StreamWorker` `source_lost` var 500:e ms utan att stanna tråden. Efter `MAX_AUTO_RETRIES` (2 försök) fortsätter den gamla tråden att anropa `read()` och emitta `source_lost` två gånger i sekunden (vilket ritar om `lost_label` med ökande försöksnummer `3, 4, 5...`) tills användaren byter källa. `StreamWorker.run()` bör avsluta loopen (`break`) när `read()` ger `None`, eftersom `StreamPanel._on_retry()` ändå skapar en ny `StreamWorker` vid återanslutning.

---

## 6. Val av ramverk, beroenden och deprecations

### 6.1 GUI och grafer: `PySide6` och `PySide6.QtCharts`
- **PySide6 (Qt 6):** Ett utmärkt val för den här typen av applikation på Windows – mogen hantering av trådar, bildrendering, tangentbordsgenvägar och inbyggd svensk översättning (`qtbase_sv.qm`).
- **Deprecation-varning kring `QtCharts` (`ui/training_chart.py`):** Qt har fasat ut `QtCharts` till förmån för `QtGraphs` i nyare Qt 6-versioner (deprecated i Qt 6.8, borttaget i Qt 6.10). Utöver detta drar `PySide6.QtCharts` in en stor modul för att rita två mycket enkla linjediagram (`Loss` och `mAP`), och `QChart` i `training_chart.py` följer **inte** appens tema (graferna har alltid vit bakgrund och mörk text även när appen körs i mörkt tema).
  - **Förslag:** Ersätt `QChart`/`QChartView` i `training_chart.py` med en enkel egen `QWidget` som ritar axlar och polylinjer med `QPainter` (~100 rader kod, precis som `BusyIndicator` och `AnnotationCanvas` redan gör) och använder `self.palette()` så den automatiskt matchar både ljust och mörkt tema utan beroende av `QtCharts`.
- **`AnnotationCanvas` vs `QGraphicsView`:** `AnnotationCanvas` i `ui/annotation_view.py` är ~400 rader manuell koordinattransformation (`_to_widget`, `_to_image`, `_base_origin`, `_image_origin`) och skalar om hela `QImage` på CPU i varje `paintEvent` (`painter.drawImage(QRect(origin, size), self.image)`). Vid hög zoom och stora röntgenbilder blir detta märkbart tyngre än `QGraphicsView` + `QGraphicsPixmapItem`. Om fler funktioner (t.ex. polygoner, mätverktyg eller kontrastreglage) planeras i annoteringsvyn bör portningen från TASK-21 genomföras.

### 6.2 Datorseende och ML: `opencv-python`, `ultralytics`, `rfdetr`
- **`cv2.VideoWriter_fourcc` (`infrastructure/video/source.py:63`, `tests/conftest.py:86`):** Byt till `cv2.VideoWriter.fourcc(*...)`, vilket är den föredragna metoden i moderna OpenCV-versioner och undviker stub-/typing-varningar.
- **`opencv-python` vs `opencv-python-headless`:** Applikationen använder aldrig `cv2.imshow` eller OpenCV:s eget HighGUI (allt visas i PySide6), men använder DirectShow (`cv2.CAP_DSHOW`) på Windows. `opencv-python-headless` innehåller *videoio* (inklusive DSHOW/MSMF på Windows) men undviker att bundla dubbla UI-bibliotek, vilket minskar risken för symbolkrockar med PySide6.

### 6.3 Kodkvalitet och statisk analys i `pyproject.toml`
I `pyproject.toml` finns `ruff>=0.6` som dev-beroende, men **ingen `[tool.ruff]`-konfiguration** alls (endast standardreglerna `E` och `F` är aktiva).
- **Förslag:** Konfigurera `[tool.ruff.lint]` med regler som fångar deprecations, oanvänd kod och buggar automatiskt:
  ```toml
  [tool.ruff.lint]
  select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
  ```
  Lägg även till `ty` eller `pyright`/`mypy` för statisk typkontroll.

---

## 7. GUI och UX-förbättringar

1. **Hårdkodade mörka färger bryter det ljusa temat ("Ljust"):**
   - I `ui/theme.py` kan användaren välja *System*, *Ljust* eller *Mörkt*.
   - Men i `ui/dataset_view.py` är bakgrunder och ramar hårdkodade för mörkt tema (`IDLE_BACKGROUND = "#2b2b2b"`, `SELECTED_BACKGROUND = "#1d3b57"`, `IDLE_BORDER = "#555"`, rubriktext `"#888"`, `"#10202e"`), och i `ui/detection_view.py:378` sätts `background: #222; color: #888;`. I ljust tema ser datasetkorten ut som svarta klossar mot en vit bakgrund.
   - **Förslag:** Samla semantiska temafärger i `ui/theme.py` eller använd `QPalette`-roller så att både ljust och mörkt tema fungerar konsekvent.
2. **Stora vyer med blandat ansvar:**
   - `ui/dataset_view.py` (1 127 rader) och `ui/detection_view.py` (954 rader) innehåller både återanvändbara generella widgets (`FlowLayout`, `CaptureCard`, `Thumbnail`, `ResourceMeter`, `StreamPanel`) och vyernas affärs-/koordineringslogik.
   - **Förslag:** Bryt ut `FlowLayout` till `ui/flow_layout.py` (eller `ui/style.py`), `CaptureCard`/`Thumbnail` till `ui/dataset_cards.py` och `StreamPanel`/`ResourceMeter` till egna moduler. Då sjunker både `dataset_view.py` och `detection_view.py` till ~450–500 överskådliga rader.

---

## 8. Dokumentation, Backlog och Groma

### 8.1 `README.md` (42 kB) behöver struktureras om
`README.md` är mycket välskriven språkligt och tekniskt korrekt i detaljerna, men har vuxit genom att varje ny task har fyllt på befintliga stycken:
- Punktlistan under `## Lägen` har fyra punkter där varje punkt är ett **enda gigantiskt stycke** (punkten för *Detektion* på rad 54 är 3 400 tecken lång i en enda rad, och *Dataset* på rad 55 är 3 800 tecken lång!). Det gör texten mycket svår att skumma för en ny utvecklare eller operatör.
- **Konkreta fel i `README.md`:**
  - **Rad 3:** Hänvisar till `PLAN.md` (`"Se specs.md för krav och PLAN.md för implementeringsplan"`), men `PLAN.md` finns inte i repot.
  - **Rad 97:** Meningen `"Indikatorn tänds först efter 150 ms, så en operation som hinner klart ändå inte ger en blinkning."` är duplicerad två gånger direkt efter varandra.
  - **Rad 136:** Beskriver fortfarande `classes` i `config.yaml` som `"datasetets etiketter"`, trots att `data.yaml` är master och `config.classes` inte längre används i koden.
- **Förslag:** Dela upp `README.md` med tydliga underrubriker (`### Detektion`, `### Dataset`, `### Annotering`, `### Träning`) eller flytta den djupa tekniska arkitektur-/designhistoriken till `docs/architecture.md` och håll `README.md` koncis (Installation, Snabbstart, Funktioner, Kortfattad filöversikt).

### 8.2 `groma/`-arkitekturdokumentationen har glidit isär från koden
En granskning av `groma/` visar flera avvikelser som bör städas upp via `groma`:
1. **Trasiga källkodsreferenser och länkar från före TASK-22:**
   - `groma/systems/xray-detector/containers/gui-app/components/detectors.md` listar fortfarande de borttagna filerna `xray_detector/detection/registry.py`, `xray_detector/detection/base.py`, `xray_detector/detection/yolo_detector.py` och `xray_detector/detection/rfdetr_detector.py`, samt har trasiga länkar i sin `Relationships`-tabell och anger `RFDETRBase.predict` (som ersattes i rfdetr 1.7).
   - `video-capture.md` listar de borttagna `xray_detector/capture/camera_service.py` och `xray_detector/capture/source.py` samt har trasiga länkar i `Relationships`.
   - `dataset.md` listar de borttagna `xray_detector/dataset/store.py` och `xray_detector/dataset/export.py`.
   - `trainer.md` listar den borttagna `xray_detector/training/trainer.py`.
2. **Felplacerade och okurerade komponenter:**
   - `groma/systems/xray-detector/components/model-input.md` har `parent: xray-detector` (systemnivå) istället för `parent: gui-app` (containernivå) och saknar beskrivning.
   - `training-history.md` och `ui-training-history.md` har båda `title: Training history` och saknar helt beskrivningstext.
3. **Saknade komponenter för nya moduler:**
   - Följande källkodsfiler saknas helt i Groma: `application/evaluation.py`, `infrastructure/dataset_store/augment.py`, `infrastructure/training/metrics.py`, `infrastructure/training/progress.py`, `infrastructure/training/verdict.py` och `ui/variation_dialog.py`.

### 8.3 `backlog/`
- Samtliga 114 uppgifter i `backlog/tasks/` har `status: Done`. För att hålla `backlog/tasks/` överskådlig inför kommande utveckling kan klara uppgifter arkiveras till `backlog/archive/tasks/` via `backlog`-CLI:t.

---

## 9. Prioriterad åtgärdsplan

### Prioritet 1 – Hög effekt, låg insats (Snabba vinster & buggfixar)
1. **Aktivera egentränade modeller i träningsvyns basmodellväljare:** Byt `base_models(...)` till `available_models(...)` i `TrainingView.refresh_models()` (`ui/training_view.py:133`).
2. **Säkra trådsäkerheten i detektorerna:** Lägg till ett `threading.Lock` runt `detect()` i `BaseDetector` (eller per detektor) så att två `StreamWorker`-trådar inte kör `YOLO.predict()` samtidigt på samma instans, och se till att `StreamPanel._to_qimage()` returnerar `.copy()`.
3. **Stoppa `StreamWorker`-loopen vid förlorad källa:** Avbryt `while self._running`-loopen i `StreamWorker.run()` (`camera_service.py:71-73`) när `source.read()` returnerar `None`, så att gamla trådar inte fortsätter skicka `source_lost` i bakgrunden.
4. **Förhindra radering av pågående träning från Inställningar:** Kontrollera om en träning pågår även när en egentränad modell tas bort i `ModelSection._on_remove()` (`ui/model_settings.py:240`).
5. **Rensa bort död kod och skräpfiler:** Ta bort `load_config()`, `_parse_scalar()`, `spec_by_key()`, `device_is_available()`, `AppConfig.classes`, samt `runs/` ur git (och lägg `runs/` och `exports/` i `.gitignore`).

### Prioritet 2 – Förenkling och eliminering av duplicering
6. **Ersätt de tre handskrivna YAML-tolkarna med `PyYAML`:** Använd `yaml.safe_load` / `yaml.safe_dump` i `app_config.py` och `yolo.py`, och återanvänd `read_classes()` i `train_task.py`.
7. **Konsolidera dubbletter:**
   - En enda funktion för fångstgrupp-/bildparsgruppering i `domain/dataset.py`.
   - En enda manifestläsare för `training_manifest.json` (låt `trained_models()` bygga på `training_runs()`).
   - En enda funktion för CUDA-enhetsstatus (slå ihop `device_status()` och `cuda_device_label()`).
   - En enda `bgr_to_qimage()`-hjälpfunktion.
   - En gemensam hjälpfunktion för att fylla modell-`QComboBox` och inaktivera saknade paket (`rfdetr`).

### Prioritet 3 – Prestanda, arkitektur och framtidssäkring
8. **Skala ner och cacha thumbnails i arbetstråden (`DatasetView`):** Skala ner `QImage` till `THUMB_HEIGHT` redan i `DatasetView._load()` och cacha tumnaglarna så att 1 000 bilder i datasetet tar ~150 MB istället för ~8 GB RAM.
9. **Undvik att skriva om PNG-filer vid annoteringsredigering:** Behåll original-`frame` i `AnnotationCanvas` och uppdatera bara `.txt`-labelfiler och metadata när befintliga bildpar redigeras.
10. **Kör datasetexporten vid träningsstart i `BackgroundTask` (och först när schemalagd träning faktiskt startar):** Flytta ut exporten ur `TrainingView._on_start()` så GUI-tråden aldrig fryser och schemalagda nattjobb får med dagens sista annoteringar.
11. **Ersätt `PySide6.QtCharts` med en temamedveten `QPainter`-graf (eller `QtGraphs`):** Framtidssäkrar mot utfasningen av `QtCharts` i Qt 6.8/6.10 och gör att graferna följer mörkt/ljust tema.
12. **Uppdatera `README.md` och kurera `groma/`:** Rätta dubblettmeningen och den saknade `PLAN.md`-hänvisningen i `README.md`, dela upp jättestyckena under `## Lägen`, och rensa bort de gamla pre-TASK-22-sökvägarna i `groma/`.
