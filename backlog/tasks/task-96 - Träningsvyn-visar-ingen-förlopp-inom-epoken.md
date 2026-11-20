---
id: TASK-96
title: Träningsvyn visar ingen förlopp inom epoken
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:27:00Z'
updated_date: '2026-11-16T19:18:00Z'
labels: []
dependencies: []
priority: medium
type: enhancement
ordinal: 372000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-89. Träningsprocessen rapporterar ett epokevent per avslutad epok, så GUI:t står still under hela epoken. På ett stort dataset tar en epok flera minuter, och under den tiden kan användaren inte se om träningen lever eller har hängt sig. xray_modeltrainer skriver en heartbeat (atomiskt, throttlad till 2 s) med epok, steg och totalt antal steg, och dashboarden visar hur långt epoken kommit. Samma sak behövs här, men som ett strukturerat event på stdout i linje med EPOCH-raden så att GUI:t slipper parsa fri text.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Träningsprocessen rapporterar hur långt den kommit inom pågående epok
- [x] #2 Träningsvyn visar epokförloppet medan epoken pågår
- [x] #3 Rapporteringen är throttlad så att den inte skriver en rad per batch
- [x] #4 Ett avbrott lämnar inte kvar en heartbeat som ser ut att vara aktuell
- [x] #5 Test täcker att förloppseventet tolkas och att en gammal heartbeat känns igen som inaktuell
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
1. PROGRESS {json}-rad på stdout med epok, steg, totalt antal steg och tidsstämpel, i linje med EPOCH-raden.
2. Throttlad rapportör i träningsprocessen som skriver högst varannat sekund i stället för en rad per batch.
3. YOLO rapporterar via on_train_batch_end; RF-DETR saknar publik krok och det dokumenteras.
4. Träningsvyn visar epokförloppet medan epoken pågår och markerar en gammal heartbeat som inaktuell; ett avbrott rensar den.
5. Test för tolkning av förloppseventet och för att en gammal heartbeat känns igen som inaktuell.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- domain/training.py: ProgressEvent (epok, steg, totalt antal steg, tidsstämpel) med fraction, age(), is_stale() och summary(), samt PROGRESS_STALE_AFTER_S = 10 s.
- infrastructure/training/progress.py: PROGRESS {json}-rad, parse_progress_line() och ProgressReporter som throttlar till en rad per intervall (2 s), alltid rapporterar en ny epok och epokens sista steg.
- train_task.py: _batch_callback() kopplas till on_train_batch_end och läser antalet steg ur träningslastaren en gång per epok.
- trainer.py: progress_event-signal; raden lyfts ut på samma sätt som EPOCH-raden, även när den hamnar mitt i en tqdm-rad.
- training_view.py: egen rad under epokraden som visar 'Epok 3 · steg 45/120 (38 %)', en timer som markerar en heartbeat äldre än 10 s som inaktuell ('ingen rapport på N s'), och som rensas vid avbrott och avslut.

RF-DETR saknar publik callback-krok i rfdetr 1.11, så där rapporteras bara epokevent (paketets egen förloppsrad syns i loggen). Det står i README.

Verifiering: tests/test_training_progress.py (19 tester) täcker eventraden, throttlingen, att en ny epok och sista steget alltid rapporteras, att en gammal heartbeat känns igen som inaktuell, batch-callbacken, workerns signal och vyns visning/rensning. Hela sviten: 747 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningsprocessen rapporterar nu hur långt den kommit inom pågående epok. En PROGRESS {json}-rad med epok, steg, totalt antal steg och tidsstämpel skrivs på stdout i linje med EPOCH-raden, throttlad till en rad varannat sekund i stället för en rad per batch. En ny epok rapporteras alltid, liksom epokens sista steg, så vyn ser att epoken är klar. Träningsvyn visar förloppet som 'Epok 3 · steg 45/120 (38 %)' under epokraden och markerar en heartbeat äldre än tio sekunder som inaktuell ('ingen rapport på N s') i stället för att låta siffran se aktuell ut; ett avbrott eller ett avslut rensar raden.

Verifiering: tests/test_training_progress.py (19 tester) täcker eventraden, throttlingen, att en ny epok och sista steget alltid rapporteras, att en gammal heartbeat känns igen som inaktuell, batch-callbacken, workerns signal och vyns visning respektive rensning. Hela sviten: 747 passed, 1 skipped.

Begränsning: rfdetr 1.11 har ingen publik callback-krok, så RF-DETR rapporterar bara epokevent; paketets egen förloppsrad syns fortfarande i loggen. Det står i README.
<!-- SECTION:FINAL_SUMMARY:END -->
