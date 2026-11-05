# X-ray detector

Applikation för detektion av objekt i video med röntgenbilder. Se `specs.md` för krav och `PLAN.md` för implementeringsplan.

## Köra

Kräver Python 3.11+ och [uv](https://docs.astral.sh/uv/). CUDA-rekommenderas för detektion och träning.

```bash
uv sync --extra cu128
uv run python -m xray_detector.app
```

`--extra cu128` hämtar PyTorch med CUDA 12.8-stöd från PyTorch:s eget index (krävs för GPU, inklusive RTX 50-serien/Blackwell). RTX 50-kort fungerar inte med cu126-byggen. Nyare drivrutin (CUDA 13.x) kan använda `--extra cu130`.

Utan extra installeras CPU-bygget av PyTorch och appen körs på CPU – detektionsvyns enhetslabel visar då "Enhet: CPU (CUDA ej tillgänglig)" i rött, annars "Enhet: CUDA (GPU-namn)" i grönt.

Med RF-DETR-stöd:

```bash
uv sync --extra cu128 --extra rfdetr
```

## Lägen

- **Detektion** (default): två videoströmmar i split screen (UVC-kort eller videofil), detektion med valbar modell (YOLO26/RF-DETR), "Fånga bilder" sparar aktuella rutor och öppnar annoteringsläget.
- **Annotation**: rita/redigera rektanglar, välj eller skriv in klass, spara till COCO-datasetet.
- **Träning**: träna basmodell på vald datasetversion; detektion pausas under träning. Export av dataset till COCO/YOLO med manifest (version, datum, antal objekt).

Data lagras i `~/.xray-detector/` (dataset, exporter, modeller).
