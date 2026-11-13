---
id: TASK-78
title: Dataset - Använd YOLO som internt format istf COCO
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-13T12:28:00Z'
updated_date: '2026-11-13T13:48:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 76000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Applikationen har i grunden COCO som internt format för att lagra dataset. Anledningen till det vara att ha ett format som inte är direkt knutet till modellfamiljerna YOLO eller RF-DETR, men det visar sig att YOLO dataformat funkar bättre out of the box. Både YOLO-modeller och RF-DETR stödjer träning med dataset i YOLO-format. Med COCO finns inte naturligt stöd för träning av YOLO-modeller, där COCO json i sådana fall behöver konverteras till txt först.

Byt därför det interna formatet till YOLO, konvertera projektets dataset till YOLO och uppdatera referenser, dokumentation mm så att det är korrekt.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Ny intern lagring i YOLO-format under datasets/: data.yaml (klasser), images/, labels/ (YOLO-txt) och dataset.json som enbart metadata (id, filnamn, storlek, fångstgrupp, fångsttid).
2. Automatisk engångsmigrering av befintligt COCO-dataset (dataset.json med annotations/categories) till YOLO vid start; dataset.json skrivs sist så en avbruten migrering görs om.
3. DatasetStore/DatasetService läser och skriver YOLO. Klassändringar remappar labelindexen så att sparade annoteringar behåller rätt klass.
4. export.py: YOLO-exporten kopierar images+labels och delar train/val per fångstgrupp; COCO- och RF-DETR-exporterna bygger sina JSON-filer från YOLO-datat.
5. Datasetvyn läser en läsmodell med klassnamn och pixel-bboxar per bild i stället för COCO-dokumentet.
6. Uppdatera tester och dokumentation (README, PLAN, specs) samt groma-beskrivningarna via CLI.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
DatasetStore lagrar nu datasetet i YOLO-format: data.yaml (klasser), images/, labels/ (en .txt per bild) och dataset.json som enbart metadata (id, filnamn, storlek, fångstgrupp, fångsttid). Ny modul yolo.py läser och skriver data.yaml och label-filer samt konverterar mellan pixel-bboxar och normaliserade mått.

Automatisk engångsmigrering: ett dataset.json med annotations/categories konverteras till YOLO i DatasetStore.__init__. dataset.json skrivs sist, så en avbruten migrering görs om i stället för att lämna datasetet halvkonverterat.

set_classes remappar labelindexen när klasslistan ändras, eftersom YOLO lagrar klassen som index i names-listan. class_in_use läser label-filerna, så en klass som används kan fortfarande inte tas bort.

export_yolo kopierar images/ och labels/ och delar train/val per fångstgrupp. export_coco och export_rfdetr bygger COCO-JSON från YOLO-datat med category_id = klassindex + 1.

DatasetService.load_coco är ersatt av load_dataset, som returnerar klasser och bilder med annoteringar som klassnamn och pixel-bboxar. Datasetvyn använder den läsmodellen i stället för COCO-dokumentet.

Projektets dataset i ~/.xray-detector/datasets konverterades: 16 bilder, 13 objekt och 6 klasser. Alla annoteringar jämfördes mot en backup och är identiska. Backupen ligger i ~/.xray-detector/datasets.coco-backup.

Verifiering: 532 tester passerar. test_sample_video.py::test_sample_video_meta fallerar även före ändringen (videofilerna i media/ har 6000 ramar, testet förväntar 2250) och hör inte till uppgiften.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetet lagras nu i YOLO-format i stället för COCO: klasserna i datasets/data.yaml, bilderna i datasets/images/ och annoteringarna i datasets/labels/ (en .txt per bild med klassindex och normaliserade mått). datasets/dataset.json innehåller bara metadata som YOLO saknar: bild-id, storlek, fångstgrupp och fångsttid, som vyerna grupperar och sorterar på.

Varför: YOLO-formatet kan läsas direkt av både ultralytics och rfdetr, så ingen COCO-till-YOLO-konvertering behövs före träning. Exporten är nu en kopiering plus train/val-delning i stället för en formatkonvertering.

Ändrat:
- Ny modul dataset_store/yolo.py för data.yaml och label-filer samt pixel-/normaliserade bboxar.
- DatasetStore konverterar ett befintligt COCO-dataset till YOLO vid start; dataset.json skrivs sist så en avbruten migrering görs om.
- set_classes remappar labelindexen när klasslistan ändras, eftersom YOLO lagrar klassen som index.
- export_yolo kopierar images/ och labels/ och delar train/val per fångstgrupp; export_coco och export_rfdetr bygger COCO-JSON från YOLO-datat.
- DatasetService.load_coco är ersatt av load_dataset (klassnamn och pixel-bboxar per bild); datasetvyn använder den läsmodellen.
- README, PLAN, specs och groma-beskrivningarna uppdaterade.

Verifiering: 532 av 533 tester passerar. Projektets dataset i ~/.xray-detector/datasets konverterades och alla 16 bilder, 13 objekt och 6 klasser jämfördes mot en backup och är identiska; backupen ligger i ~/.xray-detector/datasets.coco-backup. Den enda felande testen, test_sample_video.py::test_sample_video_meta, fallerar även på bascommit (videofilerna i media/ har 6000 ramar medan testet förväntar 2250) och hör inte till uppgiften, så DoD 3 är medvetet okryssad.

Risker: migreringen är enkelriktad men idempotent och säker att avbryta. En label-rad vars klass inte längre finns i listan tas bort vid klassändring; annoteringsvyn hindrar redan att en använd klass tas bort.
<!-- SECTION:FINAL_SUMMARY:END -->
