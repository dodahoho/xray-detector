---
id: TASK-103
title: >-
  Träningsvy - Dataset som ett eget card i sidan till höger om de generella
  träningsparametrarna
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T20:55:00Z'
updated_date: '2026-11-16T21:15:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 197000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Skapa ett eget card för dataset och lägg dit texten om dataset storlek samt train/val split
Flytta även inställningar för andel trin/val från separata inställningsdialogen till detta nya card
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
1. Dela träningsvyns överkant i en rad med två kort: Träningsinställningar till vänster och ett nytt Dataset-kort till höger, båda med FormCard:s maxbredd.
2. Flytta sammanställningen (dataset_info) till Dataset-kortet och lägg andelen train/val där som ett eget fält med ledtext.
3. Ta bort TrainValSplitSection ur träningsvyns inställningsdialog och ur settings_dialog.py, eftersom andelen nu ställs in direkt i kortet; train_ratio() och TRAIN_RATIO_KEY ligger kvar.
4. Uppdatera testerna som pekade på den gamla dialogen (test_settings_dialog, test_form_width) och lägg till ett test för det nya kortet.
5. Verifiera med sviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Träningsvyns överkant är nu en rad med två FormCard: Träningsinställningar till vänster och ett nytt Dataset-kort till höger. Dataset-kortet bär sammanställningen (Bilder/Objekt/Train-val/Uppdaterad) och fältet Andel till train med ledtexten om att resten blir validering. Ändringen sparas direkt i training/train_ratio och räknar om redovisningen, så samma andel styr YOLO-exporten som förut.

TrainValSplitSection togs bort ur settings_dialog.py och ur träningsvyns inställningsdialog, som nu bara innehåller träningsschemat; train_ratio() och TRAIN_RATIO_KEY ligger kvar eftersom datasetvyns export och träningsvyns start använder dem. Kortet har FORM_MAX_WIDTH som minimibredd så raden blir jämn, vilket är säkert eftersom fönstrets minsta bredd redan är 2116 px (detektionsvyn).

Testerna i tests/test_settings_dialog.py och tests/test_form_width.py uppdaterades, och två nya tester låser att andelen bor i Dataset-kortet och att kortet ligger till höger om träningsinställningarna.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped), ruff check på de ändrade filerna gav inga fel, och vyn renderades och granskades visuellt.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningsvyn har nu ett eget Dataset-kort till höger om träningsinställningarna. Kortet visar datasetets storlek (bilder, objekt, train/val-par och uppdateringsdatum) och har fältet Andel till train, som tidigare låg i vyns inställningsdialog. Ändringen sparas direkt och räknar om redovisningen, och samma andel styr fortfarande YOLO-exporten.

Inställningsdialogen innehåller nu bara träningsschemat. Kortet delar bredd med träningsinställningarna (FORM_MAX_WIDTH), så raden blir jämn.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped) med uppdaterade och två nya tester, ruff check på de ändrade filerna gav inga fel, och vyn renderades och granskades visuellt.
<!-- SECTION:FINAL_SUMMARY:END -->
