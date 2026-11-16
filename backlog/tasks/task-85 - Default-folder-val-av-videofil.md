---
id: TASK-85
title: Default folder val av videofil
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-16T08:28:00Z'
updated_date: '2026-11-16T08:34:00Z'
labels: []
dependencies: []
references:
  - video-file-dialog
modified_files:
  - xray_detector/ui/video_file_dialog.py
  - xray_detector/ui/detection_view.py
  - tests/test_video_file_dialog.py
  - README.md
  - media/README.md
  - >-
    groma/systems/xray-detector/containers/gui-app/components/video-file-dialog.md
  - groma/systems/xray-detector/containers/gui-app/components/detection-view.md
ordinal: 83000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När man klickar att välja videofil öppnas ett fönster med filutforskare. Där ska default folder vara "media". Om man väljer att öppna fil från annat ställe ska applikationen komma ihåg den sökvägen och nästa gång använda det som förvald path
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Filväljaren för videofil öppnas i projektets media/ när ingen katalog är sparad
- [x] #2 Väljs en fil i en annan katalog öppnas nästa filväljare i den katalogen
- [x] #3 Den valda katalogen sparas mellan starterna
- [x] #4 Testerna passerar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Ny modul xray_detector/ui/video_file_dialog.py: video_file_dir(settings) ger senast valda katalog om den finns kvar, annars projektets media/; remember_video_file(settings, path) sparar filens katalog under detection/file_dir.
2. xray_detector/ui/detection_view.py: filväljaren i _on_source_changed öppnas i video_file_dir(self.settings) och vald fil sparas med remember_video_file, så nästa dialog öppnas där.
3. Tester i tests/test_video_file_dialog.py: media/ som default, minnet av annan katalog, borttagen katalog faller tillbaka på media/, avbruten dialog ändrar inget, panel utan settings.
4. Uppdatera README (detektionsläget) och media/README.md samt groma-beskrivningen av detektionsvyn.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- Ny modul xray_detector/ui/video_file_dialog.py: video_file_dir(settings) ger senast valda katalog om den finns kvar, annars projektets media/ (PROJECT_ROOT/media); remember_video_file(settings, path) sparar filens katalog under detection/file_dir. Panel utan settings faller tillbaka på media/.
- xray_detector/ui/detection_view.py: filväljaren i StreamPanel._on_source_changed öppnas i video_file_dir(self.settings) och vald fil sparas med remember_video_file innan _activate_file. Avbruten dialog rör inte det sparade värdet.

Verifiering:
- 7 nya tester i tests/test_video_file_dialog.py: media/ som default (även utan settings), att dialogen får media/ som katalogargument, att vald fil i annan katalog gör att nästa dialog öppnas där, att avbruten dialog behåller katalogen, att en borttagen sparad katalog faller tillbaka på media/, samt att värdet överlever en ny QSettings-instans.
- Manuell kontroll över två processer: första processen sparar C:/Users/Ai1/Videos, ini-filen får [detection] file_dir=C:\Users\Ai1\Videos och en ny process läser tillbaka samma katalog.
- Berörda tester: 53 passed (test_video_source_persistence, test_sample_video, test_gui_smoke, test_detection_overlay, test_detection_badge, test_video_modes).
- Hela sviten: 607 passed, 1 skipped.

Dokumentation: README (detektionsläget), media/README.md samt groma (ny komponenten video-file-dialog med beskrivning, relationen detection-view -> video-file-dialog och detektionsvyns översikt).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Filväljaren för videofiler öppnas nu i projektets media/ första gången och i senast valda katalog därefter. Katalogen sparas i QSettings (detection/file_dir) när en fil väljs, och en sparad katalog som inte längre finns hoppas över så dialogen aldrig öppnas i en borttagen mapp.

Ändrat: ny modul xray_detector/ui/video_file_dialog.py (video_file_dir/remember_video_file), anrop i StreamPanel._on_source_changed, 7 nya tester i tests/test_video_file_dialog.py, README, media/README.md och groma (ny komponent video-file-dialog med relation från detektionsvyn).

Verifiering: 7 nya tester passerar, 53 berörda tester passerar och hela sviten ger 607 passed, 1 skipped. Persistensen kontrollerad över två processer: ini-filen får [detection] file_dir och nästa process läser tillbaka samma katalog.

Risker: katalogen sparas bara om den finns när filen väljs; en nätverkskatalog som är otillgänglig vid nästa start faller tillbaka på media/.
<!-- SECTION:FINAL_SUMMARY:END -->
