# Jämförelse av applikationsimplementationer (5 brancher)

Detta dokument jämför de fem alternativa implementationerna av **X-ray detector** i repot (en per branch) med avseende på arkitektur, projektstruktur, val av ramverk, funktioner och implementationsdetaljer, med `vscode-qwen38` som referenspunkt.

---

## 1. Snabb överblick av brancherna

| Branch | Helhetsomdöme & profil |
| :--- | :--- |
| **`vscode-qwen38`** | Kompakt basimplementation med unik röntgenspecifik bildförbehandling (`xray_detector/detection/preprocess.py`) och separat modellval per kamera, men har **flera buggar** (trasig storleksändring/flytt av boxar, nytränade modeller hittas inte, ingen train/val-split) och saknar tester. |
| **`opencode-bigpickle`** | **Bäst arkitektur och helhet.** Ren lagerindelad DDD-arkitektur (`domain` / `application` / `infrastructure` / `ui`), äkta stöd för både **YOLO och RF-DETR** (inferens + träning + export), oföränderliga dataset-snapshots utan bildduplicering, `QProcess`-träning, kioskläge, PyInstaller-skript samt enhetstester och UI-smoketester. |
| **`opencode-deepseek-flash`** | **Bäst dataintegritet och robusthet.** Har kraschsäker `pending`-kö på disk vid bildfångst, atomiska filskrivningar (`mkstemp` + `fsync` + `os.replace`), SHA-256-checksummor, par-medveten train/val-split, `QProcess`-träning, global kraschdialog (`sys.excepthook`) och 8 testmoduler. |
| **`vibe-glm53`** | **Bäst på dataset-hantering i GUI.** Har en dedikerad **Dataset-vy** med tumnaglar där man kan granska fångster, radera dåliga par och **dubbelklicka för att öppna och om-annotera** tidigare bilder. Har även val av videofil direkt per kamerapanel och persistenta `QSettings`. |
| **`antigravity`** | **Bäst på hårdvaruoberoende demo & schemaläggning.** Har en inbyggd **TrainingScheduler** (nattfönster + inaktivitetsdetektering via global `QEvent`-filter enligt `specs.md`) och en realistisk syntetisk röntgensimulator (rullband med väskor/metall/batterier). *OBS: Träningsklassen i denna branch tränar dock bara ett dummy-nätverk på slumptensorer.* |

---

## 2. Kritiska buggar i `vscode-qwen38` som är lösta i de andra brancherna

1. **Trasig storleksändring och felaktiga koordinater vid flytt i annoteringsvyn:**
   * I `xray_detector/annotation/annotation_canvas.py` (`RectItem`) sätts endast `ItemIsMovable | ItemIsSelectable`, med en kommentar i `AnnotationCanvas` om att "`QGraphicsRectItem`-standard" ger kant-/hörnhandtag. **Det gör inte Qt** – man kan inte ändra storlek på rektanglar alls, vilket bryter mot kravet i `specs.md`.
   * Ännu värre: när användaren flyttar en `RectItem` uppdaterar Qt `item.pos()`, medan `item.rect()` förblir oförändrad i lokala koordinater. När `AnnotationView._collect` läser `r.rect().left()` och `r.rect().top()` ignoreras `pos()` helt, vilket gör att **alla flyttade rektanglar sparas på sina gamla koordinater**.
   * **Hur andra löser det:** Samtliga fyra andra brancher implementerar 8 explicita greppunkter (4 hörn + 4 kanter) med rätt muspekare (`SizeFDiagCursor` osv.) och uppdaterar antingen `_rect` direkt i scenkoordinater (`opencode-bigpickle`, `antigravity`, `vibe-glm53`) eller använder `self.mapRectToScene(self.rect())` (`opencode-deepseek-flash`).

2. **Nytränade modeller dyker aldrig upp i modellväljaren:**
   * I `xray_detector/training/trainer.py` (`TrainingWorker.run`) döps `best.pt` om *inuti* `runs/<version>/train/weights/model_<version>.pt`, men i `DetectionView._list_models` letar applikationen endast i `models/*.pt`.
   * **Hur andra löser det:** `opencode-bigpickle`, `opencode-deepseek-flash` och `vibe-glm53` kopierar vikterna till `models/` tillsammans med en `training_manifest.json` / `meta.json` (med klassnamn, dataset-version och metrics) och uppdaterar `ModelRegistry` automatiskt när träningen är klar.

3. **Träning körs i samma process (`QThread`) och går inte att avbryta:**
   * `TrainingWorker` i `vscode-qwen38` kör `model.train()` i en `QThread` i huvudprocessen. Det låser GIL, frigör inte detektionsmodellens VRAM, och `stop()` sätter bara `self._stop = True` som Ultralytics aldrig läser.
   * **Hur andra löser det:** `opencode-bigpickle` och `opencode-deepseek-flash` kör träningen i en isolerad **`QProcess`** (`python -m ...`), strömmar stdout/stderr till GUI-loggen i realtid, och kan avbryta träningen direkt (`terminate()` följt av `kill()`-fallback) utan att krascha eller låsa GUI:t.

4. **Ingen train/val-split och dataläckage mellan kamerapar:**
   * I `xray_detector/dataset/yolo_export.py` (`export_yolo`) läggs alla bilder i samma mapp och `data.yaml` pekar både `train` och `val` på `yolo/images` (100 % dataläckage).
   * **Hur andra löser det:** Både `opencode-bigpickle` (`_split_pairs`) och `opencode-deepseek-flash` (`prepare_yolo_dataset`) delar upp datasetet i `train`/`val` (t.ex. 80/20) **grupperat på `pair_id` / `capture_group`**, så att vänster och höger bild från samma fångstögonblick aldrig hamnar på olika sidor om train/val-gränsen.

---

## 3. Arkitektur & Projektstruktur

* **Modern `src/`-layout och paketering (`opencode-bigpickle`, `opencode-deepseek-flash`):**
  * Istället för ett platt paket i roten använder de `src/xray_detector/`, `[project.scripts]` entrypoints och har färdiga byggskript för **PyInstaller** (`scripts/build_exe.ps1` i `opencode-bigpickle`, `launcher.py` i `opencode-deepseek-flash`).
* **Ren lagerarkitektur / Hexagonal DDD (`opencode-bigpickle`):**
  * Tydlig separation mellan:
    * `domain/` (rena dataklasser som `BBox`, `Detection`, `AnnotationBox`, `FramePacket`, `CaptureSnapshot` utan Qt/OpenCV-beroenden)
    * `application/` (`DatasetService`, `ModelRegistry`, `TrainingService`)
    * `infrastructure/` (`dataset_store/`, `detectors/`, `training/`, `video/`)
    * `ui/` (`views/`, `widgets/`, `dialogs/`, `pipeline.py`)
  * Det gör att hela domän- och lagringslogiken kan testas utan GPU eller kameror.
* **Valfria beroendegrupper (`opencode-bigpickle`, `vibe-glm53`):**
  * I `pyproject.toml` i `vscode-qwen38` är tunga CUDA-beroenden hårt tvingande. `opencode-bigpickle` separerar bas-beroenden från `[project.optional-dependencies]` (`ml`, `windows`, `build`) så att tester och UI-utveckling kan köras lättviktigt med `FakeDetector` och `opencv-python-headless`.
* **Testsvit (`opencode-bigpickle`, `opencode-deepseek-flash`, `antigravity`):**
  * `vscode-qwen38` saknar helt tester. `opencode-deepseek-flash` har 8 testfiler och `opencode-bigpickle` har både enhetstester och `pytest-qt` smoketester (`QT_QPA_PLATFORM=offscreen`) som testar hela flödet från syntetisk kamera -> `FakeDetector` -> `CaptureSnapshot` -> `AnnotationView` -> `CocoStore` -> `export_yolo`/`export_rfdetr`.

---

## 4. Ramverk & Modeller (YOLO + RF-DETR)

* **Äkta RF-DETR-stöd (`opencode-bigpickle`, `vibe-glm53`):**
  * I `xray_detector/detection/model_registry.py` i `vscode-qwen38` antas att `ultralytics.YOLO("rfdetr-l.pt")` kan hantera RF-DETR.
  * `opencode-bigpickle` har dedikerade adaptrar för Roboflows `rfdetr`-bibliotek (`RFDETRBase` / `RFDETRLarge`) för **både inferens** (`rfdetr_detector.py`), **träning** (`rfdetr_train.py`, som dessutom inspekterar `inspect.signature(model.train)` för versionskompatibilitet) och **datasetexport** (`rfdetr_export.py`, som exporterar RF-DETR:s förväntade `train/` + `valid/` + `test/` med `_annotations.coco.json`).
* **Enhetsidentifiering på Windows med `pygrabber` (`opencode-bigpickle`):**
  * Använder `pygrabber.dshow_graph.FilterGraph` på Windows för att visa de faktiska namnen på inkopplade UVC-kort i inställningsdialogen istället för bara `0` och `1`.

---

## 5. Funktioner & UX

1. **Dataset-utforskare och om-annotering (`vibe-glm53`):**
   * `vibe-glm53` har en fjärde flik, **Dataset**, som visar alla sparade fångstpar som bildtumnaglar med objekträknare. Man kan markera och ta bort felaktiga fångster eller **dubbelklicka på ett tidigare bildpar för att öppna det i annoteringsvyn igen och justera boxarna**. I `vscode-qwen38` är sparade annoteringar en återvändsgränd i GUI:t.
2. **Flexibla videokällor för test och utveckling (`opencode-bigpickle`, `vibe-glm53`, `antigravity`):**
   * `vscode-qwen38` kan bara öppna heltalsindex (`0`, `1`).
   * `opencode-bigpickle` stödjer `device`, `file` (med loopning) och `test_pattern` per kamera.
   * `vibe-glm53` låter användaren välja videokälla eller öppna en `.mp4`/`.avi`-fil direkt i verktygsfältet ovanför respektive videoström.
   * `antigravity` genererar en syntetisk dual-energy röntgenström (väskor med metallföremål och batterier på ett rullband) när fysiska UVC-kort saknas.
3. **Träningsschemaläggare för nattetid och inaktivitet (`antigravity`):**
   * I `specs.md` nämns *"träning endast nattetid eller under inaktivitet"*. `antigravity` är den enda branchen som faktiskt har implementerat detta: en `ActivityFilter` (`QObject` installerad på `QApplication`) lyssnar på mus- och tangentbordsaktivitet och en `TrainingScheduler` kan köa träningsjobb till antingen ett nattfönster (t.ex. `23:00–05:00`) eller efter $N$ minuters inaktivitet.
4. **Riktigt Kioskläge & Inställningsdialog (`opencode-bigpickle`, `opencode-deepseek-flash`):**
   * I `config.py` i `vscode-qwen38` finns `kiosk: bool = False`, men fältet används aldrig i `app.py`.
   * `opencode-bigpickle` och `opencode-deepseek-flash` har fullt kioskläge (`--kiosk`, döljer menyer/statusrad, valfri döljning av muspekare med `BlankCursor` och konfigurerbart utbrytningskommando `Ctrl+Shift+Q`) samt en komplett grafisk **Inställningsdialog** (`Ctrl+,`) som sparar användarinställningar i `%APPDATA%`.
5. **Bättre Annoterings-UX (`opencode-bigpickle`, `opencode-deepseek-flash`):**
   * Zoom med mushjul (`Ctrl+rull`), panorering med mittenmusknapp, skaloberoende (kosmetiska) linjer och handtag så att boxar är lika lätta att ta tag i oavsett zoomnivå, varning vid osparade ändringar om man byter vy, samt fråga om man vill spara som **negativt exempel** om man klickar Spara utan några inritade boxar.

---

## 6. Viktiga implementationsdetaljer under huven

* **Oföränderliga versions-snapshots utan bildduplicering (`opencode-bigpickle`):**
  * I `vscode-qwen38` (`DatasetManager`) skrivs `annotations.json` bara över med `version += 1` utan att man kan träna på eller exportera en specifik tidigare version.
  * I `opencode-bigpickle` sparas alla bilder i en gemensam `images/`-mapp medan varje sparning skapar en oföränderlig `versions/v000001.json`, `v000002.json` osv. med SHA-256-hash (`coco_sha256`). I både export- och träningsläget kan man välja exakt vilken historisk datasetversion man vill använda, utan att bildfilerna dupliceras på disk för varje version.
* **Kraschsäker `pending`-kö på disk vid bildfångst (`opencode-deepseek-flash`):**
  * Så fort användaren trycker på *Fånga* sparas råbilderna och detektionerna omedelbart till `data/pending/<group_id>/` på disk innan annoteringsvyn öppnas. Om datorn eller applikationen kraschar under annoteringen förloras inte de fångade bilderna, och de rensas från `pending/` först när annoteringen har committats atomiskt till datasetet.
* **Atomiska filskrivningar (`opencode-bigpickle`, `opencode-deepseek-flash`):**
  * Skriver aldrig direkt till `annotations.json` med `Path.write_text` (som i `coco.py` i `vscode-qwen38`, vilket korrumperar hela datasetet vid strömavbrott), utan skriver till en temporär fil i samma katalog och byter ut filen atomiskt med `os.replace()`.
* **Sekvensnummer (`FramePacket.sequence`) och lås-fria frame-buffertar (`opencode-bigpickle`):**
  * Taggar varje bildruta med ett monotont ökande sekvensnummer i `FrameBuffer` så att inferens-tråden aldrig kör detektion på samma bildruta två gånger och `VideoPanel` aldrig ritar äldre detektioner ovanpå nyare bildrutor.
* **Låg latens på UVC-kort (`antigravity`, `opencode-deepseek-flash`):**
  * Sätter `cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)` på OpenCV:s `VideoCapture` så att man inte får eftersläpande bildrutor från drivrutinens interna buffert, samt hanterar fallback mellan `CAP_ANY`, `CAP_MSMF` och `CAP_DSHOW` med kort fördröjning så att Windows-drivrutinen hinner släppa UVC-enheten vid omstart.
* **Frigöring av GPU-VRAM vid paus (`opencode-bigpickle`, `antigravity`):**
  * När detektionen pausas inför träning frigörs detektionsmodellen och `torch.cuda.empty_cache()` anropas så att träningsprocessen får tillgång till hela grafikkortets minne.

---

## 7. Vad `vscode-qwen38` faktiskt gör *bättre* (och som bör behållas)

Trots bristerna ovan har `vscode-qwen38` **tre detaljer** som de andra brancherna saknar:

1. **Röntgenspecifik bildförbehandling (`xray_detector/detection/preprocess.py`):**
   * Ingen av de andra fyra brancherna har CLAHE-kontrastförstärkning (i LAB-färgrymd som bevarar pseudofärger från dual-energy-röntgen) eller invertering av röntgenbilder innan inferens.
2. **Separata modeller per videoström (`DetectionConfig` & `DetectionView`):**
   * Om de två UVC-strömmarna visar olika vyer (t.ex. ovanifrån vs. från sidan, eller hög- vs. lågenergi) tillåter `vscode-qwen38` att man väljer olika modeller (`model_left` och `model_right`) för ström 1 och ström 2. De andra brancherna använder samma modellinstans för båda strömmarna.
3. **Visuell återanslutningsknapp direkt i videopanelen (`StreamLabel`):**
   * Den inbyggda status-overlayen med "Ansluter… (försök X/3)" och knappen "Försök igen" direkt i respektive kameravy är väldigt tydlig för operatören om ett USB3-kort tappar kontakten.

---

## 8. Rekommendation

Om målet är att konsolidera till en optimal kodbas är **`opencode-bigpickle`** den klart bästa grunden att utgå ifrån, kompletterad med:
1. **Röntgenförbehandlingen (CLAHE/invert)** och **separat modellval per ström** från `vscode-qwen38`,
2. **Dataset-utforskaren (med tumnaglar och om-annotering)** från `vibe-glm53`,
3. **`pending`-diskkön** från `opencode-deepseek-flash`, samt
4. **Natt-/inaktivitetsschemaläggaren (`TrainingScheduler`)** från `antigravity`.
