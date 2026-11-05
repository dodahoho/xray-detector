# Implementeringsplan: X-ray detector

Plan utifrån `specs.md`. Beslut tagna i dialog 2025 (GUI på svenska, YOLO26 medium som default, fullscreen, Python + uv).

## Beslut

| Val | Beslut |
|---|---|
| Språk/ramverk | Python 3.11+ (hanteras med **uv**), PySide6-GUI på **svenska** |
| Körning | Fullscreen vid start (ingen riktig kiosk), Python + uv – .exe eventuellt senare |
| Video | OpenCV; `VideoSource`-abstraktion med `UvcSource` och `FileSource` (videofil för test utan capture cards) |
| Detektion | Ultralytics **YOLO26 medium** som default, modell valbar i GUI; RF-DETR-stöd via samma `Detector`-ABC |
| Klasser | Startlista: `cigaretter`, `cannabis`, `kniv`, `pistol` (utökningsbar via annoteringsläget) |
| Dataset | COCO internt, med versionssiffra/datum/objektantal; YOLO-export via konvertering |
| Träning | Separat process (CUDA), kopplad till datasetversion; detektion pausas under träning |

## Modulstruktur

```
xray_detector/
├── pyproject.toml          # uv-projekt, deps: pyside6, opencv, ultralytics, rfdetr
├── app.py                  # ingång, fullscreen, lägesval
├── ui/
│   ├── main_window.py      # Tabbar: Detektion / Annotation / Träning
│   ├── detection_view.py   # split screen, modellval, fånga-knapp
│   ├── annotation_view.py  # redigerbara rektanglar, klasslista
│   └── training_view.py    # basmodell, dataset, hyperparametrar, progress
├── capture/
│   ├── source.py           # VideoSource-ABC, UvcSource, FileSource
│   └── camera_service.py   # tråd per källa, senaste-frame-queue
├── detection/
│   ├── base.py            # Detector-ABC: load(), detect(frame) -> [Detection]
│   ├── yolo_detector.py   # Ultralytics (YOLO26 n/s/m)
│   ├── rfdetr_detector.py # RF-DETR-familjen
│   └── registry.py        # tillgängliga modeller + valda vikter
├── dataset/
│   ├── store.py           # COCO, versionering, metadata
│   └── export.py          # COCO→YOLO, manifest.json
├── training/trainer.py    # subprocess, progress via queue
└── config.py              # klasser, sökvägar, trösklar
```

## Nyckeldetaljer

- **0/1/2 strömmar:** varje halva i split screen visar antingen video, detekterad video, eller en grå platta med "Ingen videokälla". Källval per vy: UVC-index eller fil (via "Öppna videofil...").
- **Detektion:** worker-tråd per aktiv källa; hoppar över frames om inferens är långsammare än fps; rektangel + `klass 98%` ritas på frames i GUI-tråden.
- **Fånga:** senaste frame + aktuella detektioner från båda vyerna → annoteringsläget öppnas med detektioner förrenderade som redigerbara rektanglar.
- **Annotation:** rita (drag), resize via hörn-/kanthandles, klassbyte från lista eller fritext (nya klasser sparas globalt), radera; Spara → COCO + återgång till detektion.
- **Träning:** YOLO26-träning via Ultralytics; RF-DETR via dess egna API bakom `trainer`-interfacet; vikter sparas som `v{datasetversion}_{datum}.pt`.

## Fasordning

1. **Stomme:** uv-projekt, PySide6-app fullscreen, lägesval, split screen med "Ingen videokälla".
2. **Video:** `VideoSource` (UVC + fil), trådar, källval per vy.
3. **Detektion:** `Detector`-ABC, YOLO26-detektor, overlay-ritning, modellval.
4. **Fånga + annotering:** fånga-knapp, annoteringsvy med redigerbara rektanglar och klasslistan.
5. **Dataset:** COCO-store, versionering, YOLO-export med manifest.
6. **Träning:** träningsvy, subprocess, paus av detektion, vikter med versionskoppling.
7. **RF-DETR:** andra detektorn, modellval i GUI.
8. **Polering:** felhantering, inställningar (confidens, kamera-index), loggning.

## Prestanda- och designbeslut

- **Trådning:** kameror = 2 trådar, detektion = worker-trådar, GUI = huvudtråd. Träning = separat process (undvik GIL + full GPU-access).
- **Frame-strategi:** senaste-frame-wins; detektion kan hoppa över frames om inferensen är långsammare än kamerans fps.
- **Dataset:** alltid COCO internt → ingen "export nödvändig" för fortsatt arbete; YOLO genereras vid träning/export.
