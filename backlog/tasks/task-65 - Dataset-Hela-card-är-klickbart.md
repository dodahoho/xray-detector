---
id: TASK-65
title: Dataset - Hela card är klickbart
status: Done
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:24:00Z'
updated_date: '2026-11-12T14:46:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 63000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
För att markera ett card med bildpar går det nu att klicka på någon av bilderna, men det skulle vara bättre att man istället har hela ytan som utgör ett card som klickbar
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ett klick var som helst på kortet markerar hela fångsten
- [x] #2 Ett klick på en thumbnail markerar fångsten en gång, inte två
- [x] #3 Kortet behåller sin storlek när fångsten markeras
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
1. Inför CaptureCard, en QFrame som äger fångstens group_id och sänder clicked vid musklick.
2. Låt både sparade och osparade kort använda CaptureCard och koppla clicked till samma växling som thumbnails använder.
3. Gör rubrikraden genomsläpplig för musklick, så klick på tid och klassmärken når kortet.
4. Test: klick på kortets yta markerar hela fångsten, klick på en thumbnail växlar bara en gång, och kortets storlek är oförändrad.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
CaptureCard är en QFrame som äger fångstens group_id och sänder clicked vid musklick; både sparade och osparade kort använder den. _on_thumb_clicked och _on_card_clicked går båda till _toggle_group, så växlingen sker på ett ställe. Rubrikraden har WA_TransparentForMouseEvents, så klick på tid och klassmärken når kortet. Thumbnailens egen mousePressEvent accepterar händelsen, så ett klick på en bild inte också når kortet bakom. Kortets cursor är PointingHandCursor.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Hela kortet markerar fångsten, inte bara bilderna.

Vad som ändrades i xray_detector/ui/dataset_view.py:
- CaptureCard (QFrame) med group_id och signalen clicked; både sparade och osparade kort använder den.
- _on_card_clicked och _on_thumb_clicked går till _toggle_group, så markeringen växlar på ett ställe.
- Rubrikraden är genomsläpplig för musklick, så klick på tid och klassmärken når kortet.
- Thumbnailens klick hanteras som förut och når inte kortet bakom, så ett klick växlar en gång.

Verifiering:
- Nya tester i tests/test_dataset_card_click.py med QTest.mouseClick: klick på kortets yta markerar hela fångsten, andra klick avmarkerar, klick på rubriken markerar, klick på en thumbnail växlar bara en gång, osparade kort fungerar likadant, kortets geometri och sizeHint är oförändrade och dubbelklick öppnar fortfarande annoteringen.
- Hela sviten: 452 passed, 1 skipped.
- ruff check på ändrade filer: inga anmärkningar.

Risker: klick med höger musknapp växlar också markeringen, samma beteende som thumbnails hade före ändringen.
<!-- SECTION:FINAL_SUMMARY:END -->
