# Arkitektur

Hur koden är uppdelad, hur arbetet flyttas bort från GUI-tråden och var filerna
hamnar. Beteendet i vyerna beskrivs i [beteende.md](beteende.md).

## Innehåll

- [Kodstruktur](#kodstruktur)
- [Trådar och tidskrävande operationer](#trådar-och-tidskrävande-operationer)
- [Modeller](#modeller)
- [Filer och mappar](#filer-och-mappar)
- [Tester och CI](#tester-och-ci)

## Kodstruktur

Koden ligger i fyra lager under `xray_detector/`, och pilen betyder "får importera":

```
ui ──▶ application ──▶ infrastructure ──▶ domain
 └───────────────────────────────────────────▶
```

- **`domain/`** – rena datatyper och regler: `Detection`, `AppConfig`, `TrainConfig`, grupperingen i `group_images` och variationernas gränser (`MIN_SCALE`, `MAX_SCALE`, `describe`). Importerar inget annat lager och har inga tunga beroenden.
- **`infrastructure/`** – implementationerna: datasetlagringen (`DatasetStore`), detektorerna, träningsprocessen, videokällorna (`CameraService`) och loggningen. Importerar `domain`, aldrig `application`.
- **`application/`** – det som samordnar `infrastructure`: `TrainingService` (kö och schemaläggning), `ModelRegistry` (modellval och detektorskapande), `BackgroundTask`, konfiginläsningen och utvärderingen. Lagret är en tunn fasad över `infrastructure`, inte en egen domänmodell: ren vidarebefordran hör hemma i `infrastructure` i stället för i en tjänsteklass. Importerar `domain` och `infrastructure`.
- **`ui/`** – vyerna. Importerar `application` för samordning och `domain` för typer. Vyerna använder `DatasetStore` och `CameraService` direkt, eftersom de tidigare tjänsteklasserna bara delegerade till dem.

Utanför paketet ligger `scripts/`, som innehåller verktyg för att mäta appen i stället för att köra den. De importerar appens moduler men ingår inte i appen och täcks inte av testsviten. `scripts/variation_eval.py` kör en matris av träningar med och utan syntetiska bildvariationer och skrev [rapporten om bildvariationer](rapporter/bildvariationer.md) för YOLO26 medium och [samma utvärdering för RF-DETR large dvxray](rapporter/bildvariationer-rfdetr.md); den rör aldrig användarens dataset, eftersom indata kopieras till en arbetskatalog först.

Regeln som håller lagren åtskilda är att **`infrastructure` aldrig importerar `application`**. Loggfångsten låg tidigare i `application/app_config.py` och gjorde beroendet cykliskt; den ligger nu i `infrastructure/logging.py`. Tunga och valfria beroenden (`torch`, `ultralytics`, `rfdetr`, `pygrabber`) importeras först när de används och märks med `# noqa: PLC0415`, så `ruff check` håller reda på vilka lokala importer som är medvetna.

## Trådar och tidskrävande operationer

Åtta operationer som tidigare blockerade GUI-tråden körs i en arbetstråd och visar en gemensam upptagenindikator (`xray_detector/ui/busy_indicator.py`) som läggs över vyn: modellbyte i detektionsvyn, omladdning av bildlistan, export till COCO/YOLO, import av ett YOLO-dataset och utökning med bildvariationer i datasetvyn, sparning av annoteringar, enhetskontrollen vid start och utvärderingen i träningsvyn. Indikatorn tänds först efter 150 ms, så en operation som hinner klart ändå inte ger en blinkning.

Modellväljaren är avstängd medan en modell laddas, så två laddningar inte kan köra samtidigt. En misslyckad laddning ger samma felmeddelande som förut och lämnar detektorn avstängd. Mätt på RTX 5080 tar RF-DETR nano 6,3 s att ladda; under hela den tiden animeras snurran och fönstret ritas om. Datasetvyns bildavkodning var den dyra delen av omladdningen (826 av 870 ms för 200 bilder) och ligger därför i arbetstråden, medan widgetbygget (cirka 45 ms) sker i GUI-tråden. Enhetskontrollen, som initierar CUDA-kontexten på cirka 1 s, har ingen indikator: den flyttades bara bort från `MainWindow.__init__` så fönstret kan visas direkt.

## Modeller

RF-DETR finns i storlekarna nano, small, medium och large. Vald storlek styr både vilka vikter detektionen laddar och vilken modell träningen utgår från. På GPU optimeras RF-DETR för inferens med FP16, vilket mätt gav 17,8 → 9,2 ms per ram med rutor inom 0,8 px från den ooptimerade modellen.

Med CUDA begränsas PyTorch och OpenCV till en CPU-tråd. Inferensen körs på GPU, och de små CPU-tensorerna i modellernas för- och efterbearbetning vinner inget på att spridas över alla kärnor: mätt med två strömmar i 30 fps gick RF-DETR small från cirka 2200 % till cirka 100 % CPU med oförändrad bildfrekvens. Utan CUDA lämnas trådinställningarna orörda.

## Filer och mappar

Dataset, exporter och inställningar ligger under `~/.xray-detector/`. Datasetet är en enda samling i YOLO-format: `datasets/data.yaml` med klasserna, bilderna i `datasets/images/`, annoteringarna i `datasets/labels/` (en `.txt` per bild) och metadata som bild-id, fångstgrupp och fångsttid i `datasets/dataset.json`. En syntetisk bild har `synthetic`, `source` (originalets bild-id) och `variation` (en lista med typ och styrka per variation i bilden) i samma fil, så den går att skilja från originalen och spåra tillbaka till bilden den skapades från. Exporten hamnar i `exports/yolo/`, `exports/coco/` eller `exports/rfdetr/`. YOLO-exporten kopierar bilderna, labels och `dataset.json` och skriver `train.txt` och `val.txt` med sökvägar till kopiorna, så exporten är en egen samling som kan flyttas till en annan maskin och importeras tillbaka. `dataset.json` följer med eftersom YOLO-formatet saknar bildpar: filen bär bild-id, fångstgrupp, fångsttid och den syntetiska bildens ursprung, så importen kan återställa datasetet som det var före exporten. Ett externt YOLO-dataset utan `dataset.json` importeras ändå, men då blir varje bild ett eget bildpar. Ett dataset som sparades i det tidigare COCO-formatet konverteras automatiskt till YOLO när appen startar. Modellvikterna och loggarna ligger i stället i projektets `models/` respektive `logs/`, som båda skapas vid behov och är gitignorerade:

| Sökväg | Innehåll |
| --- | --- |
| `models/` | Basvikter, till exempel `yolo26n.pt`. Ultralytics laddar ner en saknad vikt hit i stället för till arbetskatalogen. |
| `models/models.json` | Modellistan som väljarna bygger på: nyckel, visningsnamn, familj och viktfil per modell. Skapas först när listan ändras i modelldialogen; utan filen gäller standardmodellerna. |
| `models/trained/` | Egentränade modeller, en katalog per träningskörning (`<datum>_<tid>`) med `training_manifest.json`, bästa vikterna under `yolo/weights/best.pt` (YOLO) eller `rfdetr/checkpoint_best_total.pth` (RF-DETR) och `evaluation.json` när körningen är utvärderad. |
| `logs/app.log` | Applikationsloggen: start, statusmeddelanden, ohanterade undantag och tredjepartens varningar. |
| `logs/training.log` | Träningsprocessens utmatning, en rubrikrad per körning med körnings-id, tidsstämpel, basmodell och körningskatalog. |

Modellväljaren listar basmodellerna först och därefter varje `training_manifest.json` under `models/trained/`, märkt med körningens namn: `[basmodell] [datum] [ursprungsbildpar + syntetiska bildpar] bildpar [antal klasser] klasser`, till exempel `YOLO26 large 2026-11-15 13+29 bildpar 4 klasser`. Modelldialogen visar samma poster i samma ordning. Båda talen räknar bildpar: en variation blir ett eget bildpar, så en utökning med två variationer per ursprungspar höjer talet efter `+` med två per par. Basmodellens namn är den modell den första träningen utgick från, så en vidareträning på samma dataset bara byter datum. Manifest som skrevs innan namnet fanns visas som `Tränad <körning> (<basmodell>)`. Manifestets `family` avgör vilken detektor posten laddas med: `yolo` ger `YoloDetector` och `rfdetr` ger `RfDetrDetector`, som läser snapshoten med `rfdetr.from_checkpoint`. Manifest som skrevs innan fältet fanns saknar `family` och behandlas som `yolo`. Bas- och egentränade vikter ligger i skilda kataloger och skriver därför aldrig över varandra.

Varje körning får en unik katalog och därmed en unik snapshot av bästa vikterna. GUI:t skickar en tidsstämplad katalog; pekar CLI:t på en katalog som redan har ett manifest flyttas den nya körningen till `<namn>_2`, `_3` och så vidare, så en tidigare snapshot aldrig skrivs över. `--output` tolkas alltid som en absolut sökväg, eftersom ultralytics annars lägger relativa `project`-sökvägar under `runs/detect/`. Snapshoten är den faktiskt bästa checkpoints för familjen: `yolo/weights/best.pt` för YOLO och `rfdetr/checkpoint_best_total.pth` för RF-DETR. Medan en RF-DETR-körning pågår eller om den avbryts finns ännu ingen `checkpoint_best_total.pth`, och då används `checkpoint_best_ema.pth` eller `checkpoint_best_regular.pth`; `last_ema.pth` är slutvikterna och väljs aldrig. Manifestet skrivs om efter varje epok och innehåller körningens namn, basmodellens namn, familj, basmodell, dataset, hyperparametrar, metrics, antal körda epoker, status (`running`, `completed` eller `aborted`), `abort_reason` samt start-, slut- och körtid, så en avbruten körning behåller både bästa hittillsvarande vikter och sitt manifest. Namnet byggs av träningsvyn, som känner datasetets sammansättning och basmodellens etikett; en körning från CLI:t utan `--name` får ingen namnrad.

Klassnamnen kommer från modellen, inte från konfigurationen: detektorn läser dem ur vikterna när den laddas (YOLO: `model.names`, RF-DETR: modellens `class_names`) och exponerar dem som `class_names`. En tränad modell visar alltså klasserna den tränades på och en basmodell sina egna, till exempel COCO:s 80. Datasetets klasser ligger i `data.yaml` och är master för annoteringen: listan i annoteringsvyn är datasetets kategorier, modellens klasser erbjuds i en fråga när listan är tom, och klasser som läggs till eller tas bort i annoteringsvyn skrivs till datasetet. YOLO lagrar klassen som ett index i klasslistan, så när en klass tas bort skrivs label-filerna om med den nya ordningen och sparade annoteringar behåller sin klass. Klassfärgen hashas ur klassnamnet, så samma klass har samma färg i detektions-, dataset- och annoteringsvyn och mellan appstarter. Går klassnamnen inte att läsa ur vikterna misslyckas laddningen med ett tydligt felmeddelande i stället för att overlayn visar klassindex. Ett klassnamn som sparats som UTF-8 men lästs som latin-1, till exempel `lÃ¶pare` i stället för `löpare`, rättas när det läses ur datasetet eller vikterna och när `data.yaml` skrivs, så dataset, export, träning och klassmärket visar samma tecken (TASK-165).

Sökvägarna till `models/` och `logs/` räknas ut från paketets placering och inte från arbetskatalogen, så appen hittar dem även när den startas från en annan mapp. Båda går att peka om i `config.yaml`, och `logs/` även med miljövariabeln `XRAY_LOGS_DIR` (som testsviten använder för att inte skriva i projektets loggar):

```yaml
models_dir: /sökväg/till/models   # relativ sökväg tolkas mot projektroten
logs_dir: /sökväg/till/logs       # relativ sökväg tolkas mot projektroten
```

Filen tolkas med `yaml.safe_load`, så kommentarer, citattecken och listor fungerar som i vilken YAML-fil som helst. Samma läsare används för datasetets `data.yaml`, så klasslistan i vyn och i träningsmanifestet kan inte gå isär.

Loggfilerna roteras vid 1 MB och sparas i fem backupfiler (`app.log.1`–`app.log.5`). Rotationen och formatet delas av alla loggtyper, så en ny loggtyp under `logs/` är bara ett nytt namn i `log_path(logs_dir, namn)` – ingen ny kod för katalog eller rotation behövs. Varje rad inleds med tidsstämpel och process-id, så rader från appen och från en träningsprocess går att skilja åt: `2026-11-16 21:44:50,600 [20980] INFO xray: ...`.

Apploggen fångar även det som annars bara syntes i konsolen. Python-varningar från torch, transformers och rfdetr loggas under loggern `py.warnings`, och rfdetr:s egna loggrar (`rf-detr`, `rfdetr.*`) leds in i filen i stället för att stanna i stderr. Loggerns namn i raden skiljer tredjepartens rader från appens `xray`-rader. Renodlat brus, som `comtypes` INFO-rader, hålls kvar på WARNING och hamnar därför inte i filen.

Vid start loggar appen vilken `config.yaml` som användes och vilka värden som gäller, datasetets storlek, kamerauppräkningens resultat och varje modelladdning med viktfil, familj, enhet och tidsåtgång. En träningskörning får ett id – körningskatalogens namn – som skrivs både i `app.log` och i `training.log`, så en körning går att följa mellan filerna. Ctrl+C loggas som INFO och stänger appen utan kraschdialog, så en ERROR-rad i loggen alltid är ett verkligt fel.

Tidigare versioner sparade tränade modeller under `~/.xray-detector/models/` och loggarna under `~/.xray-detector/logs/`. De katalogerna skrivs inte längre; flytta i så fall modellerna till `models/trained/` för att få dem i väljaren. Gamla loggar kan flyttas till `logs/` eller tas bort.

## Tester och CI

Testsviten körs med pytest:

```bash
uv run pytest -q
uv run pytest -q -n auto
```

`-n auto` fördelar filerna över alla kärnor med [pytest-xdist](https://pytest-xdist.readthedocs.io/) och tar sviten från cirka 270 s till under 90 s. Markören `slow` är registrerad i `pyproject.toml` för tester som startar `MainWindow`, så `uv run pytest -m "not slow"` kan köra sviten utan dem.

`tests/test_shortcuts.py` skickar sina tangenter genom `press()`, som sätter Qt:s aktiva fönster med `QApplication.setActiveWindow()` innan tangenten går till fönstrets fokuswidget. Genvägar och mnemonik körs bara i det aktiva fönstret, och under `-n auto` kämpar flera processer om skrivbordets förgrund, så `activateWindow()` räcker inte: fönstret kan tappa aktiveringen mitt i ett test (TASK-170).

Vid push och pull request kör GitHub Actions `.github/workflows/ci.yml` `ruff check` och hela sviten med `-n auto` på en Ubuntu-runner. Testerna ritar i Qt utan skärm, så workflowen sätter `QT_QPA_PLATFORM=offscreen` och installerar de systembibliotek PySide6 och OpenCV länkar mot.

Körs sviten med `QT_QPA_PLATFORM=offscreen` på Windows måste Qt hitta ett teckensnitt, annars blir textmåtten fel och märkestesterna fallerar. CI löser det med `fonts-dejavu-core`; lokalt räcker det att köra sviten utan variabeln.
