---
id: TASK-95
title: 'Utvärdering av tränad modell: mAP per vy och falsklarm per bild'
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:27:00Z'
updated_date: '2026-11-16T19:18:00Z'
labels: []
dependencies: []
priority: high
type: feature
ordinal: 371000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-89. Appen har ingen utvärderingsfunktion. Det enda kvalitetstalet är val-mAP från träningen, och det säger inget om det som avgör om modellen går att driftsätta i en röntgenapp: hur ofta den larmar på en bild utan farliga objekt. xray_modeltrainer har `evaluate.py` som rapporterar mAP50-95 totalt och separat per vy, samt falsklarm per bild på en held-out mängd negativa bilder vid den konfidenströskel som ger 95 % recall. En poolad modell som ser bra ut totalt men faller på en vy är trasig, och det sammanlagda talet döljer det. Det här är också förutsättningen för att kunna jämföra två tränade modeller mot varandra i stället för att gissa.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 En tränad modell kan utvärderas mot en vald delmängd utan att träningen startas
- [x] #2 Resultatet visar mAP50-95 totalt och per vy
- [x] #3 Resultatet visar falsklarm per bild på negativa bilder vid en angiven recall-nivå
- [x] #4 Resultatet sparas så att två körningar kan jämföras i efterhand
- [x] #5 Test täcker mAP-beräkningen och falsklarmsräkningen på en liten känd mängd
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
1. Ren mAP-beräkning (IoU 0.5-0.95) och falsklarmsräkning i en egen modul, utan tunga beroenden, så den går att testa utan GPU.
2. Kör inferens över en vald delmängd med vald tränad modell och samla förutsägelser per bild.
3. Rapportera mAP50-95 totalt och per vy (bildens plats i fångstgruppen) samt falsklarm per bild på negativa bilder vid den tröskel som ger 95 % recall.
4. Spara rapporten som evaluation.json i körningens katalog så två körningar kan jämföras i efterhand.
5. Knapp i historikvyn som kör utvärderingen i bakgrunden och visar resultatet.
6. Test för mAP-beräkningen och falsklarmsräkningen på en liten känd mängd.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- infrastructure/training/metrics.py: ren numpy-implementation av IoU, girig matchning per klass, recall, tröskeln för 95 % recall, falsklarm per bild och COCO-lik mAP50-95 (IoU 0.5-0.95, all-point-interpolerad AP). Inga nya beroenden.
- application/evaluation.py: subset_images() väljer delmängd med samma delning som exporten (test/val/alla), view_labels() härleder vyn ur bildens plats i fångstgruppen, evaluate_run() kör modellen med låg tröskel (0.01) och räknar ut mAP totalt och per vy samt falsklarm per bild på de negativa bilderna vid den tröskel som ger 95 % recall. save_evaluation()/load_evaluation() skriver/läser evaluation.json i körningens katalog.
- ui/training_history.py: Utvärdera-knapp (Alt+U) med delmängdsval, körs i bakgrunden med upptagenindikatorn, visar rapporten i en egen rad och visar en sparad utvärdering när körningen markeras.

Verifiering: tests/test_evaluation.py (25 tester) täcker mAP på kända små mängder (perfekt, missad, halva, lös ruta, flera klasser), falsklarmsräkningen, tröskeln för 95 % recall, rapportens innehåll, att en modell som faller på en vy syns, att rapporten sparas och läses tillbaka samt historikvyns knapp och delmängdsval. Hela sviten: 747 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Appen har fått en utvärderingsfunktion. En tränad modell kan köras mot en vald delmängd (test, val eller hela datasetet) utan att en träning startas, och rapporten visar mAP50-95 och mAP50 totalt och per vy samt falsklarm per bild på de negativa bilderna vid den konfidenströskel som ger 95 % recall på de positiva. Vyn är bildens plats i fångstgruppen: appen fångar två strömmar per fångstögonblick, så en modell som ser bra ut totalt men faller på en vy syns bara när talen delas upp. Rapporten sparas som evaluation.json i körningens katalog, så två körningar kan jämföras i efterhand, och historikvyn visar den sparade rapporten när körningen markeras. Utvärderingen körs i bakgrunden med upptagenindikatorn.

mAP räknas i ren numpy: IoU 0.5 till 0.95 i steg om 0.05, girig matchning per klass och all-point-interpolerad AP. Inga nya beroenden, och beräkningen går att testa utan GPU eller modell.

Verifiering: tests/test_evaluation.py (25 tester) täcker mAP på kända små mängder (perfekt träff, missad, halva antalet, lös ruta, flera klasser), falsklarmsräkningen, tröskeln för 95 % recall, rapportens innehåll, att en modell som faller på en vy syns, att rapporten sparas och läses tillbaka samt historikvyns knapp och delmängdsval. Hela sviten: 747 passed, 1 skipped.

Begränsning: utvärderingen läser bilderna från datasetets images/-katalog, så den mäter modellen mot datasetet och inte mot den exporterade kopian. En bild som inte går att läsa hoppas över och räknas inte in.
<!-- SECTION:FINAL_SUMMARY:END -->
