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

## Lägen

- **Detektion** (default): två videoströmmar i split screen (UVC-kort eller videofil), detektion med valbar modell (YOLO26/RF-DETR), "Fånga bilder" sparar aktuella rutor och öppnar annoteringsläget. Videofiler spelas upp i videons egen bildfrekvens; ramen skickas till visningen innan detektionen körs, så overlayn ligger en ram efter bilden men uppspelningen håller jämn takt. Detektionerna jämnas ut mellan ramar (EMA + hysteres) så overlayn inte fladdrar. I den övre raden visas appens GPU-, VRAM-, CPU- och RAM-användning som staplar, uppdaterade varje sekund; CPU visas som andel av maskinens kärnor och GPU/VRAM visar `n/a` utan CUDA.
- **Dataset**: bilderna visas grupperade per fångst med rubrik som visar när fångsten gjordes (`YYYY-MM-DD HH:MM:SS`). Ett klick markerar hela fångsten (paret) och "Ta bort markerade" tar bort alla bilder i den; knappen visar antal markerade bilder.
- **Annotation**: rita/redigera rektanglar, välj eller skriv in klass, spara till COCO-datasetet.
- **Träning**: träna basmodell på vald datasetversion; detektion pausas under träning. Export av dataset till COCO/YOLO med manifest (version, datum, antal objekt).

Data lagras i `~/.xray-detector/` (dataset, exporter, modeller).
