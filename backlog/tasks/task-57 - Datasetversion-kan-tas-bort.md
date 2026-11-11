---
id: TASK-57
title: Datasetversion kan tas bort
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T21:45:00Z'
updated_date: '2026-11-11T21:55:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/application/dataset_service.py
  - xray_detector/infrastructure/dataset_store/export.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/main_window.py
  - xray_detector/application/model_registry.py
  - xray_detector/infrastructure/dataset_store/json_io.py
  - tests/test_dataset_store.py
  - tests/test_export_split.py
  - tests/test_atomic_json.py
  - tests/test_gui_smoke.py
  - tests/test_busy_operations.py
  - tests/test_dataset_header.py
  - tests/test_dataset_selection.py
  - tests/test_dataset_sort.py
  - tests/test_shortcuts.py
  - tests/test_training_scheduler.py
  - tests/test_model_layout.py
  - tests/test_pending.py
  - tests/test_annotation_ux.py
  - tests/test_rfdetr.py
  - README.md
  - groma/systems/xray-detector/system.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset-service.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset-view.md
  - groma/systems/xray-detector/containers/gui-app/components/training-view.md
  - groma/systems/xray-detector/containers/gui-app/components/trainer.md
  - groma/flows/träna-om-modellen.md
type: enhancement
ordinal: 55000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Just nu finns det inget syfte med datasetversion så ta bort den hanteringen från vyn dataset och även från träningsvyn.

Funktionen kan vara att de bilder som för tillfället finns sparade under vyn dataset är det som blir källa till träning

Förenkla koden om det går
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Datasetvyn visar bilderna som ligger i datasetet utan versionsväljare
- [ ] #2 Träningsvyn tränar på bilderna som ligger i datasetet utan versionsväljare
- [ ] #3 Lagring, export och vyer har ingen versionshantering kvar
- [ ] #4 Tester, README och groma-arkitekturen beskriver det nya beteendet
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. DatasetStore/DatasetService: ett enda dataset (dataset.json + images/) i stället för v<N>-kataloger; ta bort versions(), current_version(), new_version() och version_dir().
2. export.py: exportera till exports/yolo, exports/coco och exports/rfdetr utan versionssiffra; manifestet tappar version; töm exportkatalogen före skrivning så gamla bilder inte ligger kvar.
3. Datasetvyn: ta bort versionsväljaren, läs det aktuella datasetet och låt refresh() ersätta refresh_versions().
4. Träningsvyn: ta bort versionsväljaren, visa datasetets sammanställning och träna på det som ligger i datasetet; körningskatalogen under models/trained/ får en tidsstämpel i stället för v<N>.
5. Annoteringsvyn och huvudfönstret: spara utan version och uppdatera datasetuppgifterna efter sparning.
6. Uppdatera tester, README och groma-beskrivningarna.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Datasetet är nu en enda samling: datasets/dataset.json med bilderna i datasets/images/. DatasetStore tappar versions(), current_version(), new_version() och version_dir(); add_samples, delete_images, load_coco och metadata tar inga versionsargument. Ett dataset som sparades som datasets/v<N> flyttas upp till roten vid start (nyaste versionen vinner), så befintliga bilder finns kvar i vyn. Exporten går till exports/yolo, exports/coco och exports/rfdetr, och katalogen töms före skrivning så bilder som raderats ur datasetet inte ligger kvar i nästa export; manifestet har kvar format, datum och antal men inte version. Datasetvyn har ingen versionsväljare och refresh_versions() är borta; refresh() läser det aktuella datasetet. Träningsvyn visar datasetets sammanställning i stället för versionsval, startar på det som ligger i datasetet (statusraden 'Datasetet är tomt' när det är tomt) och sparar körningen under models/trained/<datum>_<tid>. Annoteringsvyn sparar utan version. Verifierat med hela testsviten (277 passed, 1 skipped) och migrationen körd mot en kopia av ~/.xray-detector/datasets (8 bilder, 6 objekt flyttades upp). Ruff på de ändrade filerna visar inga nya anmärkningar.
<!-- SECTION:NOTES:END -->
