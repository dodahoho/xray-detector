---
id: TASK-74
title: Stäng av videofångst och detektion vid träning
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-12T20:05:00Z'
updated_date: '2026-11-12T20:25:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/main_window.py
  - tests/test_training_pause.py
  - tests/conftest.py
  - tests/test_stream_worker.py
  - README.md
type: feature
ordinal: 72000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
För att spara datorresurser ska videofångst (UVC), uppspelning av videofil samt detektion i videoström stängas av när man kör modellträning.

Om videofångst/uppspelning och detektion är avslaget ska det aktiveras igen automatiskt när man går till fliken Detektion
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 När en träning startar stängs videofångst (UVC), uppspelning av videofil och detektion i videoström av
- [ ] #2 Strömmarna och detektionen startar igen automatiskt när man går till fliken Detektion
- [ ] #3 Detektionen återupptas som förut när träningen avslutas, och förblir av om användaren slagit av den
- [ ] #4 Testerna för detektionsvyn, träningsstarten och flikbytet passerar
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
1. StreamPanel får show_paused() och restart_source(); _show_no_source refaktoriseras till en gemensam _show_message.

2. DetectionView.pause_detection() stänger även av strömmarna med video_service.stop_all() och visar pausad text i panelerna.

3. DetectionView.resume_streams() startar om strömmarna med samma källor och kopplar in detektorn igen; resume_detection() delegerar till den.

4. MainWindow._on_tab_changed anropar resume_streams() när detektionsfliken öppnas.

5. Nya tester för paus, återstart via fliken och avstängd detektion; README uppdateras.
<!-- SECTION:PLAN:END -->
