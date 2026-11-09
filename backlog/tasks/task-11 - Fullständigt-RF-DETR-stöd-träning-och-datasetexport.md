---
id: TASK-11
title: 'Fullständigt RF-DETR-stöd: träning och datasetexport'
status: Done
assignee: []
created_date: '2026-11-06T14:05:00Z'
updated_date: '2026-11-09T10:09:00Z'
labels:
  - detektion
  - träning
  - rf-detr
dependencies: []
references:
  - trainer
  - train-task
  - dataset
modified_files:
  - xray_detector/infrastructure/dataset_store/export.py
  - xray_detector/application/dataset_service.py
  - xray_detector/domain/training.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/ui/training_view.py
  - tests/test_rfdetr.py
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
- [x] #1 träningsvyn kan träna RF-DETR base om rfdetr är installerat (annars avstängt)
- [x] #2 dataset kan exporteras i RF-DETR-format (train/valid/test med _annotations.coco.json)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
export_rfdetr() skriver RF-DETR-formatet (train/valid/test per split med images/ och _annotations.coco.json, grupp-medveten split, manifest med num_train/num_val/num_test) och fasaden ligger i DatasetService. TrainConfig far family ('yolo'/'rfdetr'), trainer skickar --family i kommandoraden (utbrutet i testbar command()-metod), och train_task har rfdetr-gren som tränar RFDETRBase med signaturfiltrerade kwargs (rfdetr-paketets API varierar mellan versioner) samt manifest med pth-vikter och COCO-lasta klasser. Tranningsvyn avstanger RF-DETR-posten ('rfdetr ej installerat') nar paketet saknas och blockerar start med tydlig status. Verifierat: 4 nya tester (exportlayout per split inkl bilder+annoteringar+kategorier, trainer kommando med family for bada familjer, avstalning i tranningsvy - rfdetr saknas i denna milj s aven avstalningslagen fins verklig). EGEN rfdetr-traning har inte kornts eftersom paketet inte ar installerat i miljon - grenen ar skyddad men kran verifiering kraver 'uv sync --extra rfdetr'.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fullstandigt RF-DETR-stod: export i RF-DETR-format (train/valid/test med _annotations.coco.json, grupp-medveten split), traning via train_task --family rfdetr (RFDETRBase med signatur-kompatibla kwargs, manifest med pth-vikter och COCO-klasser), avstalning av RF-DETR i tranningsvyn nar paketet saknas samt blockerad start med tydlig status. Notera: riktig rfdetr-traning har inte korts i denna milj (paketet valfritt, inte installerat) - kran forsta trangning kraver 'uv sync --extra rfdetr' att bekräfta att rfdetr::train-callen fellhantering fungerar.
<!-- SECTION:FINAL_SUMMARY:END -->
