---
id: TASK-120
title: Dataset  - Ikon istället för badge "syntetisk"
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T15:03:00Z'
updated_date: '2026-11-17T15:12:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 348000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu när man utökar dataset får genererade bildpar en badge "syntetisk" för att indikera att det är en genererad bild. Jag vill istället att ikonen assets/generated.png läggs in med lämplig storlek i övre högra hörnet av card för bildparet (med lämplig padding till tom och right). För att slippa skala ikonen till rätt storlek kanske det är bäst att skapa en kopia i rätt storlek och använda den?
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Syntetiska bildpar visar ikonen i kortets övre högra hörn i stället för textmärket "Syntetisk"
- [x] #2 Ikonen används i en förberedd storlek, så vyn inte skalar den när kortet ritas
- [x] #3 Originalbildpar visar ingen ikon
- [x] #4 Ikonens tooltip anger vilka variationer som skapade paret
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
1. Skapa en nedskalad kopia av ui/assets/generated.png i rätt storlek (20x20) så vyn slipper skala ikonen vid varje omritning.
2. Byt ut textmärket "Syntetisk" i kortets rubrikrad mot ikonen, placerad längst till höger så den hamnar i kortets övre högra hörn med luft mot kortets kant. Tooltipen med variationerna behålls.
3. Uppdatera tests/test_dataset_variation_view.py så testerna kontrollerar ikonen i stället för texten, och lägg till ett test för placeringen i övre högra hörnet.
4. Kör hela testsviten och ruff, och granska ett renderat kort visuellt.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Textmärket "Syntetisk" är borta: syntetiska bildpar visar i stället ikonen i kortets övre högra hörn. Ikonen ligger sist i rubrikraden, efter stretchen, så den hamnar i hörnet oavsett hur många klassmärken kortet har. Rubrikradens höger- och övermarginal är 2 px, vilket tillsammans med kortets 8 px ger 10 px luft upptill och till höger. Rubrikraden är redan transparent för mushändelser, så ett klick på ikonen markerar bildparet som förut.

Ikonen används i en förberedd storlek: ui/assets/generated-20.png är en mjuk nedskalning av generated.png (120x120) till 20x20, så korten slipper skala om bilden varje gång listan byggs. Tooltipen med variationerna sitter kvar på ikonen. Källfilen har vit bakgrund, så ikonen syns som en liten vit ruta i både ljust och mörkt tema.

Verifiering: hela sviten gick igenom (861 passed, 1 skipped) och ruff check på de ändrade filerna gav inga fel. Korten renderades och granskades visuellt i både ljust och mörkt tema: ikonen sitter i övre högra hörnet med samma luft upptill och till höger, och originalkortet har ingen ikon. Testerna i tests/test_dataset_variation_view.py kontrollerar ikonen i stället för texten, att pixmapen är 20x20 och att den ligger sist i rubrikraden.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Textmärket "Syntetisk" är ersatt av ikonen i kortets övre högra hörn. Ikonen ligger sist i rubrikraden, efter stretchen, så den hamnar i hörnet oavsett antal klassmärken; rubrikradens 2 px marginal mot kortets 8 px ger 10 px luft upptill och till höger. Ett klick på ikonen markerar bildparet som förut, eftersom rubrikraden är transparent för mushändelser.

Ikonen används i en förberedd storlek: generated-20.png är en mjuk nedskalning av generated.png till 20x20, så korten slipper skala om bilden varje gång listan byggs. Tooltipen med variationerna sitter kvar på ikonen.

Verifiering: hela sviten gick igenom (861 passed, 1 skipped) och ruff check på de ändrade filerna gav inga fel. Korten renderades och granskades visuellt i ljust och mörkt tema, och testerna i tests/test_dataset_variation_view.py kontrollerar ikonen, dess storlek, placeringen och tooltipen.

Kvar att tänka på: källikonen har vit bakgrund, så den syns som en liten vit ruta i båda temana. En transparent ikon kräver en genomskinlig källfil, eftersom den mörka trollstaven annars försvinner mot mörkt tema.
<!-- SECTION:FINAL_SUMMARY:END -->
