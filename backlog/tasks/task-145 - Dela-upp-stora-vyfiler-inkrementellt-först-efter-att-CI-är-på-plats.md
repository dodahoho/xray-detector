---
id: TASK-145
title: Dela upp stora vyfiler inkrementellt (först efter att CI är på plats)
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-18T09:19:00Z'
labels:
  - refactor
  - review-followup
dependencies:
  - TASK-123
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/ui/flow_layout.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/capture_card.py
  - xray_detector/ui/stream_panel.py
  - xray_detector/ui/detection_view.py
  - tests/test_dataset_layout.py
  - tests/test_dataset_card_click.py
  - tests/test_dataset_header.py
  - tests/test_colors.py
  - tests/test_detection_badge.py
  - tests/test_detection_overlay.py
  - tests/test_detector_threading.py
  - tests/test_devices.py
  - tests/test_reconnect.py
  - tests/test_resources.py
  - tests/test_sample_video.py
  - tests/test_stream_worker.py
  - tests/test_training_pause.py
  - tests/test_video_file_dialog.py
  - tests/test_video_modes.py
priority: medium
type: enhancement
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
dataset_view.py (1127 rader), detection_view.py (954), annotation_view.py (804) och training_view.py (603) blandar widgets, affärslogik, QSettings och trådhantering (alla tre utvärderingarna). Big-bang-refaktorering är förbjuden innan CI körs: bryt ut EN widget i taget när filen ändå rörs, börja med FlowLayout till ui/flow_layout.py, sedan CaptureCard/Thumbnail och StreamPanel/ResourceMeter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 FlowLayout ligger i egen modul och dataset_view.py är märkbart mindre
- [ ] #2 Varje utbrytning är en egen liten ändring med passerande tester (ingen big-bang)
- [ ] #3 Ingen vyuppdelning påbörjas innan TASK-123 (CI) är Done
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
1. Flytta FlowLayout ordagrant till ui/flow_layout.py och importera den i dataset_view.py; ta bort de Qt-imports som bara layouten använde. Kör test_dataset_layout.py.
2. Flytta CaptureCard och Thumbnail till ui/capture_card.py som en egen liten ändring, med THUMB_BORDER-konstanten; uppdatera importerna i dataset_view.py och testerna. Kör test_dataset_layout.py och test_dataset_thumbnails.py.
3. Lämna StreamPanel/ResourceMeter till nästa inkrement: de kräver att konstanterna och hjälpfunktionerna i detection_view.py flyttas med, vilket är en större ändring än ett widgetutbrott.
4. Kör ruff och hela testsviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
FlowLayout ligger nu i ui/flow_layout.py och importeras av dataset_view.py; de Qt-imports som bara layouten använde är borttagna. dataset_view.py gick från 1171 till 1092 rader och test_dataset_layout.py, test_dataset_thumbnails.py, test_dataset_card_click.py och test_dataset_selection.py passerar.

CaptureCard och Thumbnail ligger nu i ui/capture_card.py tillsammans med THUMB_BORDER, och testerna importerar dem därifrån. dataset_view.py är 1022 rader (från 1171) och hela sviten ger 893 passed, 4 failed; de fyra felen är desamma som på HEAD och beror på att miljön saknar teckensnitt.

StreamPanel, ResourceMeter, draw_detections och panelernas konstanter ligger nu i ui/stream_panel.py; detection_view.py importerar dem och gick från 939 till 514 rader. Testerna importerar panelerna därifrån. Hela sviten ger 893 passed, 4 failed, och de fyra felen är desamma som på HEAD (teckensnitt saknas i miljön).
<!-- SECTION:NOTES:END -->
