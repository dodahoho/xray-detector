---
id: TASK-93
title: RF-DETR-exportens test-del är en kopia av val
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:26:00Z'
updated_date: '2026-11-16T19:17:00Z'
labels: []
dependencies: []
priority: medium
type: bug
ordinal: 376000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-89. `export.py:export_rfdetr` skriver `("train", train), ("valid", val), ("test", val)` — test-delen är samma bilder som val. Ett mått som rapporteras på test är därför i praktiken ett val-mått, och en modell som valts ut på val ser bättre ut än den är. Manifestet skriver också `num_test=len(val)`, så siffran i datasetvyn bekräftar felet i stället för att avslöja det. YOLO-exporten har samma struktur men bara train/val, så den påverkas inte.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Test-delen innehåller bilder som inte finns i train eller val
- [x] #2 Manifestets num_test motsvarar antalet bilder i test-delen
- [x] #3 Delningen är reproducerbar med samma seed
- [x] #4 Test täcker att test- och val-delarna inte delar några bilder
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
1. Dela upp fångstgrupperna i tre delmängder (train/valid/test) i RF-DETR-exporten i stället för att kopiera val till test.
2. Skriv num_test ur test-delens faktiska bildantal.
3. Gör delningen gruppbaserad och reproducerbar med samma seed; test får en egen grupp när datasetet har minst tre.
4. Låt träningsvyns train/val-redovisning räkna RF-DETR:s delning så siffran stämmer med exporten.
5. Test som visar att test- och val-delarna inte delar några bilder.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- export.py: train_val_test_split() med _three_way_targets(). Train får andelen, resten delas mellan valid och test; med minst tre grupper lämnas alltid en grupp till valid och en till test, så test aldrig blir en kopia av valid. Med färre än tre grupper blir test tom och manifestet säger num_test=0.
- export_rfdetr() skriver num_test ur test-delens faktiska bildantal.
- DatasetService.train_val_counts() tar family och räknar RF-DETR:s delning, så träningsvyns Train/val-siffra stämmer med exporten. Träningsvyn uppdaterar siffran när modellfamiljen byts.

Verifiering: tests/test_export_split.py täcker att test och val inte delar bilder, att manifestets num_test stämmer, att delningen är reproducerbar, att bildparen hålls ihop och att två grupper inte ger någon test-del. Hela sviten: 747 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RF-DETR-exportens test-del är inte längre en kopia av valid. Delningen sker i tre delmängder: train får den valda andelen, resten delas mellan valid och test, och med minst tre fångstgrupper lämnas alltid en grupp till vardera så test aldrig blir samma bilder som valet av bästa modell gjordes på. Delningen är gruppbaserad och reproducerbar med samma seed, och manifestets num_test räknar test-delens faktiska bildantal i stället för att upprepa val. DatasetService.train_val_counts tar familjen, så träningsvyns Train/val-siffra stämmer med RF-DETR:s export och uppdateras när modellfamiljen byts.

Verifiering: tests/test_export_split.py täcker att test och val inte delar bilder, att manifestets num_test stämmer, att delningen är reproducerbar, att bildparen hålls ihop och att två grupper inte ger någon test-del. Hela sviten: 747 passed, 1 skipped.

Begränsning: med färre än tre fångstgrupper går tre delmängder inte att fylla; då blir test tom och manifestet säger num_test=0 i stället för att låtsas att val är test.
<!-- SECTION:FINAL_SUMMARY:END -->
