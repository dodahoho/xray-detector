# X-ray detector

Applikation för detektion av objekt i video med röntgenbilder. Se `specs.md` för krav och `PLAN.md` för implementeringsplan.

## Köra

Kräver Python 3.11+ och [uv](https://docs.astral.sh/uv/). CUDA-rekommenderas för detektion och träning.

```bash
uv sync --extra cu126
uv run python -m xray_detector.app
```

`--extra cu126` hämtar PyTorch med CUDA-stöd från PyTorch:s eget index (krävs för GPU). Utan extra installeras CPU-bygget av PyTorch och appen körs på CPU – statusraden visar då "CPU (CUDA ej tillgänglig)" när en modell laddas.

Med RF-DETR-stöd:

```bash
uv sync --extra cu126 --extra rfdetr
```

## Lägen

- **Detektion** (default): två videoströmmar i split screen (UVC-kort eller videofil), detektion med valbar modell (YOLO26/RF-DETR), "Fånga bilder" sparar aktuella rutor och öppnar annoteringsläget.
- **Annotation**: rita/redigera rektanglar, välj eller skriv in klass, spara till COCO-datasetet.
- **Träning**: träna basmodell på vald datasetversion; detektion pausas under träning. Export av dataset till COCO/YOLO med manifest (version, datum, antal objekt).

Data lagras i `~/.xray-detector/` (dataset, exporter, modeller).
