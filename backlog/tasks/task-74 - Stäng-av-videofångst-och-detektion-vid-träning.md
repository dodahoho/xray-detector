---
id: TASK-74
title: Stäng av videofångst och detektion vid träning
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T20:05:00Z'
updated_date: '2026-11-12T20:29:00Z'
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
- [x] #1 När en träning startar stängs videofångst (UVC), uppspelning av videofil och detektion i videoström av
- [x] #2 Strömmarna och detektionen startar igen automatiskt när man går till fliken Detektion
- [x] #3 Detektionen återupptas som förut när träningen avslutas, och förblir av om användaren slagit av den
- [x] #4 Testerna för detektionsvyn, träningsstarten och flikbytet passerar
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
1. StreamPanel får show_paused() och restart_source(); _show_no_source refaktoriseras till en gemensam _show_message.

2. DetectionView.pause_detection() stänger även av strömmarna med video_service.stop_all() och visar pausad text i panelerna.

3. DetectionView.resume_streams() startar om strömmarna med samma källor och kopplar in detektorn igen; resume_detection() delegerar till den.

4. MainWindow._on_tab_changed anropar resume_streams() när detektionsfliken öppnas.

5. Nya tester för paus, återstart via fliken och avstängd detektion; README uppdateras.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
StreamPanel fick show_paused() och restart_source(); _show_no_source delar nu _show_message med pausläget. pause_detection() anropar video_service.stop_all() utöver set_detector(None) och visar pausad text i båda panelerna. resume_streams() startar om panelernas senaste källor (uvc eller fil) och kopplar in detektorn igen; resume_detection() delegerar till den så träningens slut och fliken Detektion går samma väg. MainWindow._on_tab_changed anropar resume_streams() först när flikbytet faktiskt landar på Detektion, alltså efter den osparade-annotering-guarden.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningsstarten stänger av videofångsten (UVC), uppspelningen av videofil och detektionen i videoströmmen: pause_detection() stoppar kameratrådarna med video_service.stop_all(), kopplar bort detektorn, släpper VRAM och visar "Avstängt under träning" i båda panelerna. Fliken Detektion tänder strömmarna och detektionen igen automatiskt via resume_streams(), och träningens slut återupptar dem på samma sätt; om användaren slagit av detektionen förblir den av. Verifierat: test_training_start_stops_the_streams_and_the_detection (stop_all, bortkopplad detektor, pausad text), test_pause_stops_a_running_stream_worker (en riktig StreamWorker på en videofil är stoppad efter pausen), test_detection_tab_restarts_the_same_sources (uvc och fil startas om med samma källor), test_resume_streams_does_nothing_when_not_paused, test_detection_tab_keeps_the_detection_off, test_training_finish_restarts_the_streams samt test_training_start_and_the_detection_tab_drive_the_streams (MainWindow: träningsstart stänger av, fliken Dataset tänder inte, fliken Detektion tänder). Hela sviten: 500 passed, 1 skipped. README beskriver beteendet.
<!-- SECTION:FINAL_SUMMARY:END -->
