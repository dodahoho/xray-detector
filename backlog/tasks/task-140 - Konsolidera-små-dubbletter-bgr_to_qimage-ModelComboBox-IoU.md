---
id: TASK-140
title: 'Konsolidera små dubbletter: bgr_to_qimage, ModelComboBox, IoU'
status: Done
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-17T22:35:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
modified_files:
  - xray_detector/ui/image_utils.py
  - xray_detector/ui/model_combo.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/infrastructure/detectors/smoothing.py
  - tests/test_ui_shared.py
priority: medium
type: enhancement
ordinal: 159000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tre BGR->QImage-kopior (annotation_view, dataset_view, detection_view), två identiska modellcombo/RF-DETR-kontroller (detection_view._disable_unavailable_models, training_view._disable_missing_rfdetr) och två IoU-implementationer (smoothing._iou, metrics.iou_matrix) (utvärdering_argon.md §3.5, utvärdering_hydrogen.md §3.2-3.3). Skapa bgr_to_qimage() i ui/image_utils.py (alltid .copy()), en gemensam ModelComboBox/hjälpare, och låt smoothing använda iou_matrix. Görs när respektive modul ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bgr_to_qimage() används på alla tre ställen och returnerar alltid en ägd kopia
- [x] #2 En gemensam komponent fyller modell-QComboBox och inaktiverar saknat rfdetr-paket
- [x] #3 En IoU-implementation används av både smoothing och metrics
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Ny ui/image_utils.py med bgr_to_qimage() som alltid returnerar en ägd kopia; de tre vyerna använder den.

2. Ny ui/model_combo.py med ModelComboBox som fyller sig ur modellistan och stänger av saknade paket; detektions- och träningsvyn använder den.

3. Låt smoothing._iou använda iou_matrix från metrics.

4. Tester för kopian, kanalbytet, väljaren och IoU-likheten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ui/image_utils.bgr_to_qimage äger BGR->RGB-konverteringen och kopian; StreamPanel._to_qimage är kvar som tunn delegat eftersom testet för TASK-128 anropar den. ui/model_combo.ModelComboBox fyller listan, behåller valet, stänger av familjer vars paket saknas (OPTIONAL_FAMILIES/missing_packages) och märker posten med '(rfdetr ej installerat)'. Båda vyerna använder den, så _disable_unavailable_models och _disable_missing_rfdetr är borta. smoothing._iou delegerar till metrics.iou_matrix.

Verifiering: fem nya tester i tests/test_ui_shared.py - kopian överlever anropet, kanalbytet blir rätt, väljaren behåller valet, saknat rfdetr stänger av posten, och smoothingens IoU är identisk med iou_matrix (25/175). Hela sviten: 884 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Tre dubbletter är borta: bgr_to_qimage i ui/image_utils.py används av detektions-, annoterings- och datasetvyn och lämnar alltid en ägd kopia; ModelComboBox i ui/model_combo.py fyller båda modellväljarna och stänger av saknade paket på ett ställe; och smoothingens IoU är metrics.iou_matrix. Fem nya tester täcker dem, och hela sviten ger 884 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
