---
id: TASK-84
title: Detektion - Tydligare notis om identifierad objekttyp
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T07:47:00Z'
updated_date: '2026-11-16T08:12:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/badge.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/settings_dialog.py
  - tests/test_detection_badge.py
  - README.md
ordinal: 384000
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
- [x] #6 Flera klasser som detekteras samtidigt visas som varsitt märke i videofönstret
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

6. Uppföljning: märket visar bara en klass trots att flera detekteras. BadgeTracker.update returnerar i stället alla synliga klasser sorterade på sannolikhet, och draw_badges staplar ett märke per klass uppifrån och ned på samma plats i fönstret. Uppdatera testerna så de räknar listor, lägg till tester för två klasser samtidigt, och uppdatera README och groma.
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

Uppföljning: flera klasser samtidigt.
- BadgeTracker.update returnerar nu en lista med alla synliga klassers säkraste detektion, sorterad på sannolikhet (och klassnamn vid lika), i stället för en enda Detection. Hysteresen är oförändrad och räknas fortfarande per klass, så en klass som ligger stabilt över tröskeln syns även när en annan flimrar.
- draw_badge ersattes av draw_badges, som staplar ett märke per klass uppifrån och ned med BADGE_GAP mellan. Den säkraste klassen ligger överst. Märken som inte får plats i fönstret ritas inte, så en liten panel inte täcks helt.
- StreamPanel._draw_badge heter _draw_badges och skickar hela listan till draw_badges.

Verifiering:
- tests/test_detection_badge.py: 21 tester. Nya: varje detekterad klass får ett märke med den säkraste först, en klass som ännu väntar på show_frames får inget märke medan en annan får det, en klass som försvinner lämnar de andra i fred, båda klasserna syns i märkesremsan i båda panelerna, och det andra märket sitter under det första.
- Regressionen reproducerad: med badge.py och detection_view.py återställda till HEAD fallerar test_both_detected_classes_get_a_badge med 0 pixlar i kniv-färg, alltså exakt det rapporterade felet. Med ändringen passerar alla 21.
- 93 tester i de berörda filerna passerar. Hela sviten: 600 passed, 1 skipped. test_sample_video_meta som föll i förra omgången passerar nu.
- Visuell kontroll: panel renderad till PNG med tre klasser (pistol 93 %, kniv 71 %, bomb 55 %). Tre staplade märken högst upp till höger, i klassfärg och i sannolikhetsordning.

Dokumentation: README (detektionsläget och klassmärkets fördröjning) samt groma (badge-komponenten och detektionsvyns översikt).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Detektionsvyn visar nu ett märke per detekterad klass, så två klasser i samma ram ger två märken i stället för ett.

Vad som ändrades:
- BadgeTracker.update returnerar en lista med alla synliga klassers säkraste detektion, sorterad på sannolikhet med den säkraste först, i stället för en enda Detection. Hysteresen är oförändrad och räknas per klass, så en klass som ligger stabilt över tröskeln syns även när en annan flimrar kring den.
- draw_badge ersattes av draw_badges, som staplar ett märke per klass uppifrån och ned på samma plats i fönstret: högst upp till höger i vänstra panelen och högst upp till vänster i högra. Märken som inte får plats i fönstret ritas inte, så en liten panel inte täcks helt av märken.
- StreamPanel._draw_badge heter _draw_badges och skickar hela listan vidare.

Verifiering: 21 tester i tests/test_detection_badge.py, varav fem nya för flera klasser samtidigt. Regressionen är reproducerad: med badge.py och detection_view.py återställda till HEAD fallerar testet för två klasser med noll pixlar i den andra klassens färg, alltså exakt det rapporterade felet. 93 tester i de berörda filerna passerar och hela sviten ger 600 passed, 1 skipped. En panel med tre klasser renderades till PNG och kontrollerades: tre staplade märken i klassfärg, i sannolikhetsordning.

Risker och uppföljning: märkena staplas nedåt, så en panel med många klasser samtidigt får de lägst rankade klasserna utan märke när platsen tar slut. Klassfiltret är vägen att begränsa antalet.
<!-- SECTION:FINAL_SUMMARY:END -->
