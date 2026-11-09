---
id: TASK-22
title: 'Lagerindelad DDD-arkitektur: domain / application / infrastructure / ui'
status: To Do
assignee: []
created_date: '2026-11-09T08:36:00Z'
updated_date: '2026-11-09T08:36:00Z'
labels:
  - arkitektur
  - refaktorering
  - ddd
dependencies: []
references:
  - gui-app
  - training-process
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
- [ ] #1 domänlagret (domain/) är fritt från Qt-, OpenCV- och torch-importer (verifieras med importsökning/test)
- [ ] #2 ui/-paketet importerar inte infrastructure/ direkt, bara application/ och domain/
- [ ] #3 både katalog- och funktionsbeteende bibehålls (ström, fånga, annotera, spara, träna, detektera)
- [ ] #4 träningsprocessen startar via nya modulsökvägen och TRAINING_DONE fångas i loggen
- [ ] #5 groma scan körd och komponentägandet följer nya platsen
<!-- AC:END -->
