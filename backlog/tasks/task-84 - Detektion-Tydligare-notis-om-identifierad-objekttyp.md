---
id: TASK-84
title: Detektion - Tydligare notis om identifierad objekttyp
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T07:47:00Z'
updated_date: '2026-11-16T07:54:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/badge.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/settings_dialog.py
  - tests/test_detection_badge.py
  - README.md
ordinal: 82000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu visas ett identifierat objekt med annoterad ruta i respektive videofönster. Det är ibland svårt att se vilken klass som identifieras. Dels pga att textstorleken är för liten, dels pga att färgerna i bilden kan få kontrasten att bli dålig.

Föreslår följande:
* Dubbla textstorleken för annoterat objekt i detekterad video
* Lägg en badge med identifierad objektklass och procentuell sannolikhet högst upp i respektive videofönster. Lägg den längst upp till höger i det första videofönstret och längst upp till vänster för det andra fönstret så kommer de nära varandra. För att undvika att badge flimrar mellan olika frames (dyker upp och försvinner när detektion hamnar över/under tröskelvärdet i olika frames) så ska det vara en inställningsbar fördröjning att visas och döljas. T ex att det ska detekteras i 3 efterföljande frames innan det visas och en fördröjning på 10 frames utan detektion innan badge döljs
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Etiketten för ett annoterat objekt i detekterad video har dubbel textstorlek
- [x] #2 En badge med klass och procentuell sannolikhet visas högst upp till höger i första videofönstret och högst upp till vänster i andra
- [x] #3 Badgen visas först efter ett inställningsbart antal ramar med detektion och döljs först efter ett inställningsbart antal ramar utan
- [x] #4 Fördröjningarna går att ställa in i detektionsvyns inställningar och sparas mellan starterna
- [x] #5 Testerna passerar
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
1. Ny modul ui/badge.py: BadgeTracker som per klass räknar sammanhängande ramar med respektive utan detektion och därmed styr när märket visas (standard 3 ramar) och döljs (standard 10 ramar), plus ritning av märket med klassfärg och procentsats.
2. ui/detection_view.py: dubbla textstorleken för rutans etikett (10 -> 20 pt) och placera etiketten med fontmetrik så den inte klipps vid bildkanten. Rita märket på den skalade pixmapen högst upp till höger i vänstra panelen och högst upp till vänster i högra panelen, så det sitter nära mitten. Nollställ spårningen när overlayn rensas.
3. ui/settings_dialog.py: BadgeSection med två spinnrar (visa efter N ramar, dölj efter N ramar) som sparas i QSettings och slår igenom direkt på båda panelerna.
4. Tester i tests/test_detection_badge.py: hysteresen (visas efter N ramar, hålls kvar över glapp, döljs efter N missade ramar, högsta sannolikhet vinner), märkets placering i respektive panel, att etiketten blir större och att inställningarna sparas och slår igenom.
5. Uppdatera README (detektionsläget och vyernas inställningar) samt groma-beskrivningen av detektionsvyn.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- Ny modul xray_detector/ui/badge.py: BadgeTracker räknar sammanhängande ramar per klass (visas efter show_frames, döljs efter hide_frames, högst sannolikhet vinner när flera klasser syns), badge_delays läser fördröjningarna ur QSettings, draw_badge ritar märket med klassfärg som bakgrund.
- xray_detector/ui/detection_view.py: LABEL_POINT_SIZE 20 (tidigare 10) och etiketten placeras med fontmetrik så den inte klipps vid bildkanten. draw_detections bröts ut som egen funktion. Märket ritas på den skalade pixmapen, så det har fast storlek oavsett källans upplösning: badge_align_right=True i vänstra panelen, False i högra. clear_overlay nollställer spårningen så märket försvinner direkt när detektionen slås av.
- xray_detector/ui/settings_dialog.py: BadgeSection med 'Visa efter' (1-60 ramar) och 'Dölj efter' (1-120 ramar), sparade under detection/badge_show_frames och detection/badge_hide_frames. Ändringar slår igenom direkt på båda panelerna.

Verifiering:
- 16 nya tester i tests/test_detection_badge.py: hysteresen (väntar på show_frames, räknaren börjar om vid glapp, hålls kvar över glapp kortare än hide_frames, döljs efter hide_frames, högsta sannolikhet vinner, reset), märkets placering i respektive panel, att märket inte ritas före show_frames, att clear_overlay tar bort det direkt, att etiketten når minst 20 px över rutan (10 pt nådde 15 px, 20 pt 25 px), samt att inställningarna sparas och slår igenom på båda panelerna.
- 88 tester i de berörda filerna passerar (test_detection_badge, test_detection_overlay, test_settings_dialog, test_detection_toggle, test_class_filter, test_gui_smoke, test_stream_worker).
- Hela sviten: 594 passed, 1 failed. Felet är test_sample_video_meta, som är trasigt sedan c1d39f4 bytte demovideorna: filen har 6000 ramar men testet förväntar 2250. Verifierat att samma test fallerar på HEAD d9b4df2 i en ren worktree, alltså före denna uppgift.
- Visuell kontroll: båda panelerna renderade till PNG med ljus och mörk bakgrund. Märket sitter högst upp till höger respektive vänster, med klassfärg och mörk text, och rutans etikett är tydligt större.

Dokumentation: README (detektionsläget och avsnittet om vyernas inställningar) samt groma (ny komponenten badge med beskrivning, relationen detection-view -> badge och detektionsvyns översikt).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Detektionsvyn visar nu vilken klass som identifieras, både på rutan och högst upp i videofönstret.

Vad som ändrades:
- Etiketten på en detekterad ruta ritas i 20 pt i stället för 10 pt och placeras med fontmetrik, så den inte klipps när rutan ligger högt i bilden.
- Ny modul ui/badge.py med BadgeTracker, som per klass räknar sammanhängande ramar med och utan detektion. Märket visas först efter 3 ramar med klassen och döljs först efter 10 ramar utan, så en detektion nära tröskelvärdet inte får det att flimra. Syns flera klasser samtidigt visas den med högst sannolikhet.
- Märket ritas på den skalade bilden, så textstorleken inte beror av källans upplösning, och sitter högst upp till höger i vänstra panelen och högst upp till vänster i högra, så de två märkena hamnar nära varandra. Bakgrunden är klassens färg, så kontrasten mot bilden bakom spelar ingen roll.
- Fördröjningarna ställs in i detektionsvyns inställningar (Visa efter / Dölj efter, i ramar) och sparas i settings.ini under detection/badge_show_frames och detection/badge_hide_frames. Ändringar slår igenom direkt på båda panelerna.
- När detektionen slås av eller pausas nollställs spårningen, så märket försvinner direkt i stället för att dröja kvar.

Verifiering: 16 nya tester i tests/test_detection_badge.py, och 88 tester i de berörda filerna passerar. Hela sviten gav 594 passed och 1 failed: test_sample_video_meta förväntar 2250 ramar men demovideorna byttes i c1d39f4 och har 6000. Felet finns även på HEAD före denna uppgift och rör inte denna ändring. Båda panelerna renderades till PNG och kontrollerades visuellt.

Risker och uppföljning: test_sample_video_meta behöver uppdateras till de nya demovideornas ramantal, och groma-komponenten translations.md ligger fortfarande ocommittad sedan TASK-83.
<!-- SECTION:FINAL_SUMMARY:END -->
