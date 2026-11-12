---
id: TASK-76
title: Annotering - Konsekvent färg per objektklass
status: Done
assignee: []
created_date: '2026-11-12T21:05:00Z'
updated_date: '2026-11-12T21:20:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/colors.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/detection_view.py
  - tests/test_colors.py
  - tests/test_dataset_thumbnails.py
  - tests/test_annotation_canvas.py
  - tests/test_annotation_classes.py
  - tests/test_detection_overlay.py
  - README.md
type: bug
ordinal: 74000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu verkar det vara möjligt att en och samma objektklass får olika färg på annotering i de olika bilderna. Det bör vara en bestämd färg per klass
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Samma objektklass har samma färg i annoteringsvyn, datasetvyn och detektionsvyn
- [x] #2 Färgen beror bara på klassnamnet, inte på ordningen i någon klasslista eller på vilken bild som visas
- [x] #3 Färgen är densamma mellan appstarter
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
1. Gör class_color() till en ren funktion av klassnamnet, utan known_classes-parametern.
2. Hasha namnet med md5 i stället för crc32: crc32 gav samma index åt tre av fyra klasser i paletten, md5 sprider namnen jämnt.
3. Utöka paletten från 8 till 16 färger med jämnt fördelade kulörer och samma ljushet, så namnhashningen inte kolliderar för de klasser som används.
4. Ta bort known_classes-plumbingen i dataset_view.py och detection_view.py.
5. Uppdatera test_colors.py, test_dataset_thumbnails.py och test_annotation_classes.py, och lägg renderande tester för annoteringsvyn och detektionsoverlayn.
6. Verifiera att samma klass får samma färg i alla tre vyerna.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rotorsak: class_color() använde klassens plats i en lista när known_classes skickades in, och crc32 annars. Annoteringsvyn skickade ingen lista medan dataset- och detektionsvyn skickade datasetets kategorier, så samma klass fick olika färg i olika vyer; listordningen avgjorde också färgen.

class_color() tar nu bara klassnamnet och hashar det med md5. crc32 provades först men gav samma index åt tre av fyra klasser (cigaretter, kniv, pistol), så md5 valdes för jämnare spridning.

Paletten utökades från 8 till 16 färger med jämnt fördelade kulörer (22,5 graders steg) och samma ljushet (S=230, L=155), så alla syns mot den mörka videobilden och fungerar som bakgrund bakom mörk text i datasetmärkena.

known_classes-plumbingen togs bort ur dataset_view.py (_badge, _capture_header, _thumbnail_pixmap, _add_capture_card, _add_pending_section) och detection_view.py (StreamPanel.known_classes).

Verifiering: 516 passed, 1 skipped. Nya tester: test_annotation_is_drawn_with_the_shared_class_color (annoteringsvyn), test_overlay_draws_the_shared_class_color (detektionsoverlayn), test_thumbnail_draws_the_annotations (datasetvyn), test_color_depends_only_on_the_class_name och test_unknown_class_survives_hash_seed_change.

Kvarstående risk: ett hashat index kan ge två klasser samma färg. De fyra vanligaste klasserna får fyra olika färger, men en modell med många klasser kan få kollisioner. Det är priset för att färgen inte får bero på vilka andra klasser som finns.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
class_color() är nu en ren funktion av klassnamnet: md5-hash modulo 16 färger, utan known_classes. Samma klass har därmed samma färg i annoterings-, dataset- och detektionsvyn, oavsett listordning och mellan appstarter. Paletten utökades från 8 till 16 jämnt fördelade färger eftersom crc32 gav tre av fyra klasser samma färg. known_classes-plumbingen togs bort ur dataset_view.py och detection_view.py. Verifierat med 516 passerande tester, inklusive renderande tester för alla tre vyerna och ett subprocesstest som visar att färgen inte beror av Pythons hash-seed. Kvarstående risk: hashning i en palett på 16 färger kan ge två klasser samma färg; det är avvägningen mot att färgen inte får bero på vilka andra klasser som finns.
<!-- SECTION:FINAL_SUMMARY:END -->
