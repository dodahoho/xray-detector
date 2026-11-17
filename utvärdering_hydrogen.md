# Utvärdering av projektet X-ray detector

Detta dokument sammanfattar en teknisk utvärdering av kodbasen, arkitekturen, ramverksvalen, GUI:t och dokumentationen i `G:\xray-detector`, samt konkreta förslag på hur projektet kan göras enklare, effektivare, mer lättunderhållet och fritt från duplicering och död/gammal kod.

---

## 1. Övergripande intryck

Projektet är funktionellt rikt, väldokumenterat med svenska docstrings och har en stor testsvit (70+ testfiler under `tests/`). Samtidigt bär kodbasen tydliga spår av inkrementell, task-driven utveckling (119 uppgifter i `backlog/tasks/`): många moduler har vuxit till stora monoliter, ansvar har läckt mellan arkitekturlager och flera mekanismer har implementerats parallellt på olika ställen.

---

## 2. Arkitektur & lagerindelning

Projektet siktar på en lagerindelad DDD-/Clean Architecture-struktur (`domain`, `application`, `infrastructure`, `ui`), men i praktiken bryts beroendereglerna på flera avgörande punkter:

### 2.1 Observationer
1. **UI importerar `infrastructure` direkt:**
   - `xray_detector/ui/detection_view.py` (r. 27–29) importerar `BaseDetector`, `ResourceMonitor`, `ResourceUsage` och `list_device_modes` direkt från `infrastructure`.
   - `xray_detector/ui/dataset_view.py` (r. 27) importerar `augment.describe` från `infrastructure`.
   - `xray_detector/ui/variation_dialog.py` (r. 24) importerar `MAX_SCALE, MIN_SCALE` från `infrastructure.dataset_store.augment`.
2. **`application` är hårt kopplat till PySide6 och `infrastructure`:**
   - `xray_detector/application/background_task.py` (r. 11) och `xray_detector/application/training_service.py` (r. 4) importerar `PySide6.QtCore` (`QObject`, `QRunnable`, `QThreadPool`, `QTimer`, `Signal`). Applikationslagret kan därmed inte testas eller återanvändas utan Qt.
   - Samtliga tjänster i `application/` (`dataset_service.py`, `evaluation.py`, `model_registry.py`, `training_history.py`, `training_service.py`, `video_service.py`) importerar konkreta implementationer från `infrastructure/` utan portar/protokoll (`typing.Protocol`).
3. **Cykliskt beroende `infrastructure` → `application`:**
   - `xray_detector/infrastructure/detectors/rfdetr_detector.py` (r. 29) importerar `capture_third_party_logs` från `xray_detector.application.app_config`.
4. **Domänlagret läcker `numpy`:**
   - `xray_detector/domain/capture.py` och `xray_detector/domain/dataset.py` importerar `numpy` för bildmatriser.

### 2.2 Förslag
- **Inför `Protocol`-gränssnitt i `domain`/`application`** för t.ex. `Detector`, `DatasetRepository`, `VideoSource` och `Trainer`, och injicera implementationerna i `app.py` (Composition Root).
- **Flytta `BackgroundTask` till `ui/`** (eftersom den använder `QThreadPool`, `QCoreApplication.processEvents()` och Qt-signaler för GUI-tråden), och ersätt `QTimer`/`Signal` i `TrainingScheduler` med en ren Python-klock-/callback-modell eller en Qt-adapter i `ui/`.
- **Flytta domänkonstanter** som `MAX_SCALE`, `MIN_SCALE` och `describe()` till `domain/dataset.py` så `ui/` aldrig behöver importera `infrastructure`.
- **Bryt den cykliska importen** i `rfdetr_detector.py` genom att lägga loggfångsten i `infrastructure/logging.py` eller skicka in en callback.

---

## 3. Duplicering & parallella implementationer

Flera problem har lösts på flera ställen samtidigt i stället för i en gemensam abstraktion:

### 3.1 Tre handskrivna YAML-tolkar
1. `xray_detector/application/app_config.py` (`apply_yaml_overrides`, r. 59–100): egen rad-för-rad-parser för `config.yaml`.
2. `xray_detector/infrastructure/dataset_store/yolo.py` (`read_classes`, `_parse_names`, `_parse_indented_names`, r. 19–63): egen parser för `data.yaml` med `ast.literal_eval`.
3. `xray_detector/infrastructure/training/train_task.py` (`_read_data_classes`, r. 69–89): ytterligare en separat parser för `data.yaml`.

**Förslag:** `ultralytics` drar redan in `PyYAML` (`yaml`). Använd `yaml.safe_load` via en enda hjälpfunktion (eller deklarera `pyyaml` explicit i `pyproject.toml`), alternativt använd `tomllib` (inbyggt i Python 3.11+) för `config.toml` och `yaml.safe_load` för YOLO:s `data.yaml`. Då försvinner alla tre specialparsers.

### 3.2 Duplicerad modellväljare & RF-DETR-kontroll i UI
- `DetectionView.refresh_models` / `_disable_unavailable_models` (`xray_detector/ui/detection_view.py`, r. 627–655) och `TrainingView.refresh_models` / `_disable_missing_rfdetr` (`xray_detector/ui/training_view.py`, r. 125–156) gör nästan identisk populering av `QComboBox` och inaktivering av RF-DETR när paketet saknas.

**Förslag:** Extrahera en gemensam widget eller hjälpare, t.ex. `ModelComboBox(QComboBox)` i `xray_detector/ui/`, som hanterar `ModelSpec`-listan, `importlib.util.find_spec("rfdetr")`, avstängda poster och valbevarande.

### 3.3 Tre kopior av BGR-till-`QImage`-konvertering
Samma konvertering (`frame[:, :, ::-1]` → `QImage(..., Format_RGB888).copy()`) finns på tre ställen:
- `xray_detector/ui/annotation_view.py` (r. 82–85)
- `xray_detector/ui/dataset_view.py` (r. 962–964)
- `xray_detector/ui/detection_view.py` (r. 479–484)

**Förslag:** Samla detta i en gemensam funktion `bgr_to_qimage(frame: np.ndarray) -> QImage` (och omvänt `qimage_to_bgr`) i en `ui/image_utils.py`.

### 3.4 Åtta parallella `BackgroundTask` + `wait_for_*`-mönster
`BackgroundTask` och manuella `wait_for_*()`-metoder upprepas i fem UI-klasser (`annotation_view.py`, `dataset_view.py` ×3, `detection_view.py` ×2, `model_settings.py`, `training_history.py`). I `main_window.py` (r. 271–274) måste `closeEvent` uttryckligen anropa fyra olika `wait_for_*()`-metoder.

**Förslag:** Skapa en `TaskRunner` eller `BusyTaskMixin` i `ui/` som äger aktiva tasks, kopplar `BusyIndicator`, hanterar felrapportering och erbjuder en enda `wait_all()` vid stängning. Dessutom bör `BackgroundTask.wait()` (r. 43–50) använda `QEventLoop` / `QThreadPool.waitForDone()` i stället för en 5 ms `while`-poll-loop med `QCoreApplication.processEvents()`.

### 3.5 Parallella inställningsytor (Flik vs Dialog)
Trots att TASK-43 flyttade vyernas inställningar till en `Inställningar`-knapp per vy (`settings_dialog.py`), finns `SettingsView` (`ui/settings_view.py`) kvar som en femte flik i `MainWindow` enbart för `ThemeSection` och `ModelSection`.

**Förslag:** Ta bort den femte fliken (`SettingsView`) och lägg i stället `ThemeSection` och `ModelSection` i en global inställningsdialog (t.ex. via meny/verktygsfält eller en flik i `SettingsDialog`). Det ger ett enhetligt GUI-mönster och förenklar `MainWindow`.

---

## 4. Död kod, gammal kod & rester från tidigare uppgifter

1. **Oanvänd funktion `_parse_scalar`:**
   - `xray_detector/application/app_config.py` (r. 45–56) definierar `_parse_scalar()`, som inte anropas någonstans i filen.
2. **Övergiven `QGraphicsScene`-prototyp i `tests/prototype/`:**
   - `tests/prototype/annotation_scene.py` och `tests/prototype/test_prototype_annotation_scene.py` (från TASK-21-spiken) ligger kvar i testsviten trots att produktionskoden i `ui/annotation_view.py` valde en egen `QPainter`-baserad `AnnotationCanvas`.
3. **Engångsmigreringar som körs i produktion:**
   - `xray_detector/infrastructure/dataset_store/store.py`: `_migrate_versions()` (TASK-57, r. 35–58) och `_migrate_coco()` (TASK-78, r. 61–105).
   - `xray_detector/app.py`: `_warn_about_legacy_models()` (TASK-50, r. 48–60).
   - *Rekommendation:* Om migreringarna är genomförda i befintliga miljöer bör de flyttas till ett fristående CLI-migreringsskript (eller tas bort) så att appstart och `DatasetStore.__init__` blir renare.
4. **Bruten dokumentationslänk:**
   - `README.md` (r. 3) hänvisar till `PLAN.md`, som inte finns i repot.

---

## 5. GUI-kod & ramverksval

### 5.1 Monolitiska vyfiler
De fyra huvudvyerna står för över 3 400 rader kod tillsammans:
- `xray_detector/ui/dataset_view.py`: **1 127 rader** (blandar `FlowLayout`, `CaptureCard`, `Thumbnail`, filtrering, sortering, export-orkestrering, variations-orkestrering och 17 `setStyleSheet()`-anrop).
- `xray_detector/ui/detection_view.py`: **954 rader** (blandar `ResourceMeter`, `StreamPanel`, `DetectionView`, `draw_detections`, `_CaptureKeyFilter`, enhets-/modellhantering och bildkonvertering).
- `xray_detector/ui/annotation_view.py`: **804 rader** (egen `QPainter`-canvas med manuell zoom/pan/hit-testing i stället för `QGraphicsView`/`QGraphicsScene`).
- `xray_detector/ui/training_view.py`: **603 rader**.

**Förslag:**
- Dela upp `ui/` i delpaket per vy, t.ex. `ui/dataset/` (`view.py`, `card.py`, `flow_layout.py`), `ui/detection/` (`view.py`, `stream_panel.py`, `resource_meter.py`, `overlay.py`) och `ui/annotation/`.
- Överväg att faktiskt slutföra spiken från TASK-21 och migrera `AnnotationCanvas` till `QGraphicsView`/`QGraphicsScene`: det ger hårdvaruaccelererad/inbyggd zoom, pan, markering och `cosmetic` pennor med betydligt mindre manuell koordinatmatte.

### 5.2 Blandning av `QPalette` (`theme.py`) och hårdkodade inline-`setStyleSheet()`
`ui/theme.py` sätter Fusion-stil och `QPalette` för ljust/mörkt tema, men **31 inline-`setStyleSheet()`-anrop** (varav 17 i `dataset_view.py`) hårdkodar färger som `#e5a52a` och `#8a8a8a` direkt i widgetar.

**Förslag:** Ersätt inline-stylesheets med en central QSS-mall kopplad till `theme.py` och dynamiska Qt-properties (t.ex. `widget.setProperty("selected", True)` + `style().polish()`).

### 5.3 Skör koppling i `MainWindow`
- `xray_detector/ui/main_window.py` hårdkodar annoteringsflikens index som `1` på flera ställen (`setTabEnabled(1, ...)`, `index == 1`, `setCurrentIndex(1)`). Använd `self.tabs.indexOf(self.annotation_view)` eller ett enum/referens.
- `main_window.py` (r. 164, 255) anropar den privata metoden `self.annotation_view._on_save()`. Exponera en publik `save()`-metod.

### 5.4 Ramverksval
- **PySide6 (Qt Widgets + QtCharts):** Ett bra val för en Windows-desktopapplikation med dubbla realtidsströmmar, UVC-kameror och kioskläge. QML är inte nödvändigt här, men `QGraphicsView` bör utnyttjas för annoteringsduken.
- **OpenCV (`opencv-python` vs `opencv-python-headless`):** `pyproject.toml` använder `opencv-python>=4.9`. Eftersom GUI:t helt ritas av PySide6 behövs inte OpenCV:s HighGUI-fönster (`cv2.imshow`), och `opencv-python-headless` kan undvika Qt-plugin-konflikter på vissa miljöer (kontrollera dock DirectShow/MSMF-stöd i headless-bygget på Windows innan byte).
- **Trådning i `StreamWorker` (`infrastructure/video/camera_service.py`):** `StreamWorker` ärver direkt från `QThread` och delar `_detector`, `_detections` och `_running` mellan GUI-tråden och arbetstråden utan lås (`QMutex`/`threading.Lock`). Använd i stället `QThread.requestInterruption()`/`isInterruptionRequested()` och skydda delad state med ett lås (eller skicka `set_detector` via köad signal/slot till en `QObject`-worker flyttad med `moveToThread`).

---

## 6. Deprecations & Python-modernisering

- **Python 3.11+ & PySide6 6.7+:** Kodbasen använder redan modern typsyntax (`X | Y`, `list[...]`, `dict[...]`) och `datetime.now(UTC)` / `UTC` utan gamla `typing.Optional` eller `datetime.utcnow()`. Inga uppenbara anrop till borttagna Qt5-API:er (`exec_()`, `QDesktopWidget`) hittades.
- **Däremot finns brister i beroendehantering och livscykel:**
  - `StreamWorker` bör följa Qt6:s rekommenderade `moveToThread`-mönster eller `isInterruptionRequested()`.
  - `BackgroundTask.wait()` bör undvika `QCoreApplication.processEvents()` i en tight polling-loop, vilket kan orsaka re-entrancy-buggar i Qt.

---

## 7. Dokumentation & projekthygien

1. **`README.md` är svårläst (41,8 KB på bara 153 rader):**
   - Punkterna under `## Lägen` och `## Inställningar` (r. 54–76) är gigantiska textblock på flera tusen tecken per stycke som blandar användarguide, prestandamätningar och historiska TASK-beslut.
   - **Förslag:** Dela upp `README.md` i en kortfattad snabbstart/användarguide, flytta arkitektur- och designbeslut till `docs/` (eller `groma/`) och ta bort referensen till den saknade filen `PLAN.md`.
2. **Överlappande dokumentationssystem (`backlog/` + `groma/` + `README.md`):**
   - `backlog/tasks/` innehåller 119 task-filer och `groma/` innehåller 45+ arkitekturfiler. Om samma beteende dokumenteras i både `README.md`, `groma/` och kodkommentarer (`TASK-XX`) riskerar dokumentationen snabbt att glida isär. Låt `groma/` äga arkitekturbilden, `README.md` äga körning/användning och håll kodkommentarer fokuserade på *varför*, inte task-nummer.

---

## 8. Prioriterad åtgärdsplan

| Prio | Åtgärd | Effekt |
| :--- | :--- | :--- |
| **1 (Hög)** | **Konsolidera de 3 YAML-parsers** (`app_config.py`, `yolo.py`, `train_task.py`) till `yaml.safe_load` och ta bort oanvända `_parse_scalar`. | Minskar buggrisk och duplicering direkt. |
| **2 (Hög)** | **Fixa trådsäkerhet i `StreamWorker`** (lås kring `_detector` + `isInterruptionRequested()`). | Eliminerar race condition vid modellbyte/paus under aktiv ström. |
| **3 (Hög)** | **Bryt upp de största vyfilerna** (`dataset_view.py` 1 127 rader, `detection_view.py` 954 rader, `annotation_view.py` 804 rader) och extrahera gemensam `ModelComboBox`, `bgr_to_qimage` och `TaskRunner`. | Dramatiskt bättre läsbarhet, testbarhet och mindre duplicering. |
| **4 (Medel)** | **Städa lagergränserna:** flytta `BackgroundTask` till `ui/`, bryt `rfdetr_detector.py` → `app_config.py`, flytta `augment`-konstanter till `domain`. | Renare arkitektur utan cykliska beroenden. |
| **5 (Medel)** | **Ersätt inline-`setStyleSheet` med tematiserad QSS** och slå ihop `SettingsView`-fliken med inställningsdialogen. | Konsekvent utseende i ljust/mörkt tema och enklare `MainWindow`. |
| **6 (Låg)** | **Städa bort `tests/prototype/`, gamla engångsmigreringar och banta `README.md`** (samt ta bort länken till `PLAN.md`). | Renare repo och lättare onboarding. |
