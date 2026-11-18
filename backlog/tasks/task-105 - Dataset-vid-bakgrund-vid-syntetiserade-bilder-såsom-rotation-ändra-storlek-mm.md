---
id: TASK-105
title: >-
  Dataset - vid bakgrund vid syntetiserade bilder såsom rotation, ändra storlek
  mm
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T20:59:00Z'
updated_date: '2026-11-16T21:15:00Z'
labels: []
dependencies: []
type: bug
ordinal: 195000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om man väljer att utöka dataset med bilder ska t ex roterade eller förminskade bilder inte ge svart bakgrund för nya bakgrundsytan. Använd alltid vit bakgrund så att det matchar befintliga bakgrunden på bilderna.
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
1. Sätt borderValue till vitt i rotate() i augment.py, så ytan utanför den roterade bilden matchar bildernas vita bakgrund (verifierat: median 254, hörn 255 i media-videorna).
2. Uppdatera modulens docstring som i dag säger att ytan blir svart.
3. Anpassa testbilden i test_dataset_variations.py till vit bakgrund med mörkt objekt, så objektet går att hitta även när ramen är vit, och lägg till ett test som låser att ramen är vit.
4. Verifiera med sviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
rotate() i augment.py använder nu borderValue=BACKGROUND (255, 255, 255) i stället för 0, så ytan som rotationen lägger till matchar bildernas vita bakgrund. Bakgrunden verifierades mot media-videorna: median 254 och alla fyra hörn 255. Skalning och vändning lägger inte till någon ny yta, så de behövde ingen ändring.

Testbilden i tests/test_dataset_variations.py är nu vit med ett mörkt objekt, så objektet går att hitta även när ramen är vit; färgtestet använder negativ ljusstyrka eftersom en vit bakgrund inte kan ljusas upp. Ett nytt test låser att ramen är vit.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped) och ruff check på de ändrade filerna gav inga fel.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
En roterad syntetisk bild får inte längre en svart ram: ytan som rotationen lägger till fylls med bildernas vita bakgrund (255, 255, 255), som verifierades mot media-videorna (median 254, hörn 255). Skalning och vändning lägger inte till någon ny yta och behövde ingen ändring.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped) med ett nytt test som låser att ramen är vit, och ruff check på de ändrade filerna gav inga fel.
<!-- SECTION:FINAL_SUMMARY:END -->
