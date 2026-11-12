---
id: TASK-64
title: Dataset - Thumbnails med inritade detektioner
status: Done
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:22:00Z'
updated_date: '2026-11-12T14:46:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 62000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Det vore önskvärt om de annoterade detektionerna var inritade även i thumbnails för bildparen
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Thumbnailen för en sparad bild visar bildens annoteringar inritade med klassens färg
- [x] #2 Ramen hamnar över objektets bbox, skalad till thumbnailens storlek
- [x] #3 En thumbnail utan annoteringar ritas utan ramar
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
1. Rita avbildningens annoteringar på thumbnailen med klassfärgen från ui/colors.py, skalat från originalbildens mått till thumbnailens höjd.
2. Låt ritningen ske i GUI-tråden där QPixmap skapas, så arbetstråden fortsätter dekoda QImage.
3. Test: thumbnailens pixmap innehåller klassfärgen när bilden har annoteringar, och inte när den saknar dem.
4. Uppdatera README och verifiera med hela testsviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Thumbnailen ritas av _thumbnail_pixmap: bilden skalas först till THUMB_HEIGHT och annoteringarna ritas sedan med QPainter i klassens färg från ui/colors.py. Skalan är thumbnailens höjd delad med originalbildens, vilket gäller båda axlarna eftersom scaledToHeight behåller bildförhållandet. Ritningen sker i GUI-tråden där QPixmap skapas, så arbetstråden dekodar fortfarande bara QImage. Mätt: en 64x48-bild med bbox [2,2,8,8] ger en 227x170-thumbnail med ramen på (7,7)-(35,35).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Thumbnails i datasetvyn visar bildens detektioner inritade med klassens färg.

Vad som ändrades i xray_detector/ui/dataset_view.py:
- _thumbnail_pixmap skalar bilden till THUMB_HEIGHT och ritar sedan varje annoterings bbox med QPainter och class_color, så ramen blir lika tunn oavsett bildstorlek.
- _add_capture_card använder den i stället för att skala pixmapen direkt.

Verifiering:
- Nya tester i tests/test_dataset_thumbnails.py: klassfärgen finns i thumbnailen när bilden har annoteringar, ramen hamnar i bildens övre vänstra del där bboxen ligger, och en bild utan annoteringar får ingen ram.
- Hela sviten: 452 passed, 1 skipped.
- Renderad vy: pistol röd, kniv grön, cannabis blå och cigaretter gul ram på respektive bild.
- ruff check på ändrade filer: inga anmärkningar.

Risker: ramen ritas utan klassnamn, så två klasser som delar färg (index modulo 8) ser likadana ut i thumbnailen; klassnamnen finns i titelradens märken.
<!-- SECTION:FINAL_SUMMARY:END -->
