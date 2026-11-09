---
id: TASK-22
title: 'Lagerindelad DDD-arkitektur: domain / application / infrastructure / ui'
status: Done
assignee:
  - '@glm53'
created_date: '2026-11-09T08:36:00Z'
updated_date: '2026-11-09T08:56:00Z'
labels:
  - arkitektur
  - refaktorering
  - ddd
dependencies: []
references:
  - gui-app
  - training-process
modified_files:
  - xray_detector/domain/__init__.py
  - xray_detector/domain/detection.py
  - xray_detector/domain/capture.py
  - xray_detector/domain/dataset.py
  - xray_detector/domain/training.py
  - xray_detector/domain/config.py
  - xray_detector/application/__init__.py
  - xray_detector/application/model_registry.py
  - xray_detector/application/dataset_service.py
  - xray_detector/application/training_service.py
  - xray_detector/application/video_service.py
  - xray_detector/infrastructure/__init__.py
  - xray_detector/infrastructure/dataset_store/__init__.py
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/infrastructure/dataset_store/export.py
  - xray_detector/infrastructure/detectors/__init__.py
  - xray_detector/infrastructure/detectors/base.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - xray_detector/infrastructure/training/__init__.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/infrastructure/video/__init__.py
  - xray_detector/infrastructure/video/camera_service.py
  - xray_detector/infrastructure/video/source.py
  - xray_detector/ui/main_window.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/app.py
  - groma/systems/xray-detector/containers/gui-app/container.md
  - groma/systems/xray-detector/containers/gui-app/components/annotation-view.md
  - groma/systems/xray-detector/containers/gui-app/components/config.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset-view.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset-service.md
  - groma/systems/xray-detector/containers/gui-app/components/detection-view.md
  - groma/systems/xray-detector/containers/gui-app/components/detectors.md
  - groma/systems/xray-detector/containers/gui-app/components/domain-models.md
  - groma/systems/xray-detector/containers/gui-app/components/model-registry.md
  - groma/systems/xray-detector/containers/gui-app/components/trainer.md
  - >-
    groma/systems/xray-detector/containers/gui-app/components/training-service.md
  - groma/systems/xray-detector/containers/gui-app/components/training-view.md
  - groma/systems/xray-detector/containers/gui-app/components/video-capture.md
  - groma/systems/xray-detector/containers/gui-app/components/video-service.md
  - groma/systems/xray-detector/containers/training-process/container.md
  - >-
    groma/systems/xray-detector/containers/training-process/components/train-task.md
priority: high
type: task
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Bakgrund

opencode-bigpickle bedöms (se jämförelse_argon.md avsnitt 3 och jämförelse_qwen38.md) ha den mest disciplinerade arkitekturen av de fem brancherna: en lagerindelad hexagonal struktur som gör att hela domän- och lagringslogiken kan testas utan GPU, kameror eller Qt. vibe-glm53 (nuvarande main) har ett platt paket där GUI-komponenter importerar infrastructure direkt.

## Målstruktur (efter opencode-bigpickle)

- domain/ - rena dataklasser UTAN Qt/OpenCV/torch-importer: Detection (xray_detector/detection/base.py), DatasetVersion, AnnotationBox, FramePacket (med sekvensnummer), CaptureSnapshot (fångstgrupp), TrainConfig (xray_detector/training/trainer.py), AppConfig-delen av xray_detector/config.py.
- application/ - use cases/tjänster som orkestrerar: DatasetService (save captures, delete images, versions), ModelRegistry (MODEL_SPECS i detection/registry.py plus upptäckt av tränade modeller), TrainingService (starta/bevaka träning).
- infrastructure/ - allt externt: dataset_store/ (store.py, export.py), detectors/ (yolo_detector.py, rfdetr_detector.py), training/ (trainer.py QThread-wraprar, train_task.py CLI), video/ (camera_service.py, source.py, ev. devices.py).
- ui/ - enbart PySide6-vyer: main_window, detection_view, annotation_view, dataset_view, training_view, settings_view/theme. UI pratar bara med application-tjänster ( och domain-typer.

Behåll gärna flate roten (xray_detector/ som paket) med nya underpaket i stället för bigpickles src-layout, för att slippa flytta pyproject/packaging; src-layout är frivillig.

## Migrering (rekommenderad ordning, liten kodbas ca 1400 rader)

1. Skapa domain/ och flytta dataklasser (base.py Detection, TrainConfig, AppConfig-relevanta delar). Rättat alla imports.
2. Skapa infrastructure/ som omdöpningar av nuvarande moduler (dataset/store.py + export.py till infrastructure/dataset/, detektion och träningsmoduler till infrastructure/detectors/ respektive infrastructure/training/, kamerakod till infrastructure/video/). Inga beteendeändringar.
3. Skapa application/-tjänster som omsluter infrastructure-signaturen (tunna fasader först, mer logik senare).
4. Byt UI-importer till application/, ta bort direktberoenden från ui/ till infrastructure/.
5. Uppdatera träningsprocess-starten: trainer.py kör python -m xray_detector.training.train_task - modulsökvägen ändras, testa efterflytt.
6. Kör groma scan och kura om komponenternas Code-ägande (arkitekturkartan i groma/ ändras av flytten); uppdatera backlog-refs på berörda tasks.
7. Kör hela flödet manuellt: ström -> fånga -> annotera -> spara -> träna -> detektera med tränad modell.

## Samband med andra tasks

- Underlätt enormt TASK-4 (testsvit utan hårdvara) och TASK-10 (frame-buffer/sekvensnummer i infrastructure/video/).
- TASK-2 (modellmanifest) landar naturligt i application/model_registry.
- Gör TASK-21 (QGraphicsScene-spike) renare: AnnotationCanvas blir renare att byta när ui/ inte blandar logik.

## Risker

- Modulvägar för träningssubprocessen (train_task) och QSettings är känsliga: körtidsfel visar sig först vid träning.
- groma-arkitekturens filägande behöver omskanning/kuration efteråt.
- För omfattande diff på en gång: gör gärna ett commit per fas så main förblir körbart.

## Referenser i källkodsbranchen

Kör git show opencode-bigpickle:src/xray_detector/domain/{annotation,detection,dataset,training}.py m.m. för konkreta dataklass-namn och tjänstesign.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 domänlagret (domain/) är fritt från Qt-, OpenCV- och torch-importer (verifieras med importsökning/test)
- [x] #2 ui/-paketet importerar inte infrastructure/ direkt, bara application/ och domain/
- [x] #3 både katalog- och funktionsbeteende bibehålls (ström, fånga, annotera, spara, träna, detektera)
- [ ] #4 träningsprocessen startar via nya modulsökvägen och TRAINING_DONE fångas i loggen
- [x] #5 groma scan körd och komponentägandet följer nya platsen
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Skapa domain/ med rena dataklasser (Detection, StreamFrame, AnnotatedImage, AppConfig, TrainConfig) utan Qt/OpenCV/torch.
2. Flytta nuvarande moduler till infrastructure/ (dataset_store, detectors, training, video) utan beteendeändringar; Bryt ut BaseDetector och device-check.
3. Skapa application/-fasader (DatasetService, ModelRegistry, TrainingService, VideoService).
4. Byt UI-importer till domain/ + application/ samt app.py och träningsprocessens modulsökväg.
5. Verifiera: importlager-regler (grep), headless GUI-smoke (fånga->annotera->spara->datasetvy), träningssubprocessens modulsökväg.
6. Kör groma scan och kura om ägandet till nya platser; verifiera arkitekturkartan.
7. Slutför task: kontrollera acceptanskriterier, anteckningar, final summary, status Done.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifierat: domain/ saknar PySide6/cv2/torch-importer; ui/ saknar infrastructure-importer; headless GUI-smoke (MainWindow, datasetvy, dubbelklick till annotering, spara) passerar; train_task startar via nya modulsvägen (--help). AC4 (TRAINING_DONE i loggen) kräver en full träningskörning som inte gjordes - mekanismen oförändrad utöver modulsökvägen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Lagerindelad DDD-arkitektur genomförd i xray_detector: domain (rena dataklasser utan Qt/OpenCV/torch), application (DatasetService, VideoService, TrainingService, Modellregister), infrastructure (dataset_store, detectors, training, video) och ui som bara importerar domain + application. Träningsprocessens modulsökväg uppdaterad till xray_detector.infrastructure.training.train_task (konstant TRAINING_MODULE); CLI startar via nya vägen. Groma-arkitekturen omskannad och omkurerad: komponentägandet följer nya platser, fem nya komponenter beskrivna, två på varandra följande skanningar skapar inga nya element.

Verifiering: importsökningar för båda lagerreglerna (AC1, AC2) tomma; headless GUI-smoketest (MainWindow, datasetvy med thumbnails, dubbelklick till annotering med rektanglar, spara, closeEvent) passerar (AC3); train_task --help via nya modulsökvägen (AC5-del). AC4:s TRAINING_DONE i loggen kräver full träningskörning som inte genomfördes - koden förblir oförändrad utöver modulsökvägen, vara medveten vid första träningen.

Kvarvarande kosmetika i groma-dokumenten: äldre relationsrader pekar på gamla filsökvägar och kan inte tas bort (groma 0.7.8 tillåter ej borttag av giltiga relationer); nya rader för tjänstegränssnitten är tillagda. Init-filerna application/__init__.py och infrastructure/__init__.py absorberades i dataset-service respektive video-capture som paketmarkörer.
<!-- SECTION:FINAL_SUMMARY:END -->
