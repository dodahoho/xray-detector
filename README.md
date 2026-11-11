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

- **Detektion** (default): två videoströmmar i split screen (UVC-kort eller videofil), detektion med valbar modell (YOLO26/RF-DETR), "Fånga bilder" sparar aktuella rutor och öppnar annoteringsläget. Källväljaren visar enheternas riktiga namn, så ett capture-kort och en virtuell kamera går att skilja på. Videofiler spelas upp i videons egen bildfrekvens; ramen skickas till visningen innan detektionen körs, så overlayn ligger en ram efter bilden men uppspelningen håller jämn takt. Detektionerna jämnas ut mellan ramar (EMA + hysteres) så overlayn inte fladdrar. I den övre raden visas appens GPU-, VRAM-, CPU- och RAM-användning som staplar, uppdaterade varje sekund; CPU visas som andel av maskinens kärnor och GPU/VRAM visar `n/a` utan CUDA. Knappen längst till höger i samma rad slår av och på objektdetektionen och visar vad ett klick gör: "Detektion av" när detektionen är igång, "Detektion på" när den är av. Overlayn rensas och detektorn kopplas bort från strömmarna, men modellen ligger kvar i minnet så den går snabbt att slå på igen. Läget gäller till nästa start.
- **Dataset**: bilderna visas grupperade per fångst med rubrik som visar när fångsten gjordes (`YYYY-MM-DD HH:MM:SS`). Ett klick markerar hela fångsten (paret) och "Ta bort markerade" tar bort alla bilder i den; knappen visar antal markerade bilder.
- **Annotation**: rita/redigera rektanglar, välj eller skriv in klass, spara till COCO-datasetet.
- **Träning**: träna basmodell på vald datasetversion; detektion pausas under träning. Export av dataset till COCO/YOLO med manifest (version, datum, antal objekt). Träningsschemat – nattfönster och inaktivitet innan träning – ställs in i träningsvyns inställningar.

## Inställningar

Inställningsfliken håller applikationens globala inställningar, det vill säga sådant som inte hör till någon av de andra flikarna. I dag är det temat.

Varje vy har dessutom en **Vyns inställningar**-knapp högst upp till höger, med ett kugghjul framför texten. Den öppnar de inställningar som hör till vyn; i dag är det bara träningsvyn som har några (träningsschemat med nattfönster och inaktivitet). En vy utan egna inställningar har kvar knappen men avstängd, så placeringen är densamma oavsett vilken flik som är öppen.

Ändringar sparas direkt, och **Stäng** (eller Esc) lämnar allt orört. Nycklarna i `settings.ini` är oförändrade (`ui/theme`, `training/night_start_hour`, `training/night_end_hour`, `training/inactivity_minutes`), så sparade val fortsätter att gälla.

## Tidskrävande operationer

Fem operationer som tidigare blockerade GUI-tråden körs i en arbetstråd och visar en gemensam upptagenindikator (`xray_detector/ui/busy_indicator.py`) som läggs över vyn: modellbyte i detektionsvyn, omladdning av bildlistan i datasetvyn, export till COCO/YOLO, sparning av annoteringar och enhetskontrollen vid start. Indikatorn tänds först efter 150 ms, så en operation som hinner klart ändå inte ger en blinkning.

## Tangentbord

Allt som går att klicka på går också att nå från tangentbordet. Genvägen syns i etiketten: Qt:s mnemonik ritar en understruken bokstav som ger **Alt+bokstav**, och genvägar som inte är mnemonik visas i stället inom parentes, som `Avbryt (Esc)`. Hjälpmodulen `xray_detector/ui/shortcuts.py` sätter `&` på rätt plats och binder de genvägar som inte är mnemonik.

| Var | Genväg |
| --- | --- |
| Flikar | Alt+D Detektion, Alt+A Annotation, Alt+S Dataset, Alt+T Träning, Alt+I Inställningar |
| Vyns inställningar | Alt+V öppnar den aktiva vyns inställningar; avstängd när vyn inte har några |
| Detektion | Alt+F Fånga bilder, Alt+O Detektion av/på, Alt+G/Alt+N Försök igen (ström 1/2) |
| Annotation | Alt+P Spara till dataset, Alt+B Ta bort markerad, Esc Avbryt, Ctrl++/Ctrl+- lägg till/ta bort klass |
| Dataset | Alt+B Ta bort markerade |
| Träning | Alt+R Starta träning, Esc Avbryt, Alt+E Exportera COCO, Alt+Y Exportera YOLO |
| Övrigt | F11 helskärm, Delete/Backspace tar bort markerad rektangel, Ctrl+hjul zoomar |

Mnemonikbokstäverna är unika inom varje vy och krockar inte med flikraden, som alltid syns. En genväg som hör till en knapp på en flik som inte är aktiv utlöses inte: Qt aktiverar bara genvägar vars widget syns och är påslagen, och Esc/Ctrl++/Ctrl+- binds med `WindowShortcut` på vyn. Av samma skäl går en avstängd flik inte att nå med sin mnemonik.


Modellväljaren är avstängd medan en modell laddas, så två laddningar inte kan köra samtidigt. En misslyckad laddning ger samma felmeddelande som förut och lämnar detektorn avstängd. Mätt på RTX 5080 tar RF-DETR nano 6,3 s att ladda; under hela den tiden animeras snurran och fönstret ritas om. Datasetvyns bildavkodning var den dyra delen av omladdningen (826 av 870 ms för 200 bilder) och ligger därför i arbetstråden, medan widgetbygget (cirka 45 ms) sker i GUI-tråden. Enhetskontrollen, som initierar CUDA-kontexten på cirka 1 s, har ingen indikator: den flyttades bara bort från `MainWindow.__init__` så fönstret kan visas direkt.

Data lagras i `~/.xray-detector/` (dataset, exporter, modeller).
