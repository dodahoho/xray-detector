---
id: TASK-11
title: 'Fullständigt RF-DETR-stöd: träning och datasetexport'
status: In Progress
assignee: []
created_date: '2026-11-06T14:05:00Z'
updated_date: '2026-11-09T09:38:00Z'
labels:
  - detektion
  - träning
  - rf-detr
dependencies: []
references:
  - trainer
  - train-task
  - dataset
priority: medium
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vibe-glm53 har RF-DETR bara som inferens-backend; träningsvyn listar RF-DETR base men train_task.py kan bara träna YOLO, och exporten saknar RF-DETR-format. opencode-bigpickle har hela kedjan: rfdetr_train.py (träning, med inspect.signature för versionskompatibilitet) och rfdetr_export.py (RF-DETR:s förväntade format: train-/valid-/test-kataloger med _annotations.coco.json). Se jämförelse_argon.md avsnitt 4.

Tillvägagångssätt: utöka export.py med export_rfdetr(), låt träningsprocessen hantera rfdetr-modellfamiljen (separat träningsläge i train_task.py eller en sysentrypoint), och inaktivera RF-DETR-träning i träningsvyn när paketet saknas.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 träningsvyn kan träna RF-DETR base om rfdetr är installerat (annars avstängt)
- [ ] #2 dataset kan exporteras i RF-DETR-format (train/valid/test med _annotations.coco.json)
<!-- AC:END -->
