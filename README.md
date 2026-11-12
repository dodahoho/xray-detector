# X-ray detector

Applikation för detektion av objekt i video med röntgenbilder. Se `specs.md` för krav och `PLAN.md` för implementeringsplan.

## Utveckla

Under utveckling testas olika kodagenter och ramverk. Koden är till största del skapad med AI-verktyg.  

För hålla koll på uppgifter (tasks) används [Backlog.md](https://github.com/MrLesk/Backlog.md)  

För kontinuerlig översikt arkitektur och monitorering av förändringar används [Groma.md](https://github.com/MrLesk/Groma.md)  

Konfiguration för både Backlog och Groma sparas i detta repo. Kommandoverktyg installeras med t ex npm. GUI för browser startas enligt nedan.  
```bash
$ backlog browser
$ groma web
```

## Köra

Kräver Python 3.11+ och [uv](https://docs.astral.sh/uv/). CUDA-rekommenderas för detektion och träning.

```bash
uv sync --extra cu128
uv run python -m xray_detector.app
```

`--extra cu128` hämtar PyTorch med CUDA 12.8-stöd från PyTorch:s eget index (krävs för GPU, inklusive RTX 50-serien/Blackwell). RTX 50-kort fungerar inte med cu126-byggen. 

Utan extra installeras CPU-bygget av PyTorch och appen körs på CPU – detektionsvyns enhetslabel visar då "Enhet: CPU (CUDA ej tillgänglig)" i rött, annars "Enhet: CUDA (GPU-namn)" i grönt.

Med RF-DETR-stöd:

```bash
uv sync --extra cu128 --extra rfdetr
```

`rfdetr` är ett valfritt extra. Saknas paketet är RF-DETR-posten avstängd i modellväljaren (både i detektions- och träningsläget) och märkt `(rfdetr ej installerat)`; ett sparat RF-DETR-val faller då tillbaka på en tillgänglig modell i stället för att ge ett felladdningsmeddelande.

RF-DETR finns i storlekarna nano, small, medium och large. Vald storlek styr både vilka vikter detektionen laddar och vilken modell träningen utgår från. På GPU optimeras RF-DETR för inferens med FP16, vilket mätt gav 17,8 → 9,2 ms per ram med rutor inom 0,8 px från den ooptimerade modellen.

Med CUDA begränsas PyTorch och OpenCV till en CPU-tråd. Inferensen körs på GPU, och de små CPU-tensorerna i modellernas för- och efterbearbetning vinner inget på att spridas över alla kärnor: mätt med två strömmar i 30 fps gick RF-DETR small från cirka 2200 % till cirka 100 % CPU med oförändrad bildfrekvens. Utan CUDA lämnas trådinställningarna orörda.

`pygrabber` installeras automatiskt på Windows och ger videokällorna deras riktiga DirectShow-namn. Utan den visas bara index (`UVC 0`, `UVC 1`), vilket gör det omöjligt att se skillnad på ett capture-kort och en virtuell kamera som NVIDIA Broadcast.

## Videokälla

När en UVC-enhet väljs i en strömpanel dyker två listor upp bredvid källväljaren: upplösning och pixelformat. De fylls från enhetens egna DirectShow-kapabiliteter, så bara lägen som enheten faktiskt erbjuder går att välja. Varje panel minns sitt eget val mellan starterna, och **Auto** lämnar tillbaka valet till drivrutinen. Ett byte startar om strömmen med det nya formatet.

Formatet spelar stor roll på USB 2.0-kort. Ett MacroSilicon MS2109-kort ger 1920x1080 i både MJPG och YUY2, men okomprimerad YUY2 kapas av bandbredden: mätt 9,3 fps mot 52,9 fps med MJPG i samma upplösning. Välj MJPG för 1080p, eller en lägre upplösning om kortet inte klarar MJPG. Formatet måste anges när källan öppnas — `cap.set(CAP_PROP_FOURCC)` efter öppning ignoreras av DSHOW-backend.

## Lägen

- **Detektion** (default): två videoströmmar i split screen (UVC-kort eller videofil), detektion med valbar modell (YOLO26/RF-DETR), "Fånga bilder" sparar aktuella rutor och öppnar annoteringsläget. Källväljaren visar enheternas riktiga namn, så ett capture-kort och en virtuell kamera går att skilja på. Raden ovanför bilden visar bara strömmens bildfrekvens i fps; källans namn står i källväljaren i stället för i raden. Videofiler spelas upp i videons egen bildfrekvens; ramen skickas till visningen innan detektionen körs, så overlayn ligger en ram efter bilden men uppspelningen håller jämn takt. Detektionerna jämnas ut mellan ramar (EMA + hysteres) så overlayn inte fladdrar. I den övre raden visas appens GPU-, VRAM-, CPU- och RAM-användning som staplar, uppdaterade varje sekund; CPU visas som andel av maskinens kärnor och GPU/VRAM visar `n/a` utan CUDA. Knappen längst till höger i samma rad slår av och på objektdetektionen och visar vad ett klick gör: "Detektion av" när detektionen är igång, "Detektion på" när den är av. Overlayn rensas och detektorn kopplas bort från strömmarna, men modellen ligger kvar i minnet så den går snabbt att slå på igen. Läget gäller till nästa start.
- **Dataset**: bilderna grupperas i en sektion per datum, med datumet som rubrik. Inom sektionen är varje fångst ett kort med fångstens tid, antal bilder och objekt samt bildparet; korten läggs efter varandra på samma rad och radbryts när raden är full. Det nyaste datumet listas överst; i datasetvyns inställningar byts ordningen till äldst först, och osparade fångster följer samma ordning. Osparade fångster från pending-kön ligger i en egen sektion överst, tydligt åtskilda från de sparade. Ett klick markerar hela fångsten (paret) och "Ta bort markerade" tar bort alla bilder i den; knappen visar antal markerade bilder. "Exportera COCO" och "Exportera YOLO" skriver datasetet till `exports/` med manifest (format, datum, antal objekt).
- **Annotation**: rita/redigera rektanglar, välj eller skriv in klass, spara till COCO-datasetet. Klasslistan är datasetets egna klasser: första gången vyn öppnas fylls den med vald modells klasser, och klasser du lägger till eller tar bort skrivs direkt till datasetet. En klass som redan används av sparade annoteringar kan inte tas bort. Vyn öppnas från Detektion ("Fånga bilder") eller Dataset (dubbelklick på en fångst), och både "Spara till dataset" och "Avbryt" tar dig tillbaka till fliken du kom från.
- **Träning**: träna basmodell på datasetet; detektion pausas under träning. Starten exporterar datasetet i den familj modellen tillhör. Träningsschemat – nattfönster och inaktivitet innan träning – ställs in i träningsvyns inställningar.

Träningsvyn visar en progressbar med epok X/Y och de aktuella värdena (train-loss, val-loss, mAP50, mAP50-95, precision och recall) medan träningen körs. Värdena kommer från träningsprocessen som ett strukturerat event per epok, inte från fri text: processen läser ultralytics `results.csv` respektive RF-DETR:s `metrics.csv` och skriver en `EPOCH {json}`-rad på stdout som workern lyfter ut till en egen signal. Loggen under grafen visar fortfarande processens utmatning; en rad som skrivs i flera delar buffras tills radbrytningen kommer och blir en loggrad. RF-DETR skriver en rad per loggning, så train- och valvärdena för samma epok slås ihop innan eventet skickas.

Ovanför loggen ritas två grafer, en för train- och val-loss och en för mAP50 och mAP50-95, med epok på x-axeln. De fylls på med ett epokevent i taget och behåller sina punkter när träningen avbryts, så en avbruten körning går att läsa av efteråt. Loss och mAP har olika skalor och får därför var sin y-axel. Grafen använder QtCharts som följer med PySide6, så ingen ny dependency behövs. En körning med en enda epok ger en punkt; axlarna spänner då över ett minsta intervall och punkten ritas som en markör, annars hade grafen sett tom ut.

**Avbryt vid överträning** är på som default och stängs av i träningsvyn. Vakten jämför valvärdet (mAP50-95, annars mAP50, annars val-loss) med train-loss: den larmar först när valvärdet stått still i tio epoker *och* train-loss samtidigt fortsatt sjunka. En kurva som bara planar ut räknas alltså som avstannad, inte som övertränad. Avbrottet sker i träningsprocessen, inte genom att GUI:t dödar den: YOLO stoppas i sin `on_fit_epoch_end`-callback (`trainer.stop`) och får samma patience som reserv i ultralytics egen early stopping, och RF-DETR använder paketets `early_stopping` med samma patience eftersom det saknar publik callback-krok. Bästa vikterna och manifestet skrivs om efter varje epok, så de finns kvar även när träningen avbryts. Orsaken syns i träningsvyn och i statusraden, och sparas som `abort_reason` i manifestet.

## Inställningar

Inställningsfliken håller applikationens globala inställningar, det vill säga sådant som inte hör till någon av de andra flikarna. I dag är det temat.

Varje vy har dessutom en **Inställningar**-knapp högst upp till höger, med ett kugghjul framför texten. Den öppnar de inställningar som hör till vyn: detektionsvyn har klassfiltret, datasetvyn sorteringen och träningsvyn träningsschemat med nattfönster och inaktivitet. En vy utan egna inställningar har kvar knappen men avstängd, så placeringen är densamma oavsett vilken flik som är öppen.

Detektionsvyns inställningar håller **klassfiltret**: en kryssruta per klass som vald modell kan detektera. Alla klasser är valda från början, så beteendet är oförändrat tills något klickas bort. Klasslistan följer modellen och byggs om när en annan modell laddas. Valen sparas per modell under `detection/classes_off/<modellnyckel>`, och det är bara bortvalen som sparas – en klass som tillkommer i en modell är därför vald från början. Bortvalda klasser filtreras bort i detektorn innan overlayn ritas. Väljs alla klasser bort kopplas detektorn bort helt: sektionen visar "Inga klasser valda – ingen detektion körs", statusraden säger samma sak och ingen detektion körs förrän minst en klass är vald igen.

Ändringar sparas direkt, och **Stäng** (eller Esc) lämnar allt orört. Nycklarna i `settings.ini` är oförändrade (`ui/theme`, `training/night_start_hour`, `training/night_end_hour`, `training/inactivity_minutes`), så sparade val fortsätter att gälla.

## GUI-element

Knapparna har samma höjd (32 px) i alla vyer. Måtten ligger i `xray_detector/ui/style.py` i stället för i varje vy, och vyerna skapar knappar med `button()`; en ändring av `BUTTON_HEIGHT` slår då igenom överallt. Huvudåtgärden i en vy markeras med `primary=True`, vilket ger fet stil i stället för en högre knapp, så raden håller sig rak: **Fånga bilder**, **Spara till dataset** och **Starta träning**. Klassknapparna `+` och `−` i annoteringsvyn är 36 px breda (`ICON_BUTTON_WIDTH`).

Ett element som behöver egna mått skickar `height=` eller `width=` till `button()`, eller använder `apply_metrics()` på en widget som Qt har skapat, som dialogens **Stäng**-knapp. `height=None` lämnar höjden till Qt. `tests/test_style.py` mäter att alla knappar i alla vyer har samma höjd, så en ny knapp som sätter en egen höjd fastnar i testet.

## Tidskrävande operationer

Fem operationer som tidigare blockerade GUI-tråden körs i en arbetstråd och visar en gemensam upptagenindikator (`xray_detector/ui/busy_indicator.py`) som läggs över vyn: modellbyte i detektionsvyn, omladdning av bildlistan och export till COCO/YOLO i datasetvyn, sparning av annoteringar och enhetskontrollen vid start. Indikatorn tänds först efter 150 ms, så en operation som hinner klart ändå inte ger en blinkning.

## Tangentbord

Allt som går att klicka på går också att nå från tangentbordet. Genvägen syns i etiketten: Qt:s mnemonik ritar en understruken bokstav som ger **Alt+bokstav**, och genvägar som inte är mnemonik visas i stället inom parentes, som `Avbryt (Esc)`. Hjälpmodulen `xray_detector/ui/shortcuts.py` sätter `&` på rätt plats och binder de genvägar som inte är mnemonik.

| Var | Genväg |
| --- | --- |
| Flikar | Alt+D Detektion, Alt+A Annotation, Alt+S Dataset, Alt+T Träning, Alt+L Inställningar |
| Vyernas inställningar | Alt+I öppnar den aktiva vyns inställningar; avstängd när vyn inte har några |
| Detektion | Alt+F Fånga bilder, Alt+O Detektion av/på, Alt+G/Alt+N Försök igen (ström 1/2) |
| Annotation | Alt+P Spara till dataset, Alt+B Ta bort markerad, Esc Avbryt, Ctrl++/Ctrl+- lägg till/ta bort klass |
| Dataset | Alt+B Ta bort markerade, Alt+E Exportera COCO, Alt+Y Exportera YOLO |
| Träning | Alt+R Starta träning, Esc Avbryt |
| Övrigt | F11 helskärm, Delete/Backspace tar bort markerad rektangel, Ctrl+hjul zoomar |

Mnemonikbokstäverna är unika inom varje vy och krockar inte med flikraden, som alltid syns. Fliken Inställningar använder därför Alt+L i stället för Alt+I: inställningarna för vyn man arbetar i nås oftare än de globala, så Alt+I hör till vyernas inställningsknappar. En genväg som hör till en knapp på en flik som inte är aktiv utlöses inte: Qt aktiverar bara genvägar vars widget syns och är påslagen, och Esc/Ctrl++/Ctrl+- binds med `WindowShortcut` på vyn. Av samma skäl går en avstängd flik inte att nå med sin mnemonik.


Modellväljaren är avstängd medan en modell laddas, så två laddningar inte kan köra samtidigt. En misslyckad laddning ger samma felmeddelande som förut och lämnar detektorn avstängd. Mätt på RTX 5080 tar RF-DETR nano 6,3 s att ladda; under hela den tiden animeras snurran och fönstret ritas om. Datasetvyns bildavkodning var den dyra delen av omladdningen (826 av 870 ms för 200 bilder) och ligger därför i arbetstråden, medan widgetbygget (cirka 45 ms) sker i GUI-tråden. Enhetskontrollen, som initierar CUDA-kontexten på cirka 1 s, har ingen indikator: den flyttades bara bort från `MainWindow.__init__` så fönstret kan visas direkt.

## Filer och mappar

Dataset, exporter och inställningar ligger under `~/.xray-detector/`. Datasetet är en enda samling: `datasets/dataset.json` (COCO) med bilderna i `datasets/images/`, och exporten hamnar i `exports/yolo/`, `exports/coco/` eller `exports/rfdetr/`. Modellvikterna och loggarna ligger i stället i projektets `models/` respektive `logs/`, som båda skapas vid behov och är gitignorerade:

| Sökväg | Innehåll |
| --- | --- |
| `models/` | Basvikter, till exempel `yolo26n.pt`. Ultralytics laddar ner en saknad vikt hit i stället för till arbetskatalogen. |
| `models/trained/` | Egentränade modeller, en katalog per träningskörning (`<datum>_<tid>`) med `training_manifest.json` och bästa vikterna under `yolo/weights/best.pt` (YOLO) eller `rfdetr/checkpoint_best_total.pth` (RF-DETR). |
| `logs/app.log` | Applikationsloggen: start, statusmeddelanden och ohanterade undantag. |
| `logs/training.log` | Träningsprocessens utmatning, en rubrikrad per körning med tidsstämpel, basmodell och körningskatalog. |

Modellväljaren listar basmodellerna först och därefter varje `training_manifest.json` under `models/trained/`, märkt `Tränad <körning> (<basmodell>)`. Manifestets `family` avgör vilken detektor posten laddas med: `yolo` ger `YoloDetector` och `rfdetr` ger `RfDetrDetector`, som läser snapshoten med `rfdetr.from_checkpoint`. Manifest som skrevs innan fältet fanns saknar `family` och behandlas som `yolo`. Bas- och egentränade vikter ligger i skilda kataloger och skriver därför aldrig över varandra.

Varje körning får en unik katalog och därmed en unik snapshot av bästa vikterna. GUI:t skickar en tidsstämplad katalog; pekar CLI:t på en katalog som redan har ett manifest flyttas den nya körningen till `<namn>_2`, `_3` och så vidare, så en tidigare snapshot aldrig skrivs över. `--output` tolkas alltid som en absolut sökväg, eftersom ultralytics annars lägger relativa `project`-sökvägar under `runs/detect/`. Snapshoten är den faktiskt bästa checkpoints för familjen: `yolo/weights/best.pt` för YOLO och `rfdetr/checkpoint_best_total.pth` för RF-DETR. Medan en RF-DETR-körning pågår eller om den avbryts finns ännu ingen `checkpoint_best_total.pth`, och då används `checkpoint_best_ema.pth` eller `checkpoint_best_regular.pth`; `last_ema.pth` är slutvikterna och väljs aldrig. Manifestet skrivs om efter varje epok och innehåller familj, basmodell, dataset, hyperparametrar, metrics, antal körda epoker, status (`running`, `completed` eller `aborted`), `abort_reason` samt start-, slut- och körtid, så en avbruten körning behåller både bästa hittillsvarande vikter och sitt manifest.

Klassnamnen kommer från modellen, inte från konfigurationen: detektorn läser dem ur vikterna när den laddas (YOLO: `model.names`, RF-DETR: modellens `class_names`) och exponerar dem som `class_names`. En tränad modell visar alltså klasserna den tränades på och en basmodell sina egna, till exempel COCO:s 80. Datasetets klasser ligger i `dataset.json` och är master för annoteringen: modellens klasser fyller bara på listan när datasetet är tomt, och klasser som läggs till eller tas bort i annoteringsvyn skrivs till datasetet. `classes` i `config.yaml` är reservlistan som annoteringsvyn visar innan modellens klasser är kända, och den styr overlayfärgerna. Går klassnamnen inte att läsa ur vikterna misslyckas laddningen med ett tydligt felmeddelande i stället för att overlayn visar klassindex.

Sökvägarna till `models/` och `logs/` räknas ut från paketets placering och inte från arbetskatalogen, så appen hittar dem även när den startas från en annan mapp. Båda går att peka om i `config.yaml`:

```yaml
models_dir: /sökväg/till/models   # relativ sökväg tolkas mot projektroten
logs_dir: /sökväg/till/logs       # relativ sökväg tolkas mot projektroten
```

Loggfilerna roteras vid 1 MB och sparas i fem backupfiler (`app.log.1`–`app.log.5`). Rotationen och formatet delas av alla loggtyper, så en ny loggtyp under `logs/` är bara ett nytt namn i `log_path(logs_dir, namn)` – ingen ny kod för katalog eller rotation behövs.

Tidigare versioner sparade tränade modeller under `~/.xray-detector/models/` och loggarna under `~/.xray-detector/logs/`. De katalogerna skrivs inte längre; flytta i så fall modellerna till `models/trained/` för att få dem i väljaren. Gamla loggar kan flyttas till `logs/` eller tas bort.

Dataset som sparades som `datasets/v1`, `datasets/v2` och så vidare flyttas automatiskt upp till `datasets/` vid start; den nyaste versionen blir då datasetet.
