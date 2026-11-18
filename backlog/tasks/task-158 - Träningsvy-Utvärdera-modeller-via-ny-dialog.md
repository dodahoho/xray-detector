---
id: TASK-158
title: Träningsvy - Utvärdera modeller via ny dialog
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-18T12:21:00Z'
updated_date: '2026-11-18T13:22:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 154000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu finns en liten sektion under tidigare träningar att man kan utvärdera modeller. Jag vill utveckla den funktionen mycket och tänker att det är bäst att göra det i en ny dialog som öppnas via knapp under tidigare träningar. Flytta in eventuell befintlig utvärderingsfunktionalitet till den nya dialogen.

Jag tänker mig att man inför en checkbox först i varje rad i tabellen över tidigare träningar samt en toggle markera/avmarkera alla. Knappen "Utvärdera" gör en jämförelse av de valda modellerna och visualiserar det i den dialog som öppnas. Det kan vara en sammanfattande tabell samt utvalda relevanta grafer för t ex uppmätt detektionsförmåga.

Som grund till uppmätt detektionsförmåga kan en vi t ex använda:
1) ett separat dataset med bilder och annoteringar vilket ger både träffsäkerhet och eventuella falska identifieringar
2) en katalog med bilder utan annoteringar, där kan uppmätingen endast räkna antal detektioner
3) en videofil med bilder utan annoteringar och där med samma resultat som punkt 2

Finns det andra sätt att lösa det eller andra relevanta metrics för utvärdering är jag öppen för förslag
<!-- SECTION:DESCRIPTION:END -->

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
1. metrics.py: track_lengths() och stability_summary() för spårlängder mellan bildrutor (ren numpy, testbar).
2. evaluation.py: EvaluationSource (dataset/mapp/video), bildruteströmmar per källtyp, evaluate_detections() för källor utan annoteringar (detektioner/bild, per klass, andel bilder med träff, medelkonfidens, konfidenshistogram, stabilitet), evaluate_source() och compare_runs().
3. ui/evaluation_chart.py: BarChart med grupperade staplar, ritad med QPainter och palettfärger som LineChart.
4. ui/evaluation_dialog.py: EvaluationDialog med källväljare (dataset + delmängd, bildmapp, videofil), sammanfattningstabell, grafer och bakgrundskörning.
5. ui/training_history.py: kryssruta först i varje rad, 'Markera alla', knappen 'Utvärdera valda...' som öppnar dialogen. Den infogade delmängdslistan, utvärderingsknappen och körningen flyttas till dialogen; etiketten med sparad utvärdering blir kvar som information.
6. Tester för metrics, källtyper, dialog och historikvyns kryssrutor. docs/beteende.md uppdateras.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Nytt: ui/evaluation_dialog.py (EvaluationDialog), ui/evaluation_chart.py (BarChart med grupperade staplar, QPainter och palettfärger), metrics.track_lengths/stability_summary, evaluation.EvaluationSource + dataset_frames/folder_frames/video_frames + evaluate_detections/evaluate_source/compare_runs/detection_summary_text.

Historikvyn: kryssruta i kolumn 'Val' först i varje rad, 'Markera alla' med tristate när bara en del är markerad, knappen 'Utvärdera valda...' öppnar dialogen. Den infogade delmängdslistan, utvärderingsknappen och bakgrundskörningen flyttade in i dialogen; raden under tabellen visar kvar den sparade utvärderingen. wait_for_evaluation finns kvar och delegerar till dialogen, så closeEvent väntar in en pågående körning.

Val: stabilitet räknas bara för videofil, eftersom spår kräver att bildrutorna kommer i tidsordning; en mapp sorteras på namn och ger därför ingen meningsfull spårlängd. Källor utan facit räknas vid appens egen konfidenströskel 0.4. Datasetrapporten sparas som evaluation.json; mapp- och videorapporterna lever bara i dialogen.

Verifiering: 938 passed, 1 skipped (pytest -n 4). ruff check utan anmärkning. Dialogen renderad offscreen för alla tre källtyperna: rätt kolumner (8 för dataset, 7 för mapp, 10 för video) och rätt grafer. Ett smoke-test genom MainWindow visar att kryssrutan aktiverar knappen och att dialogen öppnas. tests/test_shortcuts.py är instabil under -n 4 även på en orörd HEAD (två andra tester i samma fil föll där), så det är en känd svaghet i sviten och inte i den här ändringen.

Uppföljning efter testkörning: (1) utvärderingen stänger av videoströmmarna och detektionen medan modellerna går igenom källan och tänder dem igen när den är klar, via evaluation_started/evaluation_finished som dialogen sänder och MainWindow lyssnar på; knappen Utvärdera valda är dessutom avstängd medan en träning pågår. (2) Datasetkällan kan peka ut ett annat YOLO-dataset på disk (data.yaml, images/ och labels/) via infrastructure/dataset_store/external.py; tomt fält betyder applikationens eget dataset, och compare_runs läser det externa datasetet en gång per jämförelse. Ett dataset utan fångstpar hoppar över uppdelningen per vy. Commit fd21d8f.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Utvärderingen är nu en egen dialog som jämför flera modeller mot samma källa. Historiktabellen har en kryssruta först i varje rad och en 'Markera alla'-toggle, och knappen 'Utvärdera valda...' öppnar dialogen med de markerade träningarna. Den infogade delmängdslistan och utvärderingsknappen flyttade in i dialogen; raden under tabellen visar kvar den sparade utvärderingen.

Källan väljs i dialogen: en delmängd av datasetet (Test/Val/Alla), en mapp med bilder eller en videofil. Datasetkällan ger mAP50-95 och mAP50 totalt och per vy samt falsklarm per bild vid tröskeln för 95 % recall, som tidigare. Mappen och videon saknar facit, så där räknas i stället detektioner per bild och per klass, andelen bilder med minst en träff, medelkonfidensen och ett konfidenshistogram vid appens egen tröskel 0.4. En videofil ger dessutom stabiliteten: varje detektion matchas mot föregående bildrutas spår med IoU 0.5 och samma klass, och rapporten visar antal spår, medellängd i bildrutor och andel spår som håller minst tre rutor. Dialogen visar en sammanfattande tabell och staplar för mAP, falsklarm, detektioner per bild, konfidensfördelning och andel stabila spår.

Två val värda att känna till: stabiliteten räknas bara för video, eftersom en mapp sorteras på namn och därför inte har någon tidsordning att följa spår i; och bara datasetrapporten sparas som evaluation.json, eftersom mapp- och videorapporterna inte hör till någon delmängd av datasetet.

Verifierat med 938 passerade tester (1 skippat) och ruff check utan anmärkning. Dialogen renderades offscreen för alla tre källtyperna med rätt kolumner och grafer, och ett smoke-test genom MainWindow visar att kryssrutan aktiverar knappen och att dialogen öppnas. tests/test_shortcuts.py är instabil under parallell körning även på en orörd HEAD, så den flakinessen hör inte till den här ändringen.
<!-- SECTION:FINAL_SUMMARY:END -->
