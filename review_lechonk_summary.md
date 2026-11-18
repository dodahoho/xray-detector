# Sammanställning av tre projektutvärderingar (`review_lechonk_summary.md`)

**Källor:**

| Fil | Utvärderare | Omfattning |
| :--- | :--- | :--- |
| `utvärdering_argon.md` | Argon (2026-11-17) | Helhetsutvärdering: kodbas, tester, arkitektur, ramverk, GUI/UX, dokumentation, Groma/Backlog |
| `utvärdering_hydrogen.md` | Hydrogen | Teknisk utvärdering: arkitektur, duplicering, död kod, GUI, dokumentation |
| `review_vibe_deepseek41_flash.md` | Vibe/DeepSeek (TASK-121, 2026-11-17) | Full genomläsning + ruff/AST/pytest-baslinje (861 passed, 1 skipped) |

---

## 1. Vad alla tre är överens om

1. **Duplicering är projektets största strukturella problem.** Samma logik är implementerad 2–4 gånger på olika ställen (YAML-parsning, fångstgruppering, manifestläsning, enhetsstatus, IoU, BGR→QImage, modellväljare).
2. **Tre handskrivna YAML-tolkare ska ersättas av `PyYAML`** (`yaml.safe_load`), som redan finns i beroendeträdet via `ultralytics`. (`train_task.py` ska återanvända `read_classes()` från `yolo.py`.)
3. **`ui` importerar `infrastructure` direkt** (`detection_view.py`, `dataset_view.py`, `variation_dialog.py`) och bryter därmed den lagerindelade arkitekturen.
4. **Vyfilerna är för stora** (`dataset_view.py` ~1 127 rader, `detection_view.py` ~954, `annotation_view.py` ~804, `training_view.py` ~603) och blandar widgets, affärslogik, `QSettings` och trådhantering – de bör delas upp.
5. **Hårdkodade färger/inline-`setStyleSheet` bryter ljust tema** (t.ex. `detection_view.py:378` `background: #222`, mörka konstanter i `dataset_view.py`); färger ska hämtas från palett/tema.
6. **Död kod finns och ska bort:** `_parse_scalar()`, `spec_by_key()`, `load_config()`, `device_is_available()` (argon och vibe listar samma symboler; hydrogen samma för `_parse_scalar`).
7. **`tests/prototype/` (TASK-21-spiken) ligger kvar i testsviten och ska bort** – den testar inte produktionskod.
8. **Engångsmigreringar körs vid varje uppstart** (`_migrate_versions()`, `_migrate_coco()` i `DatasetStore.__init__`, `_warn_about_legacy_models()`) och bör inte ligga i produktionskoden.
9. **`README.md` är svårläst** (~42 kB, jättestycken under `## Lägen`) och **refererar `PLAN.md` som inte finns** – ska struktureras om och länken bort.
10. **PySide6 är rätt ramverksval** för en Windows-desktopapp med dubbla strömmar – byt inte GUI-ramverk.
11. **Testsviten är omfattande och värdefull** (70+ filer, kan köras utan kamera/GPU) och bör behållas.
12. **Inkrementell "big bang"-refaktorering av vyerna ska undvikas** – dela ut en widget i taget (vibe är explicit; argon/hydrogen föreslår samma inkrementella uppdelning).

## 2. Förslag som bara någon/några av dem har

### Endast Argon
- Prestandaflaskhals i `DatasetView._load()`: alla bilder laddas i full upplösning (~6–8 GB RAM för 1 000 bilder) – skala ner till tumnagel i arbetstråden och cacha.
- Träningsstart blockerar GUI-tråden (synkron export); schemalagd träning exporterar vid klickögonblicket, inte vid faktisk start; YOLO behöver inte kopiera bilder alls (train.txt/val.txt).
- PNG-filer skrivs om i onödan vid redigering av annoteringar – skriv bara om `.txt`-filer/metadata.
- Träningsvyns basmodellväljare använder `base_models()` i stället för `available_models()` – egentränade modeller kan inte väljas som bas.
- `StreamWorker` loopar `source_lost` i evighet efter förlorad källa; `ModelSection` saknar kontroll mot att radera pågående träning; `closeEvent` missar `wait_for_*` för två vyer; dubbel dialog vid stängning.
- `PySide6.QtCharts` är deprecated (Qt 6.8/6.10) och följer inte temat – ersätt med egen `QPainter`-graf.
- `AppConfig.classes` är kvarleva och ska bort; `runs/` ska ur git + `.gitignore`; `cv2.VideoWriter_fourcc` → `cv2.VideoWriter.fourcc`; `opencv-python` → `opencv-python-headless`.
- Groma-dokumentationen har glidit isär från koden (trasiga pre-TASK-22-sökvägar, saknade komponenter); arkivera klara backlog-tasks.
- `AnnotationCanvas` bör portats till `QGraphicsView` *om fler funktioner planeras*.

### Endast Hydrogen
- Inför `Protocol`-gränssnitt (`Detector`, `DatasetRepository`, `VideoSource`, `Trainer`) och Composition Root i `app.py`.
- Bryt det cykliska beroendet `infrastructure → application` (`rfdetr_detector.py` importerar `app_config`); domänlagret läcker `numpy`.
- Flytta `BackgroundTask` till `ui/`; ersätt `QTimer`/`Signal` i `TrainingScheduler` med ren Python-klocka.
- `TaskRunner`/`BusyTaskMixin` som äger aktiva tasks och en enda `wait_all()` vid stängning; `BackgroundTask.wait()` ska inte polla med `processEvents()`.
- Ta bort femte fliken `SettingsView` och lägg `ThemeSection`/`ModelSection` i en global inställningsdialog.
- `main_window.py` hårdkodar tab-index 1 och anropar privata `annotation_view._on_save()`.
- `opencv-python-headless` (med kontroll av DirectShow-stöd på Windows).

### Endast Vibe/DeepSeek
- **P1-risker:** trasig `dataset.json` kraschar hela appen vid start (saknar felhantering i `_load_metadata`); nattfönstret har två nycklar som kan glida isär; `num_objects` underhålls för hand på fem ställen.
- **Ingen CI** (`.github/` saknas) – GitHub Actions med `ruff` + `pytest`; `pytest-xdist -n auto` (270 s → <90 s); delade fixtures i `conftest.py`; `slow`-markör.
- `[tool.ruff]`-konfiguration saknas (55 fel default, 231 med utökade regler).
- `media/` innehåller 38 MB mp4 i git – Git LFS eller utanför repot; `media/README.md` dokumenterar bara 2 av 6 filer.
- `specs.md` beskriver ett system som inte längre finns (datasetversioner borttagna i TASK-57).
- Blandade tidsformat utan tidszon (`pending.py`, `training_service.py`, `training_view.py`) – `datetime.now(UTC)` överallt; `zip()` utan `strict=` på fyra ställen; funktionslokala importer (43 st, några ska till toppnivå).
- `_write_sample()` i `store.py` (största enskilda dupliceringen, ~40 rader × 3); `Detection.to_dict()/from_dict()`; `TrainArgs`-dataclass; `export_yolo` ska returnera `data.yaml`-sökvägen; `schema_version` + explicit migreringskedja; `ui/colors.py`-palett; `Protocol` för `_settings_sections()`.
- Räkneavvikelse: vibe anger 71 testfiler/862 tester; argon 72 testfiler; hydrogen 70+.

### Två av tre (inte alla)
- **Fångstgruppering i fyra varianter** → en gemensam `capture_group()`/`group_images()` i `domain/dataset.py` (argon + vibe).
- **`training_manifest.json` läses dubbelt** (`model_registry` + `training_history`) → en gemensam `read_manifest()` (argon + vibe).
- **Två CUDA-enhetsstatus-funktioner** → en enda källa (argon + vibe).
- **Två IoU-implementationer** → en (argon + vibe).
- **Tre BGR→QImage-kopior** → gemensam `bgr_to_qimage()` (argon + hydrogen).
- **Dubbel modell-QComboBox/RF-DETR-kontroll** → gemensam `ModelComboBox` (argon + hydrogen).
- **Trådsäkerhet i `StreamWorker`/delad detektor** – lås kring `detect()` (argon + hydrogen).
- **`DatasetService` är en tunn pass-through-fasad** (argon + vibe).
- **`runs/` ur git + `.gitignore`** (argon + vibe).
- **`opencv-python-headless`** (argon + hydrogen).
- **Magiska tab-index + privat `_on_save()` i `main_window.py`** (hydrogen + vibe).
- **`ruff` oconfigurerat** (argon + vibe).
- **Porta `AnnotationCanvas` till `QGraphicsView`** – överväg (argon + hydrogen, båda villkorligt).

## 3. Motsägelser och olika synsätt

1. **Hur strikt lagerarkitekturen ska försvaras:** Argon och Hydrogen vill strukturellt bryta beroendena (ui ska aldrig importera infrastructure; `Protocol`-gränssnitt; flytta `BackgroundTask` till `ui`). Vibe menar att alternativet att bara **dokumentera** att `application` är en fasad bredvid infrastructure är "billigare och mer ärligt". Inte en direkt motsägelse, men olika ambitionsnivå för samma fynd.
2. **Hantering av engångsmigreringarna:** Argon och Hydrogen vill ta bort dem (eller flytta till fristående CLI-skript) om fältinstallationerna redan är migrerade. Vibe vill i stället införa `schema_version` + explicit migreringskedja så gamla migreringar kan pensioneras kontrollerat. Olika vägval: borttagning vs. versionering.
3. **QtCharts:** Argon vill ersätta `QChart` med en egen temamedveten `QPainter`-graf på grund av deprecation i Qt 6.8/6.10. Vibe säger "byt inte GUI-ramverk" och att QtCharts "kom gratis" – vibe motsätter sig alltså inte en ersättning av själva grafen, men betonar att ett ramverksbyte är fel väg; i praktiken olika tyngdpunkt snarare än saklig motsägelse.
4. **Små faktaavvikelser:** antalet backlog-tasks uppges som ~120 (argon), 119 (hydrogen); testfiler 72 (argon), 70+ (hydrogen), 71 (vibe). Inga sakliga motsägelser, men siffrorna skiljer sig något mellan rapporterna.

## 4. Samlad åtgärdslista (från samtliga tre utvärderingar)

### Prioritet 1 – Buggar, risker och grind (först)

| # | Åtgärd | Källa |
| :--- | :--- | :--- |
| 1 | Lägg till `[tool.ruff]` i `pyproject.toml` (line-length 100, target py311, regler E/F/I/UP/B/SIM/C4/PERF/RUF; ignorera E501/PLC0415 till en början) och kör `ruff check --fix` | Vibe, Argon |
| 2 | Skapa CI (GitHub Actions): `uv sync`, `ruff check`, `pytest -q`; lägg till `pytest-xdist` (`-n auto`) och `slow`-markör | Vibe |
| 3 | Felhantering i `DatasetStore._load_metadata()` – fånga `(OSError, ValueError)`, logga, returnera tom struktur (trasig `dataset.json` får inte krascha appstart) + test | Vibe |
| 4 | En enda nyckel för nattfönstret (`training/night_start` som "HH:MM") med `parse_clock`/`format_clock` i `domain/`; migrera `_hour`-nycklarna | Vibe |
| 5 | Räkna `num_objects` i `_save_metadata()` (eller härled det) i stället för fem manuella inkrement | Vibe |
| 6 | `ANNOTATION_TAB`-konstant (eller `tabs.indexOf(...)`) och publik `AnnotationView.save()` i stället för magiska index och anrop till `_on_save()` | Vibe, Hydrogen |
| 7 | Trådsäkerhet: `threading.Lock` runt `detect()` i detektorerna; `QThread.isInterruptionRequested()`/lås för delad state i `StreamWorker`; stoppa `source_lost`-loopen vid `read() == None`; `StreamPanel._to_qimage()` ska returnera `.copy()` | Argon, Hydrogen |
| 8 | Förhindra radering av pågående träning även från `ModelSection._on_remove()` (samma kontroll som i `TrainingHistoryView`) | Argon |
| 9 | Använd `available_models(...)` i `TrainingView.refresh_models()` så egentränade modeller kan väljas som basmodell | Argon |
| 10 | Fixa `closeEvent`: vänta även på `training_view.history.wait_for_evaluation()` och `settings_view.model_section.wait_for_download()`; åtgärda dubbel dialog vid stängning med tomma annoteringar | Argon |

### Prioritet 2 – Eliminera duplicering och städa arkitekturen

| # | Åtgärd | Källa |
| :--- | :--- | :--- |
| 11 | Ersätt de tre handskrivna YAML-tolkarna med `yaml.safe_load`/`safe_dump` (deklarera `pyyaml` explicit); låt `train_task.py` återanvända `read_classes()` från `yolo.py` | Alla tre |
| 12 | Flytta fångstgrupperingslogiken till `domain/dataset.py` (`capture_group()`/`group_images()`) och använd i `store`, `export`, `evaluation`, `dataset_view` | Argon, Vibe |
| 13 | En gemensam `read_manifest()` för `training_manifest.json`; låt `trained_models()` bygga på `training_history` | Argon, Vibe |
| 14 | En enda enhetsstatus (`cuda_device_label()`); flytta färger till `ui/colors.py` | Argon, Vibe |
| 15 | Gemensam `bgr_to_qimage()` (alltid `.copy()`); gemensam `ModelComboBox`/hjälp för modellcombo + RF-DETR-kontroll; en IoU-implementation | Argon, Hydrogen, Vibe |
| 16 | `_write_sample()` i `store.py` (ersätter ~40 rader × 3 i `add_samples`/`replace_samples`/`add_variations`) | Vibe |
| 17 | Beslut om `DatasetService`: ta bort den eller låt den äga verklig logik (t.ex. `num_objects`, exportlayout); samma för `VideoService` | Argon, Vibe |
| 18 | Bryt lagerbrott: flytta `augment`-konstanter (`MIN_SCALE`/`MAX_SCALE`/`describe`) till `domain`; bryt cykliskt beroende `rfdetr_detector → app_config`; överväg `Protocol`-gränssnitt eller dokumentera fasadvalet explicit | Alla tre (olika lösning, se §3.1) |
| 19 | Central palett i `ui/colors.py` + temaberoende färger via `QPalette`/QSS i stället för 31 inline-`setStyleSheet` (fixar ljust tema, t.ex. `detection_view.py:378`) | Alla tre |
| 20 | Dela upp de stora vyfilerna inkrementellt (ej big bang): bryt ut `FlowLayout`, `CaptureCard`/`Thumbnail`, `StreamPanel`/`ResourceMeter`, ev. `ModelComboBox`, `TaskRunner`/`BusyTaskMixin` med en `wait_all()` | Alla tre, Hydrogen |
| 21 | `Detection.to_dict()/from_dict()` i `domain/detection.py`; `TrainArgs`-dataclass i `train_task.py`; `export_yolo` returnerar `data.yaml`-sökvägen; `Protocol` för `_settings_sections()`; `zip(..., strict=)`; `datetime.now(UTC)` överallt; funktionslokala importer till toppnivå (utom lazy torch/ultralytics/rfdetr) | Vibe |
| 22 | Ta bort femte fliken `SettingsView`, flytta sektionerna till global inställningsdialog; flytta `BackgroundTask` till `ui/` eller ersätt `QTimer`/`Signal` i schemaläggaren | Hydrogen |
| 23 | Överväg att slutföra TASK-21-portningen av `AnnotationCanvas` till `QGraphicsView` (villkorligt, om fler funktioner planeras) | Argon, Hydrogen |

### Prioritet 3 – Prestanda, städning och dokumentation

| # | Åtgärd | Källa |
| :--- | :--- | :--- |
| 24 | Skala ner bilder till tumnagelstorlek redan i `DatasetView._load()`-tråden och cacha tumnaglar (minne eller `datasets/.thumbs/`) – från ~8 GB till ~150 MB för 1 000 bilder | Argon |
| 25 | Skriv inte om PNG-filer vid redigering av annoteringar – uppdatera bara `.txt`-filer och metadata | Argon |
| 26 | Kör datasetexport vid träningsstart i `BackgroundTask`, och för schemalagda jobb först när jobbet faktiskt startar; använd `train.txt`/`val.txt` för YOLO så bilder inte kopieras | Argon |
| 27 | Ta bort död kod: `load_config()`, `_parse_scalar()`, `spec_by_key()`, `device_is_available()`, `AppConfig.classes`, `SPLITS`, `NO_RUNS`, oanvänd `QColor`-import, oanvänd `mode`-variabel | Argon, Vibe |
| 28 | Ta bort `tests/prototype/`; besluta om TASK-21-prototypen (porta eller ta bort) | Alla tre |
| 29 | Ta bort engångsmigreringarna ur produktionskoden – antingen bort/CLI-skript, eller `schema_version` + explicit kedja (se §3.2) | Alla tre (olika vägval) |
| 30 | `git rm --cached runs/` + lägg `runs/` och `exports/` i `.gitignore`; hantera `media/*.mp4` (38 MB) via Git LFS eller utanför repot + komplett `media/README.md` | Argon, Vibe |
| 31 | Dela upp `README.md` (snabbstart <150 rader + `docs/arkitektur.md` + `docs/beteende.md`), ta bort `PLAN.md`-länken och dubblettmeningen, ta bort `classes`-beskrivningen; uppdatera eller arkivera `specs.md` | Alla tre, Vibe |
| 32 | Kurera `groma/` (rensa pre-TASK-22-sökvägar, lägg till saknade komponenter); arkivera klara backlog-tasks | Argon |
| 33 | Testsvit: `pytest-xdist`, delade fixtures i `conftest.py`, `slow`-markör | Vibe |
| 34 | Ersätt `PySide6.QtCharts` med temamedveten `QPainter`-graf (deprecated i Qt 6.8/6.10); byt `cv2.VideoWriter_fourcc` → `cv2.VideoWriter.fourcc`; utvärdera `opencv-python-headless` (kontrollera DirectShow på Windows) | Argon, Hydrogen |

---

**Rekommenderad ordning (enligt vibe, stöds av de andra):** P1-punkterna 1–10 först (en dag – störst riskreduktion), sedan städning (27–30, ~en timme), sedan P2 när respektive modul ändå rörs, sist P3-dokumentation. Undvik big-bang-refaktorering av vyerna innan CI är på plats.
