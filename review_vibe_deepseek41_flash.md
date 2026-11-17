# Utvärdering av xray-detector

**Datum:** 2026-11-17
**Uppdrag:** TASK-121 – utvärdera hur projektet kan förenklas, effektiviseras och bli mer förvaltningsbart.
**Omfattning:** `xray_detector/` (11 575 rader), `tests/` (71 filer, 862 tester), `README.md`, `specs.md`, `pyproject.toml`, repo-hygien.
**Metod:** full genomläsning av samtliga produktionsmoduler, `ruff` med både default- och utökad regeluppsättning, AST-skanning efter oanvända definitioner, `pytest` som baslinje, samt manuell verifiering av varje fynd nedan.

**Baslinje vid genomgången:** `861 passed, 1 skipped in 270.41s`. Inget i den här rapporten är ett testfel – allt är strukturellt.

---

## 1. Sammanfattning

Projektet är i gott skick. Lagren finns, testerna är många och meningsfulla, och kommentarerna förklarar *varför* kod ser ut som den gör – vilket är ovanligt och värdefullt. Det som håller tillbaka det är inte kvaliteten i enskilda moduler, utan **tre saker**:

1. **Samma sak är implementerad två till fyra gånger.** Manifest, `data.yaml`, fångstgruppering, enhetsstatus, IoU och nattfönstret har alla parallella implementationer som redan börjat glida isär.
2. **GUI-lagret bär för mycket.** Fyra vyer på 600–1 100 rader blandar layout, affärslogik, `QSettings` och trådhantering i samma klass, och `main_window.py` styr dem via magiska tab-index.
3. **Ingen grind håller ordningen.** `ruff` finns som beroende men är oconfigurerat (55 fel i default-läget), det finns ingen CI, och `README.md` har vuxit till 41 KB ändringslogg som redan refererar en fil som tagits bort.

Den enskilt viktigaste åtgärden är **inte** en stor refaktorering. Det är att sätta `[tool.ruff]` + en CI-körning på plats, för då blir resten av listan självdrivande.

---

## 2. Vad som fungerar bra och bör behållas

- **Kommentarerna bär besluten.** `train_task.py` förklarar varför `optimizer=AdamW` ersätter `auto`, `epoch_metrics.py` förklarar Lightnings `_rewrite_with_new_header`, `source.py` förklarar varför FOURCC måste anges vid öppning. Det är den typen av kommentarer som gör en kodbas förvaltningsbar. Ta inte bort dem vid en städning.
- **`json_io.atomic_write_json`** är rätt byggd (tempfil i samma katalog, `fsync`, `os.replace`) och används på de ställen som spelar roll.
- **`export.py`-delningen** är genomtänkt: stratifierad på klassuppsättning, seedad, och syntetiska bilder följer sitt ursprung så train/val inte läcker. Det är den svåraste logiken i projektet och den är rätt.
- **`metrics.py`** är rena numpy-funktioner utan torch-beroende – testbara utan GPU. Föredömligt.
- **`style.py` + `FormCard`** gav enhetliga mått, och `tests/test_style.py`/`test_form_width.py` håller dem kvar. Bra mönster som fler delar borde följa.
- **`shortcuts.py`** samlar tangentbeteendet på ett ställe i stället för att varje vy uppfinner det.

---

## 3. Fynd med prioritet

Prioritet: **P1** = fel eller risk för dataförlust/startkrash, **P2** = underhållskostnad som växer, **P3** = städning.

### P1 – Fel och risker

#### P1.1 En trasig `dataset.json` hindrar appen från att starta

`DatasetStore._load_metadata()` (`infrastructure/dataset_store/store.py:138`) saknar felhantering:

```python
def _load_metadata(self) -> dict:
    if self.metadata_path.exists():
        with open(self.metadata_path, encoding="utf-8") as file:
            return json.load(file)
```

Ett avbrott mitt i en skrivning, en manuellt redigerad fil eller en halv synk ger `JSONDecodeError` som propagerar rakt ut. Kedjan är `MainWindow.__init__` → `_log_startup()` (`ui/main_window.py:94`) → `DatasetService.image_pair_count()` → `load_dataset()` → `_load_metadata()`, så **appen startar inte alls** – den kraschar innan fönstret visas.

Verifierat reproducerbart:

```
KRASCH: JSONDecodeError Expecting property name enclosed in double quotes: line 1 column 3 (char 2)
```

`ModelCatalog._read()` (`application/model_registry.py:168`) gör rätt i samma situation: fångar `(OSError, ValueError)` och faller tillbaka på standardlistan. Datasetet förtjänar samma behandling – en trasig metadatafil ska ge ett tomt dataset och en varning i loggen, inte en död app.

**Förslag:** fånga `(OSError, ValueError)` i `_load_metadata`, logga och returnera tom struktur. Lägg ett test som skriver skräp i `dataset.json` och startar `MainWindow`.

#### P1.2 Nattfönstret har två nycklar som kan glida isär

`TrainingScheduleSection._save_clock()` (`ui/settings_dialog.py:123`) skriver **båda** representationerna:

```python
self.settings.setValue(f"{key}_hour", hour)          # training/night_start_hour = 23
self.settings.setValue(key, f"{hour:02d}:00")        # training/night_start      = "23:00"
```

`TrainingView._on_start()` (`ui/training_view.py:435`) läser strängvarianten, `TrainingScheduleSection.__init__` läser int-varianten, och `TrainingScheduler` (`application/training_service.py:30`) har dessutom egna defaultvärden (`23:00`/`05:00`). Tre ställen för ett värde, synkade för hand.

Det är inte trasigt i dag, men det är precis den sortens duplicering som blir trasig: ändrar någon `_save_clock` utan att ändra läsaren slutar inställningen att gälla tyst.

**Förslag:** en nyckel, `training/night_start` som `"HH:MM"`, med en `parse_clock`/`format_clock` i `domain/` som både vyn och schemaläggaren använder. Migrera `_hour`-nycklarna i `restore_settings()`.

#### P1.3 `num_objects` underhålls för hand på fem ställen

`store.py` räknar om `num_images` i `_save_metadata()` (rad 155) men underhåller `num_objects` inkrementellt i fyra separata operationer:

| Rad | Operation |
| --- | --- |
| 284 | `add_samples` – `+ objects` |
| 332 | `replace_samples` – `- replaced + objects` |
| 415 | `add_variations` – `+ objects` |
| 477 | `delete_images` – `- objects` |

`export.write_manifest()` (rad 293) räknar dessutom om samma tal en femte gång, från annoteringarna. Talet är alltså både lagrat och härlett, och de två kan gå isär. `training_view.py:358` visar det lagrade värdet för användaren.

**Förslag:** räkna `num_objects` i `_save_metadata()` på samma sätt som `num_images`, från `len(read_labels(...))` per bild – eller härled det i `metadata()` och sluta lagra det. Den senare är billigare men kräver en läsning av `labels/`; den förra kostar inget extra eftersom `_save_metadata` redan skriver hela filen.

#### P1.4 `main_window.py` anropar privata metoder och använder magiska tab-index

Annoteringsfliken är tab 1, hårdkodat på tio ställen (`ui/main_window.py:56, 136, 141, 171, 183, 184, 196, 197, 205, 206`). Dessutom anropas `self.annotation_view._on_save()` – en privat metod – från `MainWindow` på två ställen (rad 164 och 255).

Det gör att flikordningen inte kan ändras utan att tio rader följer med, och att `AnnotationView`s interna API är låst utifrån.

**Förslag:** `ANNOTATION_TAB = 1` som modulkonstant (eller `self.tabs.indexOf(self.annotation_view)`), och en publik `AnnotationView.save()` som `_on_save` delegerar till.

---

### P2 – Duplicering och parallella implementationer

#### P2.1 `training_manifest.json` läses av två moduler med var sin tolkning

| Modul | Funktion | Rad |
| --- | --- | --- |
| `application/model_registry.py` | `trained_models()` | 244 |
| `application/training_history.py` | `_read_run()` | 127 |

Båda gör `rglob("training_manifest.json")`, läser `weights_relative`, defaultar `family` till `"yolo"` för äldre manifest, och räknar ut `run_dir.relative_to(trained_dir)`. `model_registry` bygger en `ModelSpec`, `training_history` en `TrainingRun` – men **inläsningen** är densamma och underhålls två gånger. Ett nytt manifestfält måste läggas till på båda ställena, annars syns modellen i väljaren men inte i historiken (eller tvärtom).

**Förslag:** en `read_manifest(path) -> dict` i `infrastructure/training/` som båda använder, eller låt `TrainingRun` vara den enda läsaren och `trained_models()` bygga `ModelSpec` ur den.

#### P2.2 `data.yaml` parsas två gånger, med olika förmåga

`train_task._read_data_classes()` (`infrastructure/training/train_task.py:69`) och `yolo.read_classes()` (`infrastructure/dataset_store/yolo.py:19`) gör samma sak. Den förra är en **delmängd**: den klarar bara listformen på en rad, medan `read_classes` även klarar dictformen över flera rader (`names:\n  0: a\n  1: b`) som ultralytics skriver.

Det betyder att en `data.yaml` som ultralytics har skrivit om ger rätt klasser i datasetvyn men **tom klasslista i träningsmanifestet** – och manifestets `classes` används för modellens visningsnamn (`trained_model_name`).

**Förslag:** importera `read_classes` i `train_task.py` och ta bort `_read_data_classes`. Den behöver bara kompletteras med COCO-grenen (`_annotations.coco.json`).

#### P2.3 Fångstgruppering finns i fyra varianter

| Plats | Rad | Gör |
| --- | --- | --- |
| `store._pair_count()` | 30 | `{image.get("group") or image["id"]}` |
| `export._group_key()` + `_groups()` | 16, 38 | samma, plus `_root_image`-uppföljning |
| `evaluation.view_labels()` | 68 | samma gruppering, för att sätta vy-etikett |
| `dataset_view._pair_count()` | 659 | samma gruppering, filtrerad på `synthetic` |

Alla fyra kodar samma regel: *en bild hör till `group`, annars till sitt eget `id`*. `export`-versionen är den enda som följer `source`-kedjan för syntetiska bilder. De andra tre räknar därför **fel** för en syntetisk bild vars `group` skiljer sig från originalets – vilket är exakt vad `export._root_image` finns för att hantera (TASK-111).

**Förslag:** flytta `_group_key`/`_root_image`/`_groups` till `domain/dataset.py` som `capture_group(image)` och `group_images(images)`, och låt alla fyra anropa dem. Det är en liten ändring med stor effekt: regeln definieras en gång.

#### P2.4 Enhetsstatus finns i två versioner

| Plats | Rad | Retur |
| --- | --- | --- |
| `model_registry.device_status()` | 303 | `("Enhet: CUDA (namn)", "#2a8")` |
| `detectors/base.cuda_device_label()` | 23 | `"CUDA (namn)"` |

Båda kollar `torch.cuda.is_available()` och `get_device_name(0)`, med olika strängar och olika felhantering (`device_status` fångar bara `ImportError`, `cuda_device_label` fångar allt kring `get_device_name`). Färgerna `#2a8`/`#c33` är dessutom hårdkodade i `model_registry` – en applikationsmodul som inte borde känna till CSS.

**Förslag:** `cuda_device_label()` blir enda källan; `device_status()` returnerar `(f"Enhet: {label}", color)` och färgen flyttas till `ui/colors.py`.

#### P2.5 Två IoU-implementationer

`detectors/smoothing._iou()` (rad 111) räknar IoU för en ruta mot en `Detection`; `training/metrics.iou_matrix()` (rad 52) räknar matrisen. Den första är den andra med `n=1`. Inte ett fel, men två ställen att ändra om IoU-definitionen någonsin justeras (t.ex. för att hantera degenererade rutor).

**Förslag:** låg prioritet – men om `smoothing` ändå rörs, låt den använda `iou_matrix` och plocka ut `[0, 0]`.

#### P2.6 Bild- och labelskrivning upprepas tre gånger i `store.py`

`add_samples` (rad 242–285), `replace_samples` (rad 287–335) och `add_variations` (rad 337–415) innehåller samma block:

```python
cv2.imwrite(str(self.images_dir / image_name), frame)
height, width = frame.shape[:2]
rows = [from_pixels(self._class_index(names, a["class_name"]), a["bbox"], width, height)
        for a in annotations]
write_labels(self._label_path(image_name), rows)
metadata["images"].append({...})
```

Cirka 40 rader gånger tre, med små variationer i vilka metadatafält som sätts. Det är den enskilt största dupliceringen i kodbasen.

**Förslag:** `_write_sample(image_name, frame, annotations, names, **extra) -> int` som returnerar antal objekt. De tre anropande funktionerna behåller sin egen metadata- och grupplogik.

#### P2.7 Hårdkodade färger i stället för en palett

`setStyleSheet` används 31 gånger, och färgerna upprepas:

| Färg | Antal | Exempel |
| --- | --- | --- |
| `#888` | 7 | `settings_dialog.py:194`, `training_view.py:100, 198, 257`, `variation_dialog.py:98, 146`, `training_history.py:97` |
| `#c33` | 3 | `settings_dialog.py:255`, `detection_view.py:217`, `model_registry.py:310` |
| `#e5a52a` | 4 | `dataset_view.py:952, 1023, 1024, 1025` |
| `#666` | 3 | `dataset_view.py:891, 1029` |
| `#4da3ff` | 2 | `dataset_view.SELECTED_BORDER` och `busy_indicator.ARC_COLOR` |

`model_settings.MUTED_COLOR = "#888"` (rad 44) finns redan som konstant – den delas bara inte. `detection_view.py:378` sätter `background: #222` oavsett tema, så mörkt läge fungerar men ljust läge får en svart ruta.

**Förslag:** `ui/colors.py` får `MUTED`, `ERROR`, `WARNING`, `SELECTED`, `ACCENT` och en `muted_label()`-hjälp. Temaberoende ytor (som `#222`) hämtas ur `QPalette` i stället för att hårdkodas.

#### P2.8 `Detection` saknar serialisering

`pending.py` (rad 38–76 och 78–119) handskriver `Detection` ↔ dict med sex fält. Det är den enda platsen, men den ligger i infrastrukturen och duplicerar domänobjektets fältlista – läggs ett fält till i `Detection` tystnar det i pending-kön.

**Förslag:** `Detection.to_dict()` / `Detection.from_dict()` i `domain/detection.py`.

#### P2.9 `DatasetService` är en ren vidarebefordran

150 rader där 25 av 26 metoder är en rad som anropar `self.store` eller en modulfunktion:

```python
def classes(self) -> list[str]:
    return self.store.classes()
```

Fasaden tillför inget i dag: den har ingen egen logik, inga invarianter och ingen cachning. Den kostar en fil att underhålla och en nivå att hoppa genom när man läser koden.

**Förslag:** antingen ta bort den och låt vyerna använda `DatasetStore` direkt (den är redan ett rent gränssnitt), eller låt den äga något verkligt – t.ex. `num_objects`-beräkningen och exportlayouten – så den motiverar sin plats. Halvvägs är sämst.

---

### P3 – Död kod och städning

#### P3.1 Oanvända definitioner (verifierat med AST-skanning)

| Fil | Rad | Symbol |
| --- | --- | --- |
| `application/app_config.py` | 45 | `_parse_scalar` |
| `application/model_registry.py` | 224 | `spec_by_key` |
| `application/evaluation.py` | 37 | `SPLITS` |
| `domain/config.py` | 55 | `load_config` |
| `infrastructure/video/devices.py` | 78 | `device_is_available` |
| `ui/training_history.py` | 41 | `NO_RUNS` |
| `ui/detection_view.py` | 9 | oanvänd import `QColor` |
| `application/training_service.py` | 107 | `mode` tilldelas, används aldrig |

`_parse_scalar` är särskilt värd att nämna: den ser ut att vara en del av YAML-tolkningen men anropas aldrig, så `apply_yaml_overrides` hanterar bara strängar, listor och float – inte booleska värden, trots att funktionen finns för det.

#### P3.2 `tests/prototype/` är en spike som fortfarande körs

`tests/prototype/annotation_scene.py` beskriver sig själv som *"INTE produktionskod utan en utvärderingsprototyp"* (TASK-21). Den har sex tester som samlas in av pytest, ett `sys.path.insert`-hack i testfilen, och testar en `QGraphicsScene`-variant som **inte används** – produktionen använder `AnnotationCanvas` i `ui/annotation_view.py`.

**Förslag:** ta bort katalogen. Vill man behålla kunskapen hör den i en Backlog-task eller i `docs/`, inte i testsviten.

#### P3.3 Ultralytics-rester i git

`runs/detect/runs/probe/args.yaml` och `runs/detect/runs/probe/results.csv` är spårade. `runs/` är 11 MB på disk och saknas i `.gitignore` (som bara har `models/`, `models/trained/` och `logs/`).

**Förslag:** `git rm -r --cached runs/` och lägg `runs/` i `.gitignore`.

#### P3.4 38 MB video i git

`media/` innehåller sex mp4-filer (38 MB) som är spårade; `.git` är 61 MB. `media/README.md` dokumenterar två av dem.

**Förslag:** Git LFS för `media/*.mp4`, eller flytta dem utanför repot och låt `media/README.md` beskriva hur de hämtas. Komplettera README med de fyra filer som saknas.

#### P3.5 `README.md` refererar en fil som inte finns

Rad 3: *"Se `specs.md` för krav och `PLAN.md` för implementeringsplan."* – `PLAN.md` togs bort i commit `49ac80b` ("tar bort gammal implementationsplan").

---

## 4. Struktur och arkitektur

### 4.1 Lagren är nominella, inte faktiska

Projektet är indelat i `domain` / `application` / `infrastructure` / `ui` (TASK-22), men beroenderiktningen håller inte:

- **UI importerar infrastruktur direkt** på fem ställen: `dataset_view.py:27` (`augment.describe`), `detection_view.py:27–29` (`BaseDetector`, `ResourceMonitor`, `list_device_modes`), `variation_dialog.py:24` (`augment.MAX_SCALE/MIN_SCALE`).
- **`application` importerar infrastruktur** i fem av åtta moduler (`dataset_service`, `model_registry`, `evaluation`, `training_service`, `app_config`).

Det betyder att `application` inte är ett lager *ovanpå* infrastrukturen – det är ett bekvämlighetslager *bredvid*. Det är ett fullt försvarbart val för en app av den här storleken, men då bör det sägas rakt ut i `README.md`/`groma/`, för i dag beskrivs det som lagerdelning.

**Förslag:** antingen (a) dokumentera att `application` är en fasad över infrastrukturen och att UI får importera infrastruktur, eller (b) flytta de fem UI-importarna bakom `application`. Alternativ (a) är billigare och mer ärligt.

### 4.2 Vyerna är för stora

| Fil | Rader | Innehåller |
| --- | --- | --- |
| `ui/dataset_view.py` | 1 128 | `FlowLayout`, kort- och thumbnail-widgets, filter, export, variationer, markering, `QSettings` |
| `ui/detection_view.py` | 954 | `StreamPanel`, resursmätare, overlay, klassfilter, modelladdning, källpersistens |
| `ui/annotation_view.py` | 804 | `AnnotationCanvas` (ritning, zoom, träffytor), klasshantering, sparning |
| `ui/training_view.py` | 603 | Formulär, schemaläggning, logg, graf, historik, utvärdering |

Varje vy är widgetbygge + affärslogik + `QSettings` + trådhantering i en klass. Det är där de flesta av P2-fynden bor.

**Förslag (inkrementellt, inte big bang):** bryt ut en sak i taget när filen ändå rörs. `FlowLayout` (rad 75–152) är en självständig widget som kan flyttas till `ui/flow_layout.py` utan risk. `StreamPanel` (rad 158–485) är nästa självklara. `AnnotationCanvas` (rad 47–430) är redan nästan separat – den har eget koordinatsystem och egna tester.

### 4.3 `train_task.main()` muterar ett `argparse.Namespace`

`main()` lägger till `args.output_path` och `args.started` (rad 372–373, 380) och skickar `args` vidare till åtta hjälpfunktioner. Det tvingar fram `getattr(args, "workers", DEFAULT_WORKERS)` (rad 186, 479) och `getattr(args, "overfitting_guard", "on")` (rad 221, 482) – defensiv kod mot ett objekt som alltid har fälten.

**Förslag:** en `@dataclass TrainArgs` som byggs en gång från `parse_args()`. `getattr`-anropen försvinner och fälten blir typade.

### 4.4 `training_view` hårdkodar exportlayouten

`ui/training_view.py:412`:

```python
self.dataset_service.export_yolo(self.config.export_dir, ratio)
dataset_path = self.config.export_dir / "yolo" / "data.yaml"
```

RF-DETR-grenen (rad 407) använder returvärdet från `export_rfdetr`. Samma funktion, två sätt att hitta resultatet. Ändras `export_yolo`s layout går YOLO-träningen sönder medan RF-DETR fortsätter fungera.

**Förslag:** låt `export_yolo` returnera `data.yaml`-sökvägen (den returnerar redan `out_dir`), eller lägg en `dataset_yaml_for(family)` i `DatasetService`.

### 4.5 Migreringar körs vid varje konstruktion

`DatasetStore.__init__` (rad 116–120) kör `_migrate_versions()` och `_migrate_coco()` varje gång butiken skapas. `_migrate_coco` **skriver om hela datasetet på plats** – en destruktiv operation som triggas av att appen startar, utan versionsmarkör och utan att fråga.

Det är rätt gjort i den meningen att den är idempotent (den skriver `dataset.json` sist), men den är också kod som aldrig kan tas bort så länge den ligger i konstruktorn, och den kostar en `json.load` av hela datasetet vid varje start.

**Förslag:** en `schema_version` i `dataset.json` och en explicit migreringskedja som bara körs när versionen är äldre. Då kan gamla migreringar pensioneras.

---

## 5. Verktyg, deprecations och tidszoner

### 5.1 `ruff` är oconfigurerat

`pyproject.toml` har `ruff>=0.6` som dev-beroende men **ingen `[tool.ruff]`-sektion**. Det betyder att bara defaultreglerna (`E4`, `E7`, `E9`, `F`) körs, och de ger i dag:

```
15  F401  unused-import
13  BLE001 blind-except
12  I001  unsorted-imports
 5  PLR0402 manual-from-import
 3  F841  unused-variable
 2  SIM102 collapsible-if
 2  S110  try-except-pass
 1  RUF012 mutable-class-default
 1  PIE807 reimplemented-container-builtin
 1  RUF059 unused-unpacked-variable
Found 55 errors. 33 fixable with --fix
```

Med utökad regeluppsättning (`UP`, `B`, `SIM`, `C4`, `RET`, `ARG`, `PERF`, `PL`, `TRY`, `DTZ`, `PT`, `RUF`) blir det 231, varav 102 är `E501` (lång rad) och 43 `PLC0415` (import utanför toppnivå).

**Förslag:** lägg in en `[tool.ruff]`-sektion med `line-length = 100`, `target-version = "py311"`, och en `[tool.ruff.lint]` som slår på `E`, `F`, `I`, `UP`, `B`, `SIM`, `C4`, `PERF`, `RUF`. Kör `ruff check --fix` en gång (33+ fel försvinner automatiskt), och lägg `E501`/`PLC0415` i `ignore` till en början så att grinden kan slås på direkt i stället för att blockeras av 145 kosmetiska fel.

### 5.2 Ingen CI

`.github/` finns inte. 862 tester tar 270 sekunder och körs bara när någon kommer ihåg. Det är den enskilt största risken i projektet: allt annat i den här rapporten är hanterbart så länge testerna körs, och inget hindrar en regression i dag.

**Förslag:** en GitHub Actions-workflow med `uv sync --group dev`, `ruff check` och `pytest -q`. Lägg `pytest-xdist` till dev-beroendena – sviten är nästan helt oberoende mellan filer och bör gå från 270 s till under 90 s med `-n auto`.

### 5.3 Blandade tidsformat

| Plats | Rad | Format |
| --- | --- | --- |
| `store.py` | 142, 154 | `datetime.now(UTC).isoformat()` |
| `evaluation.py` | 177 | `datetime.now(UTC).isoformat()` |
| `pending.py` | 71 | `time.strftime("%Y-%m-%dT%H:%M:%S")` – **lokal tid, ingen tz** |
| `training_service.py` | 84 | `datetime.now()` – **lokal tid, ingen tz** |
| `training_view.py` | 413 | `datetime.now()` – **lokal tid, ingen tz** |
| `dataset_view.py` | 178 | `datetime.fromtimestamp(...)` – lokal tid |

`pending.py` skriver en ISO-lik sträng **utan** tidszon medan `store.py` skriver en med. Två fångster tagna samma sekund får alltså tidsstämplar som ser likadana ut men betyder olika saker, och `_format_timestamp` i `dataset_view` visar dem sida vid sida.

**Förslag:** `datetime.now(UTC)` överallt där en tidsstämpel sparas, och `datetime.now()` bara där lokal tid faktiskt är poängen (nattfönstret). `ruff`s `DTZ`-regler fångar resten när de slås på.

### 5.4 Funktionslokala importer

43 stycken (`PLC0415`). En del är motiverade och bör behållas – `torch`, `ultralytics` och `rfdetr` tar sekunder att importera och laddas medvetet lazy i `app.py`, `yolo_detector.py` och `rfdetr_detector.py`. Andra är det inte:

- `train_task._write_manifest` (rad 236): `from ...json_io import atomic_write_json` – ingen tung modul.
- `main_window.closeEvent` (rad 237) och `_confirm_unsaved` (rad 119): `QMessageBox` – redan importerad i samma fil på andra ställen.
- `training_view._on_start` (rad 383, och 144): `import importlib.util` – stdlib.
- `source.py:122`: `import time` inuti `_wait_for_next_frame` – anropas per ram.

**Förslag:** flytta de fyra ovan till toppnivå. Låt `torch`/`ultralytics`/`rfdetr` ligga kvar med en `# noqa: PLC0415` och en kommentar om starttiden.

### 5.5 `zip()` utan `strict=`

Fyra ställen: `store.py:312`, `smoothing.py:64`, `metrics.py:153`, `annotation_view.py:654`. I `store.py` är det en riktig risk – `zip(targets, samples)` tystar en längdskillnad som `replace_samples` redan har kollat, men bara indirekt.

**Förslag:** `strict=True` där längderna ska vara lika, `strict=False` där de inte ska.

---

## 6. GUI

Utöver P1.4, P2.7 och 4.2:

- **`_settings_sections()`-protokollet är otypat.** Tre vyer implementerar det (`dataset_view.py:477`, `detection_view.py:689`, `training_view.py:168`) och anropas via `settings_button(self, title, self._settings_sections)` (`dataset_view.py:427`, `detection_view.py:567`, `training_view.py:163`). Det finns ingen basklass eller `Protocol`, så en vy som glömmer metoden får en `AttributeError` först när knappen klickas. En `Protocol` med `_settings_sections() -> list[QWidget]` i `ui/settings_dialog.py` kostar fem rader och ger typkontroll.
- **`_on_open_from_dataset` duck-typar** (`main_window.py:187`): `hasattr(payload, "frames")` skiljer en `PendingCapture` från en ramlista. En `Union[list[StreamFrame], PendingCapture]` med en explicit `isinstance`-kontroll vore läsbarare och säkrare.
- **`FlowLayout`** (`dataset_view.py:75–152`) är motiverad – Qt har ingen inbyggd flödeslayout – men den hör inte i en 1 128-radersfil.
- **`detection_view.py:378`** sätter `background: #222` på "ingen källa"-texten oavsett tema. I ljust läge blir det en svart ruta i en ljus vy.

---

## 7. Dokumentation

### 7.1 `README.md` är en ändringslogg, inte dokumentation

41 847 tecken på 153 rader – i snitt 270 tecken per rad, med de fem längsta raderna på 1 724–3 615 tecken (rad 54–59). Filen beskriver varje funktion med sitt TASK-nummer, sina mätvärden och sin implementationshistoria ("Sju operationer som tidigare blockerade GUI-tråden", "mätt 826 av 870 ms för 200 bilder").

Det är utmärkt underlag – men det är **inte** vad en ny läsare behöver. Det finns ingen innehållsförteckning, ingen "kom igång", och de tre första skärmarna handlar om Backlog och Groma.

**Förslag:** dela i tre:

| Fil | Innehåll |
| --- | --- |
| `README.md` | Kom igång, krav, köra, filer och mappar, tangentbord. Målsättning: under 150 rader. |
| `docs/arkitektur.md` | Lager, moduler, dataflöden, varför valen gjordes. |
| `docs/beteende.md` | De långa styckena om lägen, träning, utvärdering – strukna på TASK-nummer och mätvärden. |

TASK-numren hör i Backlog, inte i README. De är redan spårade där.

### 7.2 `specs.md` beskriver ett system som inte längre finns

Specen säger *"För exporterat dataset ska det framgå versionssiffra, datum, antal bildobjekt"* – datasetversionerna togs bort i TASK-57. Den nämner inte RF-DETR, inte syntetiska variationer, inte utvärdering, inte klassfiltret.

**Förslag:** antingen uppdatera den till nuvarande system, eller flytta den till `docs/historik/specs-2026.md` med en rad om att den är ursprungskravet. Det senare är billigare och mer ärligt – en spec som beskriver ett annat system är värre än ingen spec.

### 7.3 `media/README.md` dokumenterar 2 av 6 filer

Katalogen har `xray_slideshow_{side,top}{,_faster}.mp4` och `xray_val_30x8_{side,top}.mp4`; README beskriver bara de två första.

---

## 8. Testsviten

862 tester på 270 sekunder är en bra grund. Tre saker håller den tillbaka:

1. **Ingen parallellisering.** Testerna är nästan helt oberoende mellan filer (`conftest.py` isolerar loggkatalogen per session och river Qt-objekt per test). `pytest-xdist` med `-n auto` bör ge 3–4×.
2. **Ingen markering av långsamma tester.** Det finns inga `markers` i `pyproject.toml`, så en utvecklare som vill köra en snabb svit har inget att filtrera på.
3. **Fixtures dupliceras i stället för att delas.** `settings` definieras i **16** testfiler, `service` i **10**, `window` i **7**, `view` i **6**. Två av `settings`-fixturerna är bokstavligen identiska:

```python
@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
```

**Förslag:** flytta `settings` och en tom `service` till `conftest.py`; låt de filer som behöver förberett innehåll behålla en egen fixture med ett annat namn (`service_with_samples`). Lägg `pytest-xdist` i dev-gruppen och en `slow`-marker på de tester som startar `MainWindow`.

---

## 9. Prioriterad åtgärdsplan

| # | Åtgärd | Prioritet | Insats | Effekt |
| --- | --- | --- | --- | --- |
| 1 | `[tool.ruff]` i `pyproject.toml` + `ruff check --fix` | P1 | 1 h | Grind på plats, 33 fel försvinner automatiskt |
| 2 | CI-workflow: `ruff` + `pytest` | P1 | 1 h | Regressioner fångas; största risken elimineras |
| 3 | Felhantering i `DatasetStore._load_metadata` | P1 | 30 min | Appen startar med trasig `dataset.json` |
| 4 | En nyckel för nattfönstret | P1 | 1 h | Tar bort en tyst fellägeskälla |
| 5 | `num_objects` räknas i `_save_metadata` | P1 | 30 min | Ett tal, en källa |
| 6 | `ANNOTATION_TAB` + publik `AnnotationView.save()` | P1 | 30 min | Flikordningen blir ändringsbar |
| 7 | Ta bort död kod (P3.1) | P3 | 30 min | 8 symboler mindre att förstå |
| 8 | Ta bort `tests/prototype/` | P3 | 10 min | 6 tester som inte testar produktionen |
| 9 | `runs/` i `.gitignore` + `git rm --cached` | P3 | 10 min | 11 MB mindre i arbetsträdet |
| 10 | `read_manifest()` delas av `model_registry` och `training_history` | P2 | 2 h | Ett manifest, en tolkning |
| 11 | `read_classes()` återanvänds i `train_task` | P2 | 30 min | Klasslistan i manifestet blir rätt |
| 12 | `capture_group()`/`group_images()` i `domain/dataset.py` | P2 | 2 h | Fyra varianter blir en |
| 13 | `_write_sample()` i `store.py` | P2 | 2 h | ~80 rader duplicering bort |
| 14 | Palett i `ui/colors.py` | P2 | 2 h | Tema fungerar i båda lägena |
| 15 | `cuda_device_label()` som enda enhetskälla | P2 | 1 h | Två implementationer blir en |
| 16 | Dela `README.md` i tre filer | P2 | 3 h | Läsbar dokumentation |
| 17 | `pytest-xdist` + delade fixtures | P2 | 2 h | 270 s → under 90 s |
| 18 | Bryt ut `FlowLayout` och `StreamPanel` | P3 | 3 h | Två filer under 900 rader |
| 19 | `TrainArgs`-dataclass i `train_task` | P3 | 2 h | `getattr`-försvaret bort |
| 20 | `schema_version` + explicit migrering | P3 | 3 h | Migreringar kan pensioneras |

**Rekommenderad ordning:** 1–6 först (en dag, och risken i projektet faller mest), sedan 7–9 (en timme, ren städning), sedan 10–15 när respektive modul ändå rörs. 16–20 är bra men inte brådskande.

---

## 10. Vad jag inte föreslår

För att vara tydlig om avgränsningen:

- **Byt inte GUI-ramverk.** PySide6 fungerar, `style.py`/`FormCard` gav konsekvens, och QtCharts kom gratis. Ett byte kostar månader och löser inget av ovanstående.
- **Byt inte datasetformat.** YOLO-formatet läses direkt av både ultralytics och rfdetr, vilket är hela poängen med valet. `export.py`-delningen är den svåraste logiken i projektet och den är korrekt.
- **Gör inte en stor refaktorering av vyerna.** Dela ut en widget i taget när filen ändå rörs. En big bang på 3 500 rader UI-kod utan CI (punkt 2) är den enda åtgärden i den här rapporten som kan göra projektet sämre.
- **Ta inte bort kommentarerna.** De förklarar beslut som inte går att läsa ut ur koden. Det är projektets starkaste tillgång.
